import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migratefrom sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

# 1. Flask 애플리케이션 및 확장 객체 초기화
app = Flask(__name__)

# --- SQLAlchemy 및 Secret Key 설정 ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'a_very_secret_key_for_pos_project'

db = SQLAlchemy(app)

# --- Flask-Login 설정 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Login required'}), 401

# 2. 데이터 모델(테이블) 정의
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    orders = db.relationship('Order', backref='user', lazy=True)
    payment_transactions = db.relationship('PaymentTransaction', backref='user', lazy=True)
    # [신규] user와 purchase_orders 관계 추가
    purchase_orders = db.relationship('PurchaseOrder', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    unit = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    receivable_balance = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('customers', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone_number': self.phone_number,
            'address': self.address,
            'receivable_balance': self.receivable_balance
        }

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    total_amount = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='cash')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='completed')
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    customer = db.relationship('Customer', backref=db.backref('orders', lazy=True))

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.String(10), db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_unit = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product')

class PaymentTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False, default='cash')
    notes = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer = db.relationship('Customer', backref=db.backref('payment_transactions', lazy=True))


# --- [신규] 매입 관리 모델 ---
class Supplier(db.Model):
    """상품 공급처 정보를 저장하는 테이블"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    contact_person = db.Column(db.String(50), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('suppliers', lazy=True))

class PurchaseOrder(db.Model):
    """매입 기록(전표) 정보를 저장하는 테이블"""
    id = db.Column(db.Integer, primary_key=True)
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    total_cost = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy=True, cascade="all, delete-orphan")
    supplier = db.relationship('Supplier', backref=db.backref('purchase_orders', lazy=True))

class PurchaseOrderItem(db.Model):
    """매입 전표에 포함된 개별 상품 정보를 저장하는 테이블"""
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    product_id = db.Column(db.String(10), db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    cost_per_unit = db.Column(db.Integer, nullable=False) # 매입 시점의 단가
    product = db.relationship('Product')
afd

migrate = Migrate(app, db)

# --- [신규] Blueprint 등록 ---
# 기능별로 분리된 라우트 파일을 임포트하고 등록합니다.
from routes.product_api import product_bp
from routes.order_api import order_bp
app.register_blueprint(product_bp)
app.register_blueprint(order_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- 페이지 렌더링 ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('index.html')
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('register.html')

# --- API 엔드포인트 ---

@app.route('/api/auth/status')
@login_required
def auth_status():
    return jsonify({'username': current_user.username})

@app.route('/api/customers', methods=['GET', 'POST'])
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
        return jsonify({
            'id': new_customer.id,
            'name': new_customer.name,
            'phone_number': new_customer.phone_number,
            'address': new_customer.address
        }), 201

@app.route('/api/customer/<int:customer_id>', methods=['GET', 'PUT', 'DELETE'])
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

@app.route('/api/customer/<int:customer_id>/payments', methods=['GET', 'POST'])
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
        
# --- [신규] 매입 관리 API 엔드포인트 ---
@app.route('/api/suppliers', methods=['GET', 'POST'])
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

@app.route('/api/supplier/<int:supplier_id>', methods=['PUT', 'DELETE'])
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

@app.route('/api/purchases', methods=['GET', 'POST'])
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
                
                # 재고 증가
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

@app.route('/api/customers/receivables', methods=['GET'])
@login_required
def get_customer_receivables():
    # [누락된 기능 추가] 외상 잔액이 있는 거래처 목록 조회 API
    customers = Customer.query.filter(
        Customer.user_id == current_user.id,
        Customer.receivable_balance > 0
    ).order_by(Customer.name).all()
    
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'phone_number': c.phone_number,
        'receivable_balance': c.receivable_balance
    } for c in customers])
@app.route('/api/price')
@login_required
def get_price():
    product_id = request.args.get('productId')
    product = Product.query.get(product_id)
    if product:
        return jsonify({'price': product.price})
    return jsonify({'error': 'Price not found'}), 404

@app.route('/api/sales/daily', methods=['GET'])
@login_required
def get_daily_sales():
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400
    else:
        target_date = datetime.datetime.utcnow().date()

    total_daily_sales = db.session.query(func.sum(Order.total_amount)).filter(
        Order.user_id == current_user.id,
        func.date(Order.order_date) == target_date,
        Order.status == 'completed'
    ).scalar() or 0
    return jsonify({'date': target_date.isoformat(), 'total_sales': total_daily_sales})

@app.route('/api/sales/monthly', methods=['GET'])
@login_required
def get_monthly_sales():
    year_str = request.args.get('year')
    month_str = request.args.get('month')
    if not year_str or not month_str:
        return jsonify({'error': 'Year and month are required parameters.'}), 400
    try:
        year = int(year_str)
        month = int(month_str)
    except ValueError:
        return jsonify({'error': 'Invalid year or month format.'}), 400
    if not (1900 <= year <= 2100 and 1 <= month <= 12):
        return jsonify({'error': 'Invalid year or month value.'}), 400
    
    total_monthly_sales = db.session.query(func.sum(Order.total_amount)).filter(
        Order.user_id == current_user.id,
        db.extract('year', Order.order_date) == year,
        db.extract('month', Order.order_date) == month,
        Order.status == 'completed'
    ).scalar() or 0
    return jsonify({'year': year, 'month': month, 'total_sales': total_monthly_sales})

# --- 사용자 인증(Auth) API ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': f"User '{data['username']}' already exists"}), 409
    
    try:
        new_user = User(username=data['username'])
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to register user: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        login_user(user)
        return jsonify({'message': 'Logged in successfully'})
    
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'})

if __name__ == '__main__':
    app.run(debug=True)