# storybook/routes/ui.py
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import storybook.database.db as db

ui_bp = Blueprint("ui", __name__)


@ui_bp.get("/dashboard")
@ui_bp.get("/")
def dashboard():
    raw_stories = db.get_all_stories()
    stories = []
    for s in raw_stories:
        detail = db.get_story_detail(s['id'])
        thumb = None
        if detail and detail['pages']:
            for p in detail['pages']:
                if p.get('image_url'):
                    thumb = p['image_url']
                    break
        stories.append({
            "id": s['id'],
            "title": s['title'],
            "genre": s['genre'],
            "created_at": s['created_at'],
            "thumb_url": thumb
        })
    return render_template("dashboard.html", stories=stories)


@ui_bp.get("/editor")
def editor():
    mode = (request.args.get("mode") or "write").lower()
    return render_template("editor.html", mode=mode)


# [수정] 임시 저장 시, 기존에 생성된 이미지 세션(preview)을 초기화합니다.
@ui_bp.post("/editor/cache")
def editor_cache():
    data = request.get_json(silent=True) or {}
    session["editor_cache"] = data

    # ★ 핵심 수정: 새 내용을 작성 중이므로, 기존 이미지 세션은 비워줍니다.
    session.pop("preview", None)

    return jsonify({"ok": True})


@ui_bp.get("/images")
def images():
    cache = session.get("editor_cache") or {}
    title = cache.get("title", "")
    pages_text = cache.get("pages") or []

    # preview 세션이 삭제되었으므로, 처음엔 이미지가 없는 상태로 시작합니다.
    preview_data = session.get("preview") or {}
    preview_pages = preview_data.get("pages") or []

    page_items = []
    for i, p_data in enumerate(pages_text):
        txt = p_data if isinstance(p_data, str) else p_data.get("text", "")
        idx = i + 1

        img_url = ""
        for pp in preview_pages:
            if pp.get("index") == idx:
                img_url = pp.get("url", "")
                break

        page_items.append({
            "index": idx,
            "text": txt,
            "url": img_url
        })

    return render_template("images.html", title=title, pages=page_items, style="동화 일러스트 (기본)")


@ui_bp.get("/preview/<int:story_id>")
def preview_saved(story_id):
    story = db.get_story_detail(story_id)
    if not story:
        return "동화를 찾을 수 없습니다.", 404

    pages = []
    for p in story['pages']:
        pages.append({
            "index": p['page_index'],
            "text": p['text'],
            "url": p['image_url']
        })

    return render_template("preview.html",
                           title=story['title'],
                           pages=pages,
                           story_id=story['id'])