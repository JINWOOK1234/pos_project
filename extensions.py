# extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# 모든 확장 기능 객체들을 이 파일에서 생성합니다.
# 이제 이 파일이 db, migrate, login_manager의 유일한 출처가 됩니다.
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()