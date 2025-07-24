from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

# app.py에서 정의된 db 객체와 모델들을 임포트합니다.
from models import db, User # ★★★ 이 부분을 수정합니다. ★★★

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

@auth_bp.route('/status')
@login_required
def auth_status():
    return jsonify({'username': current_user.username})

@auth_bp.route('/register', methods=['POST'])
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

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        login_user(user)
        return jsonify({'message': 'Logged in successfully'})
    
    return jsonify({'error': 'Invalid username or password'}), 401

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'})