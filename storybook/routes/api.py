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

_http = requests.Session()
_http.headers.update({"User-Agent": "storybook-dev/0.1"})


# --- 에디터 데이터 임시 저장 ---
@api_bp.post("/editor/cache")
def editor_cache():
    payload = request.get_json(silent=True) or {}
    pages = payload.get("pages") or []

    session["editor_cache"] = payload
    # 새 스토리 작성을 위해 기존 미리보기 세션 초기화
    session.pop("preview", None)

    return jsonify({"ok": True, "count": len(pages)}), 200


# --- AI 플롯(줄거리) 생성 ---
@api_bp.post("/plot/generate")
def plot_generate():
    payload = request.get_json(silent=True) or {}
    meta = payload.get("meta") or {}
    pages = payload.get("pages") or []

    if not isinstance(pages, list) or not pages:
        return jsonify({"error": "페이지 정보가 없습니다."}), 400

    provider = GeminiProvider()
    if provider.is_available():
        try:
            print("✨ Gemini API를 이용한 플롯 생성 시작...")
            result_pages = provider.generate_story(meta, pages)
            return jsonify({"pages": result_pages}), 200
        except Exception as e:
            print(f"⚠️ 생성 실패: {e}")
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "API 키를 찾을 수 없습니다."}), 500


# --- 본문 이미지 생성 ---
@api_bp.post("/images/generate")
def images_generate():
    payload = request.get_json(silent=True) or {}
    pages_in = payload.get("pages") or []
    style = (payload.get("style") or "동화 일러스트").strip()

    img_provider = ImageProvider()
    gemini_provider = GeminiProvider()

    out = []

    # 번역을 위한 텍스트 추출
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

    # 일괄 번역 실행 (한글 -> 영어 프롬프트)
    english_prompts = gemini_provider.translate_prompts_bulk(korean_texts)

    for i, page_data in enumerate(valid_pages):
        idx = page_data["index"]

        if i < len(english_prompts):
            visual_prompt = english_prompts[i]
        else:
            visual_prompt = "storybook scene"

        full_prompt = f"({style}), {visual_prompt}"
        url = img_provider.build_image_url(full_prompt)
        out.append({"index": idx, "url": url})

        time.sleep(0.1)

    # 세션 업데이트 (미리보기용)
    current_preview = session.get("preview") or {}
    prev_pages = current_preview.get("pages") or []
    page_map = {p["index"]: p for p in prev_pages}

    for new_img in out:
        idx = new_img["index"]
        if idx in page_map:
            page_map[idx]["url"] = new_img["url"]
        else:
            page_map[idx] = {"index": idx, "url": new_img["url"], "text": ""}

    updated_pages = sorted(page_map.values(), key=lambda x: x["index"])

    session["preview"] = {
        "title": current_preview.get("title", session.get("editor_cache", {}).get("title", "")),
        "pages": updated_pages
    }
    session.modified = True

    return jsonify({"images": out}), 200


# --- 스토리 최종 저장 ---
@api_bp.post("/story/save")
def story_save():
    try:
        payload = request.get_json(silent=True) or {}
        title = payload.get("title", "제목 없음")
        pages = payload.get("pages", [])

        # 1. 스토리 정보 생성
        story_id = db.create_story(title=title, genre="동화", theme="자유")

        # 2. 페이지별 내용 저장
        db_pages = []
        for p in pages:
            db_pages.append({
                "index": int(p.get("index", 0)),
                "text": p.get("text", ""),
                "url": p.get("url", "")
            })
        db.save_pages(story_id, db_pages)

        return jsonify({"ok": True, "story_id": story_id}), 200

    except Exception as e:
        print(f"❌ 저장 중 오류 발생: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# --- 스토리 삭제 ---
@api_bp.delete("/story/<int:story_id>")
def story_delete(story_id):
    try:
        db.delete_story(story_id)
        return jsonify({"ok": True}), 200
    except Exception as e:
        print(f"❌ 삭제 중 오류 발생: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# --- 표지 이미지 생성 ---
@api_bp.post("/cover/generate_image")
def cover_generate_image():
    payload = request.get_json(silent=True) or {}

    custom_prompt = payload.get("prompt", "").strip()
    title = payload.get("title", "")

    gemini_provider = GeminiProvider()

    # 프롬프트 번역 및 생성
    if custom_prompt:
        print(f" 프롬프트 번역 시도: {custom_prompt}")
        translated_text = gemini_provider.translate_prompt_for_image(custom_prompt)
        prompt = f"(cover art style), {translated_text}, flat 2d illustration, full page design, no text, vivid colors"
    else:
        print(f" 제목 번역 시도: {title}")
        translated_title = gemini_provider.translate_prompt_for_image(title)
        prompt = f"(cover art style), flat 2d illustration for a story titled '{translated_title}', full page design, no text, vivid colors"

    img_provider = ImageProvider()
    url = img_provider.build_image_url(prompt)

    return jsonify({"url": url, "ok": True})


# --- 표지 정보 저장 ---
@api_bp.post("/cover/save")
def cover_save():
    payload = request.get_json(silent=True) or {}
    story_id = payload.get("story_id")
    new_title = payload.get("title")
    image_url = payload.get("image_url")
    title_pos = payload.get("position", "middle")
    author = payload.get("author", "")
    color = payload.get("color", "#ffffff")

    if not story_id:
        return jsonify({"ok": False, "error": "ID가 누락되었습니다."}), 400

    try:
        # 제목 업데이트 (변경된 경우)
        if new_title:
            db.update_story_title(story_id, new_title)
            final_title = new_title
        else:
            story = db.get_story_detail(story_id)
            final_title = story['title']

        # 표지 데이터 저장
        db.save_cover(story_id, image_url, final_title, author, title_pos, color)
        return jsonify({"ok": True})
    except Exception as e:
        print(f"표지 저장 실패: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500