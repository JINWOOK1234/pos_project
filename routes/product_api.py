from flask import Blueprint, jsonify, request
from flask_login import login_required

# app.py에서 정의된 db 객체와 Product 모델을 임포트합니다.
from extensions import db
from models import User, Product # ★★★ 이 부분을 수정합니다. ★★★

# 'product_api'라는 이름의 Blueprint를 생성하고, 모든 라우트에 '/api' 접두사를 붙입니다.
product_bp = Blueprint('product_api', __name__, url_prefix='/api')


@product_bp.route('/products', methods=['GET', 'POST'])
@login_required
def products_handler():
    if request.method == 'GET':
        search_term = request.args.get('search', '')
        query = Product.query
        if search_term:
            query = query.filter(Product.name.like(f'%{search_term}%'))
        all_products = query.order_by(Product.name).all()
        return jsonify([{'id': p.id, 'name': p.name, 'unit': p.unit, 'price': p.price, 'stock_quantity': p.stock_quantity} for p in all_products])
    
    if request.method == 'POST':
        data = request.get_json()
        if not data or not all(k in data for k in ['id', 'name', 'unit', 'price']):
            return jsonify({'error': 'Missing required fields: id, name, unit, price'}), 400
        if Product.query.get(data['id']):
            return jsonify({'error': f"Product with ID '{data['id']}' already exists."}), 409
        
        new_product = Product(
            id=data['id'],
            name=data['name'],
            unit=data['unit'],
            price=data['price'],
            stock_quantity=data.get('stock_quantity', 0)
        )
        db.session.add(new_product)
        db.session.commit()
        return jsonify({'id': new_product.id, 'name': new_product.name}), 201

@product_bp.route('/product/<product_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'GET':
        return jsonify({'id': product.id, 'name': product.name, 'unit': product.unit, 'price': product.price, 'stock_quantity': product.stock_quantity})
    
    if request.method == 'PUT':
        data = request.get_json()
        product.name = data.get('name', product.name)
        product.unit = data.get('unit', product.unit)
        product.price = data.get('price', product.price)
        product.stock_quantity = data.get('stock_quantity', product.stock_quantity)
        db.session.commit()
        return jsonify({'id': product.id, 'name': product.name})

    if request.method == 'DELETE':
        db.session.delete(product)
        db.session.commit()
        return '', 204

@product_bp.route('/product/<product_id>/stock', methods=['PUT'])
@login_required
def adjust_product_stock(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    data = request.get_json()
    if 'adjustment' not in data:
        return jsonify({'error': 'Missing "adjustment" field'}), 400
    try:
        adjustment = int(data['adjustment'])
    except ValueError:
        return jsonify({'error': 'Adjustment must be an integer'}), 400
    if product.stock_quantity + adjustment < 0:
        return jsonify({'error': 'Stock cannot go below zero'}), 400
    
    product.stock_quantity += adjustment
    db.session.commit()
    return jsonify({'id': product.id, 'name': product.name, 'stock_quantity': product.stock_quantity})

@product_bp.route('/price')
@login_required
def get_price():
    product_id = request.args.get('productId')
    product = Product.query.get(product_id)
    if product:
        return jsonify({'price': product.price})
    return jsonify({'error': 'Price not found'}), 404