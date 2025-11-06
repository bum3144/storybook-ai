# storybook/routes/ui.py
from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for

ui_bp = Blueprint("ui", __name__)

@ui_bp.get("/")
def home():
    # 루트 → 안내 문구 + 대시보드 이동 링크
    return (
        "AI 그림동화 생성기 서버가 실행 중입니다.<br>"
        "👉 <a href='/dashboard'>/dashboard</a> 로 이동하세요."
    )

@ui_bp.get("/dashboard")
def dashboard():
    # 저장본 목록은 다음 단계에서 서버 리스트로 교체 가능(지금은 간단히 템플릿 렌더)
    return render_template("dashboard.html")

@ui_bp.get("/new")
def new():
    # 모드선택(직접쓰기 / AI와 함께) 화면
    return render_template("new.html")

@ui_bp.get("/editor")
def editor():
    """
    글 편집 화면.
    ?mode=manual  → 직접 쓰기
    ?mode=ai      → AI 추천 모드
    """
    mode = request.args.get("mode", "manual")
    if mode not in ("manual", "ai"):
        mode = "manual"
    return render_template("editor.html", mode=mode)

@ui_bp.get("/images")
def images():
    """
    이미지 생성/미리보기 화면.
    - editor.html에서 쿼리스트링으로 전달받은 title, pages(JSON 문자열)를 그대로 넘겨
      템플릿에서 JS로 /api/story(withImages=true) 호출 → 썸네일 갤러리 표시
    """
    title = request.args.get("title", "").strip()
    pages_json = request.args.get("pages", "").strip()
    return render_template("images.html", title=title, pages_json=pages_json)
