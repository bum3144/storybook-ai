from flask import Blueprint, request, jsonify, session
from typing import Any, Dict, List

import requests
import random
import time
import hashlib
import os  # <--- 추가됨

from storybook.providers.gemini_provider import GeminiProvider
from storybook.providers.image_provider import ImageProvider

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

# ------------------------------
# A) AI 스토리 플롯 생성 (목업 / LLM 교체용)
# ------------------------------
def _generate_story_pages_mock(meta: Dict[str, str], pages: List[Dict[str, Any]]) -> List[Dict[str, str]]:

    def pick_main(value: str) -> str:
        """
        콤마로 구분된 문자열이라면 첫 번째 항목만 사용.
        예: '바다, 숲속, 우주' -> '바다'
        """
        if not value:
            return ""
        parts = [p.strip() for p in value.split(",") if p.strip()]
        return parts[0] if parts else value.strip()

    raw_title = (meta.get("title") or "").strip()
    raw_genre = (meta.get("genre") or "").strip()
    raw_world = (meta.get("world") or "").strip()
    raw_theme = (meta.get("theme") or "").strip()
    raw_hero  = (meta.get("hero")  or "").strip()

    title = pick_main(raw_title)
    genre = pick_main(raw_genre)
    world = pick_main(raw_world)
    theme = pick_main(raw_theme)
    hero  = pick_main(raw_hero) or "주인공"


    total = max(1, len(pages))

    stage_texts = [
        "이제 막 이야기가 시작되는 순간입니다.",
        "모험의 흐름이 조금씩 빨라지기 시작합니다.",
        "뜻밖의 사건으로 이야기가 크게 흔들립니다.",
        "가장 긴장되는 장면이 펼쳐지고 있습니다.",
        "이야기는 서서히 따뜻한 결말을 향해 나아갑니다.",
    ]

    def split_keywords(raw_list):
        kws = [str(k).strip() for k in (raw_list or []) if str(k).strip()]
        if not kws:
            return "", ""
        main = kws[0]
        if len(kws) == 1:
            return main, ""
        rest = kws[1:]
        if len(rest) == 1:
            rest_phrase = rest[0]
        else:
            rest_phrase = ", ".join(rest[:-1]) + " 그리고 " + rest[-1]
        return main, rest_phrase

    def build_page_story(i: int, page: Dict[str, Any]) -> Dict[str, str]:
        raw_kws = page.get("keywords") or []
        main_kw, rest_kw = split_keywords(raw_kws)

        if total == 1:
            stage_idx = 0
        else:
            stage_idx = round((i / (total - 1)) * 4)
        stage_idx = max(0, min(4, stage_idx))

        world_prefix = f"{world}에서 " if world else ""
        first: str

        # --- 장면 구성 ---
        if i == 0:
            # 시작 장면
            if main_kw:
                if rest_kw:
                    first = (
                        f"{world_prefix}{hero}는 {main_kw} 속에서 하루하루를 보내며, "
                        f"{rest_kw}에 대한 생각으로 가슴이 두근거리기 시작합니다."
                    )
                else:
                    first = (
                        f"{world_prefix}{hero}는 {main_kw}을(를) 바라보며 "
                        f"곧 특별한 모험이 시작될 것 같은 예감을 받습니다."
                    )
            else:
                first = (
                    f"{world_prefix}{hero}는 아직 이름 붙일 수 없는 무언가를 향해 "
                    f"조용히 마음이 끌리는 것을 느낍니다."
                )
        else:
            # 중간 이후 장면들
            if stage_idx <= 1:
                # 초반 전개
                if main_kw:
                    first = (
                        f"{world_prefix}{hero}는 {main_kw}과(와) 함께 "
                        f"조금 더 깊은 모험 속으로 발을 내딛습니다."
                    )
                else:
                    first = (
                        f"{world_prefix}{hero}의 발걸음은 서서히 모험의 중심으로 향하고 있습니다."
                    )
            elif stage_idx <= 2:
                # 사건 발생
                if main_kw:
                    if rest_kw:
                        first = (
                            f"{world_prefix}{hero} 앞에 {main_kw}와(과) "
                            f"{rest_kw}이(가) 얽힌 예상치 못한 일이 벌어집니다."
                        )
                    else:
                        first = (
                            f"{world_prefix}{hero} 앞에 {main_kw} 때문에 "
                            f"예상치 못한 일이 벌어집니다."
                        )
                else:
                    first = (
                        f"{world_prefix}{hero}는 갑작스러운 사건을 맞이해 당황하고 맙니다."
                    )
            elif stage_idx <= 3:
                # 클라이맥스
                if main_kw:
                    first = (
                        f"{world_prefix}{hero}는 {main_kw} 속에서 "
                        f"지금까지와는 비교할 수 없는 큰 위기에 맞섭니다."
                    )
                else:
                    first = (
                        f"{world_prefix}{hero}는 드디어 가장 큰 시련과 마주하게 됩니다."
                    )
            else:
                # 마무리
                if main_kw:
                    first = (
                        f"{world_prefix}{hero}는 {main_kw}과(와) 함께 "
                        f"긴 모험의 끝자락에 서서 오늘을 되돌아봅니다."
                    )
                else:
                    first = (
                        f"{world_prefix}{hero}는 긴 여정을 지나온 뒤, "
                        f"조용히 숨을 고르며 마음을 정리합니다."
                    )

        second = stage_texts[stage_idx]
        text = first + " " + second

        if theme:
            text += f" 이 장면 속에서도 {hero}는 '{theme}'의 의미를 조금씩 깨닫고 있습니다."

        return {
            "index": int(page.get("index", i)),
            "text": text,
        }

    result: List[Dict[str, str]] = []
    for i, page in enumerate(pages):
        result.append(build_page_story(i, page))

    return result


# ------------------------------
# 새로운 스위치 로직 (Mock vs Gemini)
# ------------------------------
def _generate_story_pages(meta: Dict[str, str], pages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    환경변수 설정에 따라 Gemini를 쓸지, Mock을 쓸지 결정하는 스위치 함수입니다.
    """
    use_gemini = os.environ.get("USE_GEMINI_TEXT") == "1"

    # GeminiProvider가 사용 가능한지(키가 있는지) 확인
    provider = GeminiProvider()

    if use_gemini and provider.is_available():
        try:
            print("✨ Gemini API를 사용하여 스토리를 생성합니다...")
            return provider.generate_story(meta, pages)
        except Exception as e:
            print(f"⚠️ Gemini 생성 실패 (Mock으로 전환): {e}")
            # 실패하면 아래 Mock으로 넘어갑니다.

    # 기본값 또는 실패 시 Mock 사용
    print("🤖 Mock 엔진을 사용하여 스토리를 생성합니다.")
    return _generate_story_pages_mock(meta, pages)

@api_bp.post("/plot/generate")
def plot_generate():
    """
    에디터에서 보낸 메타 + 페이지 정보를 받아
    페이지별 스토리 한 단락을 생성해 반환.

    요청 JSON 예:
    {
      "meta": {
        "title": "우주여행1",
        "genre": "모험",
        "world": "우주",
        "theme": "용기",
        "hero": "토르"
      },
      "pages": [
        { "index": 0, "keywords": ["로켓", "발사장"], "text": "" },
        { "index": 1, "keywords": ["지구", "우주정거장"], "text": "" },
        ...
      ]
    }

    응답 JSON 예:
    {
      "pages": [
        { "index": 0, "text": "..." },
        { "index": 1, "text": "..." },
        ...
      ]
    }
    """
    payload = request.get_json(silent=True) or {}
    meta = payload.get("meta") or {}
    pages = payload.get("pages") or []

    if not isinstance(pages, list) or not pages:
        return jsonify({"error": "no pages"}), 400

    result_pages = _generate_story_pages(meta, pages)
    return jsonify({"pages": result_pages}), 200




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


# ------------------------------
# B) 이미지 생성 API (Real AI 연결)
# ------------------------------
@api_bp.post("/images/generate")
def images_generate():
    payload = request.get_json(silent=True) or {}
    pages_in = payload.get("pages") or []
    style = (payload.get("style") or "동화 일러스트").strip()

    img_provider = ImageProvider()
    gemini_provider = GeminiProvider()

    out = []
    preview_pages_update = []

    print(f"🎨 이미지 생성 요청: {len(pages_in)}장 / 스타일: {style}")

    # ---------------------------------------------------------
    # [최적화] 1. 한글 텍스트만 쏙 뽑아서 한 번에 번역 요청 (1 API Call)
    # ---------------------------------------------------------
    korean_texts = []
    # 나중에 매칭하기 위해 유효한 인덱스만 추림
    valid_pages = []

    for p in pages_in:
        try:
            idx = int(p.get("index"))
            txt = (p.get("text") or "").strip()
            korean_texts.append(txt)
            valid_pages.append({"index": idx, "original_text": txt})
        except:
            continue

    # 여기서 한 번에 번역! (속도 UP, 할당량 절약)
    english_prompts = gemini_provider.translate_prompts_bulk(korean_texts)

    # ---------------------------------------------------------
    # 2. 번역된 프롬프트로 이미지 생성
    # ---------------------------------------------------------
    for i, page_data in enumerate(valid_pages):
        idx = page_data["index"]
        k_text = page_data["original_text"]

        # 번역된 거 가져오기 (혹시 에러나서 리스트 길이가 안 맞으면 원본 사용)
        if i < len(english_prompts):
            visual_prompt = english_prompts[i]
        else:
            visual_prompt = "storybook scene"

        full_prompt = f"({style} style), {visual_prompt}"

        # 이미지 URL 생성 (Pollinations는 제한 없음)
        url = img_provider.build_image_url(full_prompt)

        out.append({"index": idx, "url": url})
        preview_pages_update.append({"index": idx, "text": k_text, "url": url})

        # 서버 부하 방지 (번역은 끝났으니 이미지 생성 간격은 짧게)
        time.sleep(0.2)

    out.sort(key=lambda x: x["index"])

    # 세션 업데이트 로직 (기존과 동일)
    current_preview = session.get("preview") or {}
    if not current_preview:
        cache = session.get("editor_cache") or {}
        current_preview = {"title": cache.get("title", ""), "pages": []}

    existing_map = {p["index"]: p for p in current_preview.get("pages", [])}
    for new_p in preview_pages_update:
        existing_map[new_p["index"]] = new_p

    updated_pages = sorted(existing_map.values(), key=lambda x: x["index"])

    session["preview"] = {
        "title": current_preview.get("title", ""),
        "pages": updated_pages
    }
    session.modified = True

    return jsonify({"images": out}), 200