# storybook/routes/ui.py
from __future__ import annotations
from flask import Blueprint, render_template, request

ui_bp = Blueprint("ui", __name__)

@ui_bp.get("/")
def home():
    return (
        "AI 그림동화 생성기 서버가 실행 중입니다.<br>"
        "👉 <a href='/dashboard'>/dashboard</a> 로 이동하세요."
    )

@ui_bp.get("/dashboard")
def dashboard():
    # 간단 목록 (지금은 기본값 빈 리스트 전달: 템플릿 루프 안전)
    return render_template("dashboard.html", stories=[])

@ui_bp.get("/new")
def new():
    return render_template("new.html")

@ui_bp.get("/editor")
def editor():
    """
    글 편집 화면.
    쿼리:
      - mode: manual | ai (기본 manual)
      - title: (선택) 기존 제목 프리필
      - prefill: (선택) JSON 배열 문자열, 페이지별 문장 프리필
    """
    mode = request.args.get("mode", "manual")
    if mode not in ("manual", "ai"):
        mode = "manual"

    title = (request.args.get("title") or "").strip()
    prefill = (request.args.get("prefill") or "").strip()

    return render_template("editor.html", mode=mode, title=title, prefill=prefill)

@ui_bp.get("/images")
def images():
    """
    이미지 생성/미리보기 화면.
    쿼리:
      - title: 문자열
      - pages: JSON 배열 문자열 (페이지별 문장)
    """
    title = (request.args.get("title") or "").strip()
    pages_json = (request.args.get("pages") or "").strip()
    return render_template("images.html", title=title, pages_json=pages_json)
