import click
from flask import Flask, render_template, redirect, url_for, jsonify
from flask.cli import with_appcontext
from flask_login import current_user, login_required

# extensions.py에서 확장 기능 객체들을 가져옵니다.
from extensions import db, migrate, login_manager
# models.py에서 User 모델을 가져옵니다. (로그인 매니저에서 사용하기 위함)
from models import User

# --- 데이터베이스 초기화 명령어 정의 ---
@click.command('init-db')
@with_appcontext
def init_db_command():
    """기존 데이터를 모두 삭제하고 테이블을 새로 만듭니다."""
    # models.py 파일이 import 되어야 db.create_all()이 테이블을 인식할 수 있습니다.
    # 이 구조에서는 자동으로 인식되므로 별도의 import가 필요 없습니다.
    db.drop_all()
    db.create_all()
    click.echo('Initialized the database.')

# --- 애플리케이션 팩토리 함수 ---
def create_app():
    """Flask 앱 인스턴스를 생성하고 설정합니다."""
    app = Flask(__name__)

    # 설정 로드
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pos.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'a_very_secret_key_that_must_be_changed'

    # 확장 기능들을 app 인스턴스와 연결합니다.
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'login_page'

    # 위에서 정의한 CLI 명령어를 앱에 등록합니다.
    app.cli.add_command(init_db_command)

    # 순환 참조를 피하기 위해, 이 함수 안에서 블루프린트를 가져옵니다.
    from routes.auth_api import auth_bp
    from routes.product_api import product_bp
    from routes.order_api import order_bp
    from routes.customer_api import customer_bp
    from routes.supplier_api import supplier_bp
    from routes.sales_api import sales_bp

    # 블루프린트들을 앱에 등록합니다.
    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(sales_bp)

    # 기본 페이지 라우트
     # 기존의 index 라우트를 대시보드로 변경합니다.
    @app.route('/')
    @login_required # 로그인이 필요한 페이지로 설정
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/login')
    def login_page():
        # 이미 로그인한 사용자가 /login 경로로 접근하면 대시보드로 리디렉션
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/register')
    def register_page():
        # 이미 로그인한 사용자가 /register 경로로 접근하면 대시보드로 리디렉션
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('register.html')
    
    # --- 각 메뉴 페이지를 위한 임시 라우트 추가 ---
    # 실제 페이지를 만들기 전까지 임시로 사용할 수 있습니다.
    @app.route('/sales-registration')
    @login_required
    def sales_registration_page():
        return render_template('sales_registration.html')
    
    @app.route('/purchase-registration')
    @login_required
    def purchase_registration_page():
       return render_template('purchase_registration.html')
   
    @app.route('/settings')
    @login_required
    def settings_page():
        return render_template('settings.html')

    @app.route('/sales-status')
    @login_required
    def sales_status_page():
        return "<h1>판매 현황 페이지</h1><a href='/'>대시보드로 돌아가기</a>"

    return app
# --- Flask-Login 콜백 함수 ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Login required'}), 401

# --- 앱 실행 부분 ---
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, use_reloader=False)
