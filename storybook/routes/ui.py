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


# 에디터 데이터 임시 저장
@ui_bp.post("/editor/cache")
def editor_cache():
    data = request.get_json(silent=True) or {}
    session["editor_cache"] = data
    # 새 작성 시 기존 미리보기 세션 초기화
    session.pop("preview", None)
    return jsonify({"ok": True})


@ui_bp.get("/images")
def images():
    cache = session.get("editor_cache") or {}
    title = cache.get("title", "")
    pages_text = cache.get("pages") or []

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

    # [수정] 표지 정보 조회 추가
    cover = db.get_cover(story_id)

    pages = []
    for p in story['pages']:
        pages.append({
            "index": p['page_index'],
            "text": p['text'],
            "url": p['image_url']
        })

    # 템플릿에 cover 데이터 전달
    return render_template("preview.html",
                           title=story['title'],
                           pages=pages,
                           story_id=story['id'],
                           cover=cover)


# 표지 만들기 화면
@ui_bp.get("/cover/<int:story_id>")
def cover_editor(story_id):
    story = db.get_story_detail(story_id)
    if not story:
        return "동화를 찾을 수 없습니다.", 404

    cover = db.get_cover(story_id)

    return render_template("cover.html", story=story, cover=cover)