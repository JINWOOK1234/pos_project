import datetime
from flask import Flask, render_template, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from sqlalchemy import func

# --- 1. 확장 객체들을 app 없이 초기화 ---
# db, migrate, login_manager 객체를 먼저 생성합니다.
# 이때 app 객체를 넘겨주지 않는 것이 핵심입니다.
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login_page'

# --- 2. 데이터 모델(테이블) 정의 ---
# 모델 정의는 기존과 동일하게 유지합니다.
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    orders = db.relationship('Order', backref='user', lazy=True)
    payment_transactions = db.relationship('PaymentTransaction', backref='user', lazy=True)
    purchase_orders = db.relationship('PurchaseOrder', backref='user', lazy=True)
    suppliers = db.relationship('Supplier', backref='user', lazy=True)
    customers = db.relationship('Customer', backref='user', lazy=True)

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
    orders = db.relationship('Order', backref='customer', lazy=True)
    payment_transactions = db.relationship('PaymentTransaction', backref='customer', lazy=True)

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

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    contact_person = db.Column(db.String(50), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)

class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    total_cost = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy=True, cascade="all, delete-orphan")

class PurchaseOrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    product_id = db.Column(db.String(10), db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    cost_per_unit = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product')

# --- 3. 애플리케이션 팩토리 함수 정의 ---
def create_app():
    """Flask app을 생성하고 설정한 뒤 반환합니다."""
    app = Flask(__name__)

    # --- 설정 로드 ---
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pos.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'a_very_secret_key_for_pos_project'

    # --- 확장 기능들을 app과 연결 ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # --- 블루프린트 등록 ---
    # 순환 참조를 피하기 위해 이 함수 안에서 임포트합니다.
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

    # --- 페이지 렌더링 라우트 ---
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
    
    return app

# --- 4. 기타 설정 (LoginManager) ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Login required'}), 401

# --- 5. 앱 실행 ---
# 이 파일이 직접 실행될 때만 앱을 생성하고 실행합니다.
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)