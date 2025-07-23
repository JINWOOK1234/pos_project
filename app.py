import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
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

migrate = Migrate(app, db)

# --- [신규] Blueprint 등록 ---
# 기능별로 분리된 라우트 파일을 임포트하고 등록합니다.
from routes.auth_api import auth_bp
from routes.product_api import product_bp
from routes.order_api import order_bp
from routes.customer_api import customer_bp
from routes.supplier_api import supplier_bp
from routes.sales_api import sales_bp

app.register_blueprint(auth_bp)
app.register_blueprint(product_bp)
app.register_blueprint(order_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(supplier_bp)
app.register_blueprint(sales_bp)

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

if __name__ == '__main__':
    app.run(debug=True)