# storybook/routes/api.py
from __future__ import annotations
from typing import List
from flask import Blueprint, request, jsonify

from storybook.providers.gemini_provider import GeminiProvider
from storybook.providers.image_provider import ImageProvider
from storybook.repositories.story_repo_file import StoryFileRepository

api_bp = Blueprint("api", __name__)


# ----- 한국어 조사 간단 보정 -------------------------------------------------
def _has_final_consonant(word: str) -> bool:
    if not word:
        return False
    ch = word[-1]
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return ((code - 0xAC00) % 28) != 0
    return False


def _eul_reul(noun: str) -> str:
    return "을" if _has_final_consonant(noun) else "를"


def _prettify_lines_with_josa(lines: List[str]) -> List[str]:
    # "1. '사과'..." 형태를 간단히 보정
    out: List[str] = []
    for line in lines:
        try:
            num, rest = line.split(". ", 1)
            kw = rest.split("'")[1]
            out.append(f"{num}. '{kw}'{_eul_reul(kw)} 주제로 한 장면.")
        except Exception:
            out.append(line)
    return out


# ----- 스토리 텍스트 생성(목업) ----------------------------------------------
@api_bp.post("/story")
def generate_story():
    """
    입력: { "keywords": ["사과","숲"], "pages": 3, "withImages": true }
    출력: { "title": "맞춤 동화(초안)", "pages": [...], "images": [...] }
    """
    data = request.get_json(force=True, silent=True) or {}
    page_count = max(1, min(int(data.get("pages", 3) or 3), 5))

    raw_keywords = data.get("keywords") or []
    keywords = [k.strip() for k in raw_keywords if isinstance(k, str) and k.strip()]
    with_images = bool(data.get("withImages", False))

    llm = GeminiProvider(api_key=None)  # 실제 연동 전 목업
    lines = llm.suggest_pages(keywords, page_count)
    lines = _prettify_lines_with_josa(lines)

    resp = {"title": "맞춤 동화(초안)", "pages": lines}

    if with_images:
        imgp = ImageProvider()
        resp["images"] = imgp.images_for_keywords(keywords, limit=page_count)

    return jsonify(resp)


# ----- 스토리 저장(파일) -----------------------------------------------------
@api_bp.post("/story/save")
def save_story():
    """
    입력: { "title": "...", "pages": [...], "images": [...] }
    출력: { "saved": true, "path": "/abs/path/story_YYYYMMDD_HHMMSS.json" }
    """
    payload = request.get_json(force=True, silent=True) or {}
    repo = StoryFileRepository()
    path = repo.save(payload)
    return jsonify({"saved": True, "path": path})


# ----- 이미지 생성 API --------------------------------------------------------
@api_bp.post("/images/generate")
def generate_images():
    """
    입력:
      {
        "pages": ["1. ...", "2. ..."],   # 페이지별 한 줄 문장
        "style": "storybook illustration" # 선택형 스타일(옵션)
      }
    출력:
      {
        "images": ["https://...", "https://...", ...]
      }
    """
    data = request.get_json(force=True, silent=True) or {}

    # pages는 리스트 형태만 허용
    raw_pages = data.get("pages") or []
    if not isinstance(raw_pages, list):
        return jsonify({"error": "pages must be a list"}), 400

    # 최대 5장 제한
    pages: List[str] = [str(p).strip() for p in raw_pages if str(p).strip()][:5]
    if not pages:
        return jsonify({"error": "pages is empty"}), 400

    # 스타일 힌트(Optional). 현재는 간단한 접미어로만 사용
    style_hint = (data.get("style") or "").strip()

    # 간단 매핑: 페이지 문장 안의 핵심 단어를 프롬프트 키워드로 사용
    keywords: List[str] = []
    for line in pages:
        try:
            # "1. '사과'를 주제로 한 장면." 에서 사과 추출
            kw = line.split("'")[1]
        except Exception:
            kw = line
        if style_hint:
            kw = f"{kw}, {style_hint}"
        keywords.append(kw)

    imgp = ImageProvider()
    urls = imgp.images_for_keywords(keywords, limit=len(pages))

    return jsonify({"images": urls})