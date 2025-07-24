import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

# app.py에서 정의된 db 객체와 모델들을 임포트합니다.
from models import db, Order

sales_bp = Blueprint('sales_bp', __name__, url_prefix='/api/sales')

@sales_bp.route('/daily', methods=['GET'])
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

@sales_bp.route('/monthly', methods=['GET'])
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