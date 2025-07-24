# models.py

# --- 필요한 라이브러리들을 모두 가져옵니다 ---
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# --- 데이터베이스 객체를 생성합니다 ---
# 이 db 객체를 다른 파일에서 가져가서 사용하게 됩니다.
db = SQLAlchemy()


# --- 데이터 모델(테이블)들을 정의합니다 ---
# User 모델과 관계(relationship)가 있는 다른 모델들을 먼저 정의합니다.

class Order(db.Model):
    """주문 정보를 담는 모델"""
    __tablename__ = 'orders' # 테이블 이름 명시
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    total_price = db.Column(db.Integer, nullable=False)
    # user.id를 외래 키(Foreign Key)로 지정하여 User 모델과 연결합니다.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class PaymentTransaction(db.Model):
    """결제 정보를 담는 모델"""
    __tablename__ = 'payment_transactions'
    id = db.Column(db.Integer, primary_key=True)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='completed')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class PurchaseOrder(db.Model):
    """발주 정보를 담는 모델"""
    __tablename__ = 'purchase_orders'
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class User(UserMixin, db.Model):
    """사용자 정보를 담는 모델"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # User 모델에서 다른 모델들을 '역참조'할 수 있도록 관계를 설정합니다.
    orders = db.relationship('Order', backref='user', lazy=True)
    payment_transactions = db.relationship('PaymentTransaction', backref='user', lazy=True)
    purchase_orders = db.relationship('PurchaseOrder', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)