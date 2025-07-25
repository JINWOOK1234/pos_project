from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

# app.py에서 정의된 db 객체와 모델들을 임포트합니다.

from app import db, Supplier, PurchaseOrder, PurchaseOrderItem, Product

supplier_bp = Blueprint('supplier_bp', __name__, url_prefix='/api')

@supplier_bp.route('/suppliers', methods=['GET', 'POST'])
@login_required
def suppliers_handler():
    """공급처 목록을 조회(GET)하거나 새 공급처를 추가(POST)합니다."""
    if request.method == 'GET':
        suppliers = Supplier.query.filter_by(user_id=current_user.id).order_by(Supplier.name).all()
        return jsonify([{'id': s.id, 'name': s.name, 'contact_person': s.contact_person, 'phone_number': s.phone_number} for s in suppliers])

    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Supplier name is required'}), 400
        
        new_supplier = Supplier(
            name=data['name'],
            contact_person=data.get('contact_person'),
            phone_number=data.get('phone_number'),
            user_id=current_user.id
        )
        db.session.add(new_supplier)
        db.session.commit()
        return jsonify({'id': new_supplier.id, 'name': new_supplier.name}), 201

@supplier_bp.route('/supplier/<int:supplier_id>', methods=['PUT', 'DELETE'])
@login_required
def supplier_detail_handler(supplier_id):
    """특정 공급처를 수정(PUT)하거나 삭제(DELETE)합니다."""
    supplier = Supplier.query.filter_by(id=supplier_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'PUT':
        data = request.get_json()
        supplier.name = data.get('name', supplier.name)
        supplier.contact_person = data.get('contact_person', supplier.contact_person)
        supplier.phone_number = data.get('phone_number', supplier.phone_number)
        db.session.commit()
        return jsonify({'message': 'Supplier updated successfully'})

    if request.method == 'DELETE':
        if supplier.purchase_orders:
            return jsonify({'error': 'Cannot delete supplier with existing purchase orders.'}), 400
        db.session.delete(supplier)
        db.session.commit()
        return '', 204

@supplier_bp.route('/purchases', methods=['GET', 'POST'])
@login_required
def purchases_handler():
    """매입 내역을 조회(GET)하거나 새 매입을 기록(POST)합니다."""
    if request.method == 'GET':
        purchases = PurchaseOrder.query.options(
            joinedload(PurchaseOrder.supplier)
        ).filter_by(user_id=current_user.id).order_by(PurchaseOrder.purchase_date.desc()).all()
        return jsonify([{'id': p.id, 'purchase_date': p.purchase_date.isoformat(), 'supplier_name': p.supplier.name if p.supplier else 'N/A', 'total_cost': p.total_cost} for p in purchases])

    if request.method == 'POST':
        data = request.get_json()
        if not data or 'items' not in data:
            return jsonify({'error': 'Purchase items are required'}), 400
        
        try:
            total_cost = sum(item['quantity'] * item['cost_per_unit'] for item in data['items'])
            new_purchase = PurchaseOrder(
                supplier_id=data.get('supplier_id'),
                total_cost=total_cost,
                user_id=current_user.id
            )
            db.session.add(new_purchase)

            for item_data in data['items']:
                product = Product.query.get(item_data['product_id'])
                if not product:
                    raise ValueError(f"Product with ID {item_data['product_id']} not found.")
                
                product.stock_quantity += item_data['quantity']
                
                purchase_item = PurchaseOrderItem(
                    purchase_order=new_purchase,
                    product_id=item_data['product_id'],
                    quantity=item_data['quantity'],
                    cost_per_unit=item_data['cost_per_unit']
                )
                db.session.add(purchase_item)
            
            db.session.commit()
            return jsonify({'message': 'Purchase recorded successfully', 'purchase_id': new_purchase.id}), 201
        except (ValueError, KeyError) as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to record purchase: {str(e)}'}), 500