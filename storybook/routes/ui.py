# storybook/routes/ui.py
from __future__ import annotations

from flask import Blueprint, render_template, request, session

ui_bp = Blueprint("ui", __name__, template_folder="../templates", static_folder="../static")


@ui_bp.get("/")
def home():
    return (
        "AI 그림동화 생성기 서버가 실행 중입니다.<br/>👉 "
        '<a href="/dashboard">/dashboard</a> 로 이동하세요.'
    )


@ui_bp.get("/dashboard")
def dashboard():
    """
    대시보드 화면.
    - 샘플/저장본 리스트 + “+ 새 스토리 만들기” 버튼
    - 템플릿: dashboard.html
    """
    return render_template("dashboard.html")


@ui_bp.get("/new")
def new_story_entry():
    """
    새 스토리 만들기 화면.
    - '직접 쓰기' / 'AI와 함께 쓰기' 카드 2개
    - 템플릿: new.html
    """
    return render_template("new.html")


@ui_bp.get("/editor")
def editor():
    """
    글 편집 화면.
    - mode=write : '직접 쓰기' (AI 추천 섹션 숨김)
    - mode=ai    : 'AI와 함께 쓰기' (AI 추천 섹션 표시)
    """
    mode = (request.args.get("mode") or "ai").strip().lower()
    if mode not in ("ai", "write"):
        mode = "ai"

    draft = session.get("draft") or {
        "title": "",
        "pages": [],
        "page_count": 3,
        "keywords": "",
    }

    try:
        page_count = int(draft.get("page_count", 3))
    except Exception:
        page_count = 3
    page_count = max(1, min(page_count, 5))

    pages = list(draft.get("pages") or [])
    if len(pages) < page_count:
        pages += [""] * (page_count - len(pages))
    else:
        pages = pages[:page_count]

    return render_template(
        "editor.html",
        mode=mode,
        title=draft.get("title", ""),
        page_count=page_count,
        pages=pages,
        keywords=draft.get("keywords", ""),
    )


@ui_bp.get("/images")
def images():
    """
    이미지 생성 화면. 세션 임시 저장본에서 페이지 텍스트 사용.
    """
    draft = session.get("draft") or {}
    pages = (draft.get("pages") or [])[:5]

    styles = [
        "동화 일러스트 (기본)",
        "연필 스케치",
        "수채화 파스텔",
        "평면 벡터",
    ]

    return render_template(
        "images.html",
        pages=pages,
        styles=styles,
    )