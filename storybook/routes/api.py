# storybook/routes/api.py
from __future__ import annotations
from typing import List
from flask import Blueprint, request, jsonify

from storybook.providers.gemini_provider import GeminiProvider
from storybook.providers.image_provider import ImageProvider
from storybook.repositories.story_repo_file import StoryFileRepository

api_bp = Blueprint("api", __name__)

# ---- 조사 보정 유틸 ---------------------------------------------------------
def has_final_consonant(word: str) -> bool:
    if not word:
        return False
    ch = word[-1]
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return ((code - 0xAC00) % 28) != 0
    return False

def josa_eul_reul(noun: str) -> str:
    return "을" if has_final_consonant(noun) else "를"

def prettify_lines_with_josa(lines: List[str]) -> List[str]:
    out = []
    for line in lines:
        try:
            num, rest = line.split(". ", 1)
            kw = rest.split("'")[1]  # 따옴표 사이 단어 추출
            particle = josa_eul_reul(kw)
            out.append(f"{num}. '{kw}'{particle} 주제로 한 장면.")
        except Exception:
            out.append(line)
    return out

# ---- 스토리 텍스트 생성 ------------------------------------------------------
@api_bp.post("/story")
def generate_story():
    """
    입력:  { "keywords": ["씨앗","숲","친구"], "pages": 3, "withImages": true }
    출력:  { "title": "맞춤 동화(초안)", "pages": ["1. ...","2. ..."], "images": [...] }
    """
    data = request.get_json(force=True, silent=True) or {}
    page_count = max(1, min(int(data.get("pages", 3) or 3), 5))
    raw_keywords = data.get("keywords") or []
    keywords = [k.strip() for k in raw_keywords if isinstance(k, str) and k.strip()]
    with_images = bool(data.get("withImages", False))

    llm = GeminiProvider(api_key=None)
    lines = llm.suggest_pages(keywords, page_count)
    lines = prettify_lines_with_josa(lines)

    resp = {"title": "맞춤 동화(초안)", "pages": lines}

    if with_images:
        imgp = ImageProvider()
        resp["images"] = imgp.images_for_keywords(keywords, limit=page_count)

    return jsonify(resp)

# ---- 스토리 저장 -------------------------------------------------------------
@api_bp.post("/story/save")
def save_story():
    """
    입력:  { "title": "...", "pages": [...], "images": [...] }
    출력:  { "saved": true, "path": "/abs/path/to/file.json" }
    """
    payload = request.get_json(force=True, silent=True) or {}
    repo = StoryFileRepository()
    path = repo.save(payload)
    return jsonify({"saved": True, "path": path})

# ---- 이미지 생성(목업 URL) ---------------------------------------------------
@api_bp.post("/images/generate")  # <-- 여기! url_prefix="/api" 기준으로 상대경로
def generate_images():
    """
    입력(JSON): {
      "pages": ["1. '사과'를 주제로 한 장면.", ...],  # 권장
      # 또는 "texts": [ ... ]                         # 호환
      "style": "storybook_basic",                     # 선택
      "only_indices": [0,2]                           # 선택(부분 재생성)
    }
    출력(JSON): { "images": [url 또는 null ...] }  # 원래 길이에 맞춘 배열
    """
    data = request.get_json(force=True, silent=True) or {}

    pages: List[str] = data.get("pages") or data.get("texts") or []
    if not isinstance(pages, list) or len(pages) == 0:
        return jsonify({"error": "pages(list) is required"}), 400

    only_indices = data.get("only_indices")
    if isinstance(only_indices, list):
        targets = [i for i in only_indices if isinstance(i, int) and 0 <= i < len(pages)]
        if not targets:
            targets = list(range(len(pages)))
    else:
        targets = list(range(len(pages)))

    style = (data.get("style") or "").strip().lower()

    def extract_keyword(line: str) -> str:
        try:
            s = line.split("'")
            if len(s) >= 3 and s[1].strip():
                return s[1].strip()
        except Exception:
            pass
        return (line or "").strip() or "장면"

    def style_prefix(s: str) -> str:
        if "연필" in s or "pencil" in s:
            return "cute pencil sketch, "
        if "수채" in s or "watercolor" in s:
            return "soft watercolor illustration, "
        return "cute storybook illustration, "

    keywords = [extract_keyword(pages[i]) for i in targets]
    prompts = [f"{style_prefix(style)}{kw}, simple background, soft colors" for kw in keywords]

    imgp = ImageProvider()
    urls = [imgp.build_image_url(p) for p in prompts]

    full = [None] * len(pages)
    for local_i, page_i in enumerate(targets):
        full[page_i] = urls[local_i]

    return jsonify({"images": full})