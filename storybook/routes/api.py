# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, session
import requests
import random  # (현재 직접 사용은 안 하지만 남겨둬도 무방)
import time
import hashlib

api_bp = Blueprint("api", __name__, url_prefix="/api")

# 1차 목업 소스(간헐적 5xx 가능)
PICSUM_TMPL = "https://picsum.photos/seed/{seed}/800/1000"
# 실패 시 대체
PLACEHOLDER_TMPL = "https://placehold.co/800x1000?text=Image%20{idx}"

# 연결 재사용을 위한 세션
_http = requests.Session()
_http.headers.update({"User-Agent": "storybook-dev/0.1"})


# ------------------------------
# A) 편집기 데이터 -> 서버 세션 캐시
# ------------------------------
@api_bp.post("/editor/cache")
def editor_cache():
    """
    요청 바디 예:
      {
        "style": "동화 일러스트 (기본)",
        "pages": [
          {"index": 1, "text": "장면1"},
          {"index": 2, "text": "장면2"},
          ...
        ]
      }
    동작: style/pages를 서버 세션에 저장.
    응답:
      { "ok": true, "count": <페이지수> }
    """
    payload = request.get_json(silent=True) or {}
    style = (payload.get("style") or "").strip()
    pages = payload.get("pages") or []

    # 간단 검증/정리
    norm_pages = []
    for p in pages:
        try:
            idx = int(p.get("index"))
        except Exception:
            continue
        norm_pages.append({"index": idx, "text": (p.get("text") or "").strip()})
    norm_pages.sort(key=lambda x: x["index"])

    # 세션 저장
    session["story_style"] = style
    session["story_pages"] = norm_pages

    return jsonify({"ok": True, "count": len(norm_pages)}), 200


@api_bp.get("/editor/cached")
def editor_cached():
    """
    디버그/확인용: 세션에 저장된 pages/style 확인
    """
    return jsonify({
        "style": session.get("story_style"),
        "pages": session.get("story_pages") or []
    }), 200


# ------------------------------
# B) 목업 이미지 생성(네가 올린 구현 유지)
# ------------------------------
def _quick_ok(url: str, timeout_sec: float = 3.5) -> bool:
    """외부 URL 가용성 빠른 점검. 실패/5xx/타임아웃 => False"""
    try:
        # 일부 서비스가 HEAD 막아 GET 사용 (stream=True로 바디 미수신)
        with _http.get(url, timeout=timeout_sec, stream=True) as r:
            return 200 <= r.status_code < 300
    except Exception:
        return False


def _safe_url(primary_url: str, idx: int, tries: int = 2) -> str:
    """
    primary를 짧게 확인 후 실패하면 소폭 재시도, 그래도 실패면 placeholder 반환.
    """
    for attempt in range(tries):
        if _quick_ok(primary_url, timeout_sec=3.5):
            return primary_url
        # 아주 짧게 간격
        time.sleep(0.15 * (attempt + 1))
    return PLACEHOLDER_TMPL.format(idx=idx)


@api_bp.post("/images/generate")
def images_generate():
    payload = request.get_json(silent=True) or {}
    pages_in = payload.get("pages") or []
    style = (payload.get("style") or "").strip()

    out = []
    preview_pages = []  # <-- 미리보기 저장용

    for p in pages_in:
        try:
            idx = int(p.get("index"))
        except Exception:
            continue
        text = (p.get("text") or "").strip()

        seed_src = f"{style}|{text}|{idx}"
        seed = hashlib.sha1(seed_src.encode("utf-8")).hexdigest()[:12]
        primary = PICSUM_TMPL.format(seed=seed)
        url = _safe_url(primary, idx, tries=2)

        out.append({"index": idx, "url": url})
        preview_pages.append({"index": idx, "text": text, "url": url})

        time.sleep(0.02)

    out.sort(key=lambda x: x["index"])
    preview_pages.sort(key=lambda x: x["index"])

    # 에디터에서 저장한 초안에서 제목 가져오기
    title = ""
    draft = session.get("draft") or {}
    if isinstance(draft, dict):
        title = draft.get("title", "")

    # 세션에 미리보기 저장
    session["preview"] = {"title": title, "pages": preview_pages}

    return jsonify({"images": out}), 200