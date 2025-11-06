# storybook/routes/api.py
from __future__ import annotations
from typing import List
from flask import Blueprint, request, jsonify

from storybook.providers.gemini_provider import GeminiProvider
from storybook.providers.image_provider import ImageProvider
from storybook.repositories.story_repo_file import StoryFileRepository

api_bp = Blueprint("api", __name__)

# 조사 보정(을/를)
def has_final_consonant(word: str) -> bool:
    if not word: return False
    ch = word[-1]; code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return ((code - 0xAC00) % 28) != 0
    return False

def josa_eul_reul(noun: str) -> str:
    return "을" if has_final_consonant(noun) else "를"

def prettify_lines_with_josa(lines: List[str]) -> List[str]:
    """기존 목업 포맷을 조사 보정 버전으로 정리(선택)."""
    out = []
    for line in lines:
        # "1. '사과'..." 형태라 가볍게 처리
        try:
            num, rest = line.split(". ", 1)
            kw = rest.split("'")[1]  # 따옴표 사이 단어 추출
            particle = josa_eul_reul(kw)
            out.append(f"{num}. '{kw}'{particle} 주제로 한 장면.")
        except Exception:
            out.append(line)
    return out

@api_bp.post("/story")
def generate_story():
    """
    입력: { "keywords": ["씨앗","숲","친구"], "pages": 3, "withImages": true }
    출력: {
      "title": "...",
      "pages": ["1. ...", "2. ..."],
      "images": ["https://...", "..."]  # withImages=true일 때만
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    page_count = max(1, min(int(data.get("pages", 3) or 3), 5))
    raw_keywords = data.get("keywords") or []
    keywords = [k.strip() for k in raw_keywords if isinstance(k, str) and k.strip()]
    with_images = bool(data.get("withImages", False))

    # 1) 텍스트 생성 (지금은 GeminiProvider의 목업 사용)
    llm = GeminiProvider(api_key=None)
    lines = llm.suggest_pages(keywords, page_count)
    lines = prettify_lines_with_josa(lines)

    resp = {
        "title": "맞춤 동화(초안)",
        "keywords": keywords,
        "pages": lines
    }

    # 2) 이미지 URL 생성 (선택)
    if with_images:
        imgp = ImageProvider()
        resp["images"] = imgp.images_for_keywords(keywords, limit=page_count)

    return jsonify(resp)

@api_bp.post("/story/save")
def save_story():
    """
    입력: { "title": "...", "pages": [...], "images": [...] }
    출력: { "saved": true, "path": "/abs/path/to/file.json" }
    """
    payload = request.get_json(force=True, silent=True) or {}
    repo = StoryFileRepository()
    path = repo.save(payload)
    return jsonify({"saved": True, "path": path})
