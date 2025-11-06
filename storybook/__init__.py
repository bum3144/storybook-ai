# storybook/__init__.py
from flask import Flask
from storybook.routes.api import api_bp
from storybook.routes.ui import ui_bp  # ✅ 새로 추가

def create_app():
    app = Flask(__name__)

    # Blueprint 등록
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(ui_bp)  # ✅ HTML 라우트 등록

    @app.route("/")
    def home():
        return "<h3>AI 그림동화 생성기 서버가 실행 중입니다.<br>👉 /dashboard 로 이동하세요.</h3>"

    return app
