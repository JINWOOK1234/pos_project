import datetime
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func

# app.py에서 정의된 db 객체와 모델들을 임포트합니다.
from extensions import db
from models  import Order, OrderItem, Product, Customer



# 'order_api'라는 이름의 Blueprint를 생성하고, 모든 라우트에 '/api' 접두사를 붙입니다.
order_bp = Blueprint('order_api', __name__, url_prefix='/api')


@order_bp.route('/orders', methods=['GET', 'POST'])
@login_required
def orders_handler():
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'items' not in data or 'total_amount' not in data:
            return jsonify({'error': 'Missing order data'}), 400

        payment_method = data.get('payment_method', 'cash')
        customer_id = data.get('customer_id')

        if payment_method == 'credit' and not customer_id:
            return jsonify({'error': 'Customer must be selected for credit transactions'}), 400

        try:
            new_order = Order(
                total_amount=data['total_amount'],
                user_id=current_user.id,
                customer_id=customer_id,
                payment_method=payment_method
            )
            db.session.add(new_order)

            if payment_method == 'credit':
                customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first()
                if not customer:
                    raise ValueError("Invalid customer for credit transaction.")
                customer.receivable_balance += new_order.total_amount

            for item_data in data['items']:
                product = Product.query.get(item_data['id'])
                if not product:
                    raise ValueError(f"Product with ID {item_data['id']} not found.")
                if product.stock_quantity < item_data['quantity']:
                    raise ValueError(f"Not enough stock for product {product.name}")
                
                order_item = OrderItem(
                    order=new_order,
                    product_id=item_data['id'],
                    quantity=item_data['quantity'],
                    price_per_unit=item_data['price']
                )
                product.stock_quantity -= item_data['quantity']
                db.session.add(order_item)
            
            db.session.commit()
            return jsonify({'message': 'Order created successfully', 'order_id': new_order.id}), 201

        except ValueError as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to create order: {str(e)}'}), 500

    if request.method == 'GET':
        query = Order.query.filter_by(user_id=current_user.id)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        try:
            if start_date_str:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                query = query.filter(func.date(Order.order_date) >= start_date)
            if end_date_str:
                end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query = query.filter(func.date(Order.order_date) <= end_date)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

        orders = query.order_by(Order.order_date.desc()).all()
        result = []
        for o in orders:
            order_data = {
                'id': o.id,
                'order_date': o.order_date.isoformat(),
                'total_amount': o.total_amount,
                'customer_id': o.customer_id,
                'customer_name': o.customer.name if o.customer else None,
                'status': o.status,
                'payment_method': o.payment_method,
                'items': [{
                    'product_id': i.product_id,
                    'product_name': i.product.name,
                    'quantity': i.quantity,
                    'price_per_unit': i.price_per_unit
                } for i in o.items]
            }
            result.append(order_data)
        return jsonify(result)

@order_bp.route('/order/<int:order_id>', methods=['GET', 'DELETE'])
@login_required
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    if request.method == 'GET':
        # 이 로직은 orders_handler의 GET 로직과 중복되므로, 별도 함수로 추출하여 재사용할 수 있습니다.
        # 여기서는 설명을 위해 그대로 둡니다.
        return jsonify({ 'id': order.id, 'order_date': order.order_date.isoformat(), 'total_amount': order.total_amount, 'customer_id': order.customer_id, 'customer_name': order.customer.name if order.customer else None, 'status': order.status, 'payment_method': order.payment_method, 'items': [{ 'product_id': item.product_id, 'product_name': item.product.name, 'quantity': item.quantity, 'price_per_unit': item.price_per_unit } for item in order.items] })

    if request.method == 'DELETE':
        if order.status == 'cancelled':
            return jsonify({'error': 'Order is already cancelled'}), 400
        
        if order.payment_method == 'credit' and order.customer:
            order.customer.receivable_balance -= order.total_amount
        
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock_quantity += item.quantity
        
        order.status = 'cancelled'
        db.session.commit()
        return jsonify({'id': order.id, 'status': order.status, 'message': 'Order cancelled successfully'})