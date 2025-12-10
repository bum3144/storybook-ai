# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, session
import requests
import random  # (현재 직접 사용은 안 하지만 남겨둬도 무방)
import time
import hashlib

from storybook.providers.gemini_provider import GeminiProvider

api_bp = Blueprint("api", __name__, url_prefix="/api")

# 1차 목업 소스(간헐적 5xx 가능)
PICSUM_TMPL = "https://picsum.photos/seed/{seed}/800/1000"
# 실패 시 대체
PLACEHOLDER_TMPL = "https://placehold.co/800x1000?text=Image%20{idx}"

# 연결 재사용을 위한 세션
_http = requests.Session()
_gemini = GeminiProvider()
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


@api_bp.post("/plot/generate")
def generate_plot():
    """
    에디터에서 보낸 스토리 메타 + 페이지 정보를 이용해
    각 페이지별 '동화 스토리 문장'을 만들어 반환합니다.

    요청 JSON 예:
    {
      "meta": {
        "title": "우주여행1",
        "genre": "모험",
        "world": "우주",
        "theme": "용기",
        "hero": "소년 케빈"
      },
      "pages": [
        {
          "index": 0,
          "text": "",
          "keywords": ["로켓", "작업실", "밤"],
          "continue": true,
          "previous_text": ""
        },
        ...
      ]
    }

    응답 JSON 예:
    {
      "pages": [
        {"index": 0, "text": "실제 스토리 문장..."},
        ...
      ]
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    meta = data.get("meta") or {}
    pages = data.get("pages") or []

    hero = (meta.get("hero") or "").strip() or "주인공"
    genre = (meta.get("genre") or "").strip()
    world = (meta.get("world") or "").strip()
    theme = (meta.get("theme") or "").strip()

    total = max(1, len(pages))

    def build_page_story(i, page, prev_story: str) -> str:
        idx = int(page.get("index", i))
        keywords = [str(k).strip() for k in (page.get("keywords") or []) if str(k).strip()]
        cont = bool(page.get("continue", True))

        # 키워드 문구
        if keywords:
            if len(keywords) == 1:
                kw_phrase = f"‘{keywords[0]}’"
            else:
                kw_phrase = "‘" + "’, ‘".join(keywords) + "’"
        else:
            kw_phrase = "특별한 무언가"

        # 장면 단계에 따라 분위기 설정
        if total == 1:
            stage_idx = 0
        else:
            stage_idx = round((i / (total - 1)) * 4)
        stage_idx = max(0, min(4, stage_idx))

        world_part = f"{world}에서 " if world else ""
        theme_part = ""
        if theme:
            theme_part = f" 이 순간, {hero}는 서서히 '{theme}'의 의미를 깨닫기 시작합니다."

        # 페이지별 기본 문장 패턴
        if i == 0:
            # 1페이지: 시작 장면
            first = (
                f"{world_part}{hero}는 {kw_phrase}을(를) 바라보며 "
                f"특별한 모험이 시작될 것 같은 예감을 받습니다."
            )
            second = " 평범했던 하루가 조용히 흔들리기 시작한 그때, 작은 선택 하나가 모든 것을 바꾸려 하고 있었습니다."
        else:
            # 2페이지 이후
            if cont and prev_story:
                lead = "앞선 장면에서 이어져, "
            else:
                lead = "새로운 장면에서, "

            if stage_idx <= 1:
                first = (
                    f"{lead}{hero}는 {world_part}{kw_phrase}과(와) 함께 "
                    f"조금 더 깊숙한 모험 속으로 발을 내딛습니다."
                )
                second = " 가슴이 두근거리지만, 동시에 기대와 설렘이 뒤섞여 눈을 반짝입니다."
            elif stage_idx <= 2:
                first = (
                    f"{lead}{world_part}{kw_phrase} 때문에 "
                    f"{hero} 앞에 예상치 못한 일이 벌어집니다."
                )
                second = " 당황한 표정을 지으면서도, {0}는 물러서지 않고 한 걸음 더 앞으로 나아갑니다.".format(hero)
            elif stage_idx <= 3:
                first = (
                    f"{lead}{hero}는 {world_part}{kw_phrase} 속에서 "
                    f"지금까지와는 비교도 할 수 없는 큰 위기를 맞이합니다."
                )
                second = " 하지만 포기하지 않으려는 마음이 점점 더 커지며, 마지막 힘을 끌어모읍니다."
            else:
                first = (
                    f"{lead}{world_part}{kw_phrase}과(와) 함께 "
                    f"{hero}의 모험은 서서히 끝을 향해 다가갑니다."
                )
                second = " 긴 여정을 지나온 만큼, {0}의 눈빛에는 이전보다 한층 단단해진 마음이 담겨 있습니다.".format(hero)

        story = first + second + theme_part
        return story

    results = []
    prev_story_text = ""
    for i, page in enumerate(pages):
        text = build_page_story(i, page, prev_story_text)
        results.append({"index": int(page.get("index", i)), "text": text})
        prev_story_text = text

    return jsonify({"pages": results}), 200



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