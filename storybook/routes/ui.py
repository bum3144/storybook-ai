from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify

ui_bp = Blueprint("ui", __name__)

@ui_bp.get("/preview")
def preview():
    data = session.get("preview")  # {'title': str, 'pages': [{'index', 'text', 'url'}]}
    if not data or not data.get("pages"):
        # 이미지가 아직 없으면 이미지 생성 화면으로
        return redirect(url_for("ui.images"))
    # index 오름차순 보장
    pages = sorted(data["pages"], key=lambda x: x["index"])
    return render_template("preview.html", title=data.get("title", ""), pages=pages)

# 새 스토리 선택(대시보드에서 오는 진입점)
@ui_bp.get("/new")
def new():
    return render_template("new.html")

# 대시보드(프로젝트 홈)
@ui_bp.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# 글 편집기 (mode=write | mode=ai)
@ui_bp.get("/editor")
def editor():
    mode = (request.args.get("mode") or "write").lower()
    return render_template("editor.html", mode=mode)

# 에디터 → 이미지 단계로 넘길 캐시 저장 (세션)
@ui_bp.post("/editor/cache")
def editor_cache():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    pages = data.get("pages") or []
    count = int(data.get("count") or len(pages) or 0)

    # 방어
    pages = [str(p or "").strip() for p in pages][:5]
    if count <= 0:
        count = len(pages)

    session["editor_cache"] = {
        "title": title,
        "pages": pages,
        "count": count,
    }
    session.modified = True
    return jsonify({"ok": True})

# 이미지 생성 페이지
@ui_bp.get("/images")
def images():
    cache = session.get("editor_cache") or {}
    pages = cache.get("pages") or []
    count = int(cache.get("count") or len(pages) or 0)
    title = cache.get("title") or ""

    # 페이지 인덱스/텍스트 형태로 템플릿에 넘김
    page_items = [{"index": i+1, "text": (pages[i] if i < len(pages) else "")}
                  for i in range(max(count, len(pages), 0))]

    # 스타일 드롭다운 기본값은 템플릿에서 처리
    return render_template("images.html",
                           title=title,
                           pages=page_items,
                           style="동화 일러스트 (기본)")