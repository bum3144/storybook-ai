# storybook/__init__.py
from flask import Flask, redirect
from storybook.routes.api import api_bp
from storybook.routes.ui import ui_bp

def create_app():
    # 템플릿/정적 경로는 기본값으로도 잘 잡히지만, 명시해도 무방합니다.
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # 세션(임시 저장) 안정화: 서버 재시작해도 세션이 유지되도록 고정 키를 둡니다.
    app.secret_key = "story-dev-secret-keep-this-constant"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # 블루프린트 등록
    # api_bp 가 파일 안에서 이미 url_prefix="/api" 로 선언되어 있다면,
    # 여기서는 접두어를 다시 주지 않습니다. (중복/충돌 방지)
    app.register_blueprint(api_bp)    # <- api_bp 쪽에서 url_prefix='/api'
    app.register_blueprint(ui_bp)     # UI 라우트 (대시보드/에디터/이미지 페이지 등)

    @app.route("/")
    def home():
        return redirect("/dashboard")

    return app