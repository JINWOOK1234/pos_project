from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db, Customer, PaymentTransaction

customer_bp = Blueprint('customer_bp', __name__)

@customer_bp.route('/api/customers', methods=['GET', 'POST'])
@login_required
def customers_handler():
    if request.method == 'GET':
        search_term = request.args.get('search', '')
        query = Customer.query.filter_by(user_id=current_user.id)
        if search_term:
            query = query.filter(Customer.name.like(f'%{search_term}%'))
        customers = query.order_by(Customer.name).all()
        return jsonify([c.to_dict() for c in customers])

    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Customer name is required'}), 400
        new_customer = Customer(
            name=data['name'],
            phone_number=data.get('phone_number'),
            address=data.get('address'),
            user_id=current_user.id
        )
        db.session.add(new_customer)
        db.session.commit()
        return jsonify(new_customer.to_dict()), 201

@customer_bp.route('/api/customer/<int:customer_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def customer_detail_handler(customer_id):
    customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first_or_404()

    if request.method == 'GET':
        return jsonify(customer.to_dict())

    if request.method == 'PUT':
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Customer name is required'}), 400
        customer.name = data.get('name', customer.name)
        customer.phone_number = data.get('phone_number', customer.phone_number)
        customer.address = data.get('address', customer.address)
        db.session.commit()
        return jsonify({'message': 'Customer updated successfully'})

    if request.method == 'DELETE':
        if customer.orders or customer.payment_transactions:
            return jsonify({'error': 'Cannot delete customer with existing orders or payments.'}), 400
        db.session.delete(customer)
        db.session.commit()
        return '', 204

@customer_bp.route('/api/customer/<int:customer_id>/payments', methods=['GET', 'POST'])
@login_required
def payment_handler(customer_id):
    customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first_or_404()

    if request.method == 'GET':
        transactions = PaymentTransaction.query.filter_by(customer_id=customer.id).order_by(PaymentTransaction.transaction_date.desc()).all()
        return jsonify([{
            'id': t.id,
            'transaction_date': t.transaction_date.isoformat(),
            'amount': t.amount,
            'payment_method': t.payment_method,
            'notes': t.notes
        } for t in transactions])

    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('amount'):
            return jsonify({'error': 'Payment amount is required'}), 400
        try:
            amount = int(data['amount'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount'}), 400

        new_transaction = PaymentTransaction(
            customer_id=customer.id,
            amount=amount,
            payment_method=data.get('payment_method', 'cash'),
            notes=data.get('notes'),
            user_id=current_user.id
        )
        customer.receivable_balance -= amount
        db.session.add(new_transaction)
        db.session.commit()
        return jsonify({
            'message': 'Payment recorded successfully',
            'customer_name': customer.name,
            'new_balance': customer.receivable_balance
        }), 201

@customer_bp.route('/api/customers/receivables', methods=['GET'])
@login_required
def get_customer_receivables():
    customers = Customer.query.filter(Customer.user_id == current_user.id, Customer.receivable_balance > 0).order_by(Customer.name).all()
    return jsonify([c.to_dict() for c in customers])