# storybook/routes/api.py
from flask import Blueprint, request, jsonify, session
from typing import Any, Dict, List

import requests
import random
import time
import os

from storybook.providers.gemini_provider import GeminiProvider
from storybook.providers.image_provider import ImageProvider
import storybook.database.db as db

api_bp = Blueprint("api", __name__, url_prefix="/api")

# 연결 재사용을 위한 세션
_http = requests.Session()
_http.headers.update({"User-Agent": "storybook-dev/0.1"})


# ------------------------------
# A) 편집기 데이터 -> 서버 세션 캐시 (수정된 부분)
# ------------------------------
@api_bp.post("/editor/cache")
def editor_cache():
    payload = request.get_json(silent=True) or {}
    pages = payload.get("pages") or []

    # 1. 텍스트 데이터 세션에 저장
    session["editor_cache"] = payload

    # 2. [핵심 수정] 새 글을 작성 중이므로, 이전에 생성된 이미지(preview) 세션은 삭제합니다.
    #    이렇게 해야 이미지 생성 페이지로 넘어갔을 때 깨끗한 상태가 됩니다.
    session.pop("preview", None)

    return jsonify({"ok": True, "count": len(pages)}), 200


# ------------------------------
# B) AI 스토리 플롯 생성
# ------------------------------
@api_bp.post("/plot/generate")
def plot_generate():
    payload = request.get_json(silent=True) or {}
    meta = payload.get("meta") or {}
    pages = payload.get("pages") or []

    if not isinstance(pages, list) or not pages:
        return jsonify({"error": "no pages"}), 400

    # Gemini 사용 여부 확인
    use_gemini = True
    provider = GeminiProvider()

    if use_gemini and provider.is_available():
        try:
            print("✨ Gemini API를 사용하여 스토리를 생성합니다...")
            result_pages = provider.generate_story(meta, pages)
            return jsonify({"pages": result_pages}), 200
        except Exception as e:
            print(f"⚠️ Gemini 생성 실패: {e}")
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "API Key not found"}), 500


# ------------------------------
# C) 이미지 생성 API
# ------------------------------
@api_bp.post("/images/generate")
def images_generate():
    payload = request.get_json(silent=True) or {}
    pages_in = payload.get("pages") or []
    style = (payload.get("style") or "동화 일러스트").strip()

    img_provider = ImageProvider()
    gemini_provider = GeminiProvider()

    out = []

    # 1. 텍스트 추출
    korean_texts = []
    valid_pages = []
    for p in pages_in:
        try:
            idx = int(p.get("index"))
            txt = (p.get("text") or "").strip()
            korean_texts.append(txt)
            valid_pages.append({"index": idx, "original_text": txt})
        except:
            continue

    # 2. 번역 (Bulk)
    english_prompts = gemini_provider.translate_prompts_bulk(korean_texts)

    # 3. 이미지 생성
    for i, page_data in enumerate(valid_pages):
        idx = page_data["index"]

        # 번역된 프롬프트 매칭
        if i < len(english_prompts):
            visual_prompt = english_prompts[i]
        else:
            visual_prompt = "storybook scene"

        full_prompt = f"({style}), {visual_prompt}"

        # URL 생성
        url = img_provider.build_image_url(full_prompt)
        out.append({"index": idx, "url": url})

        time.sleep(0.1)  # 부하 조절

    # 세션 프리뷰 업데이트 (이미지 URL 저장)
    current_preview = session.get("preview") or {}
    prev_pages = current_preview.get("pages") or []

    # 기존 페이지 맵핑
    page_map = {p["index"]: p for p in prev_pages}

    # 새 이미지 정보 업데이트
    for new_img in out:
        idx = new_img["index"]
        if idx in page_map:
            page_map[idx]["url"] = new_img["url"]
        else:
            # 혹시 없으면 새로 만듦 (텍스트는 모름)
            page_map[idx] = {"index": idx, "url": new_img["url"], "text": ""}

    updated_pages = sorted(page_map.values(), key=lambda x: x["index"])

    session["preview"] = {
        "title": current_preview.get("title", session.get("editor_cache", {}).get("title", "")),
        "pages": updated_pages
    }
    session.modified = True

    return jsonify({"images": out}), 200


# ------------------------------
# D) 동화 최종 저장 API
# ------------------------------
@api_bp.post("/story/save")
def story_save():
    try:
        payload = request.get_json(silent=True) or {}
        title = payload.get("title", "제목 없음")
        pages = payload.get("pages", [])

        # 1. 스토리 DB 생성
        story_id = db.create_story(title=title, genre="동화", theme="자유")

        # 2. 페이지 DB 저장
        db_pages = []
        for p in pages:
            db_pages.append({
                "index": int(p.get("index", 0)),
                "text": p.get("text", ""),
                "url": p.get("url", "")
            })
        db.save_pages(story_id, db_pages)

        print(f"✅ 저장 완료: {title} (ID: {story_id})")
        return jsonify({"ok": True, "story_id": story_id}), 200

    except Exception as e:
        print(f"❌ 저장 에러: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ------------------------------
# E) 동화 삭제 API
# ------------------------------
@api_bp.delete("/story/<int:story_id>")
def story_delete(story_id):
    try:
        db.delete_story(story_id)
        return jsonify({"ok": True}), 200
    except Exception as e:
        print(f"❌ 삭제 실패: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500