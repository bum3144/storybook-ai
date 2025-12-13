# storybook/providers/gemini_provider.py
from __future__ import annotations
import os
import json
import logging
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold


class GeminiProvider:
    """
    Google Gemini API를 사용하여 스토리 플롯을 생성하는 공급자입니다.
    """

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")

        self._configured = False
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self._configured = True
            self.model_name = "gemini-2.0-flash"
            print(f"👀 [Storybook] 모델명: {self.model_name}")

    def is_available(self) -> bool:
        return bool(self._configured)

    def generate_story(
            self,
            meta: Dict[str, str],
            pages: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        if not self.is_available():
            raise ValueError("Gemini API Key가 설정되지 않았습니다.")

        # 1. 프롬프트 구성
        prompt = self._build_prompt(meta, pages)

        # 2. 모델 설정
        model = genai.GenerativeModel(self.model_name)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        try:
            response = model.generate_content(
                prompt,
                safety_settings=safety_settings,
                generation_config={"response_mime_type": "application/json"}
            )

            # 3. 응답 파싱
            results = self._parse_response(response.text, len(pages))

            # 인덱스 보정 로직
            if len(pages) == 1 and len(results) == 1:
                req_idx = int(pages[0].get("index", 0))
                results[0]["index"] = req_idx
            elif len(pages) > 1 and results:
                results.sort(key=lambda x: x.get("index", 0))
                for i, res in enumerate(results):
                    if i < len(pages):
                        res["index"] = int(pages[i].get("index", i))

            return results

        except Exception as e:
            logging.error(f"Gemini generation failed: {e}")
            raise e

    def _build_prompt(self, meta: Dict[str, str], pages: List[Dict[str, Any]]) -> str:
        title = meta.get("title", "제목 없음")
        genre = meta.get("genre", "동화")
        world = meta.get("world", "상상 속 세상")
        theme = meta.get("theme", "모험")
        hero = meta.get("hero", "주인공")

        pages_info = []
        target_indices = []

        for p in pages:
            idx = int(p.get("index", 0))
            display_idx = idx + 1
            kws = p.get("keywords") or []
            kw_str = ", ".join(kws) if kws else "자유 주제"

            stage_hint = ""
            if display_idx == 1:
                stage_hint = "(도입: 배경과 주인공 소개)"
            elif display_idx == 2:
                stage_hint = "(전개: 사건의 시작)"
            elif display_idx == 3:
                stage_hint = "(위기: 갈등이나 문제 발생)"
            elif display_idx == 4:
                stage_hint = "(절정: 문제 해결의 실마리)"
            elif display_idx >= 5:
                stage_hint = "(결말: 행복한 마무리)"

            pages_info.append(f"- 페이지 {display_idx} {stage_hint}: 키워드 [{kw_str}]")
            target_indices.append(idx)

        pages_text = "\n".join(pages_info)

        is_partial = len(pages) == 1
        context_instruction = ""
        if is_partial:
            context_instruction = (
                f"주의: 사용자가 {pages[0].get('index', 0) + 1}페이지의 내용만 다시 쓰기를 원합니다. "
                f"전체 이야기 흐름에 맞게 자연스럽게 이어지도록 작성해주세요."
            )

        return f"""
역할: 당신은 아이들의 상상력을 자극하는 베스트셀러 동화 작가입니다.
임무: 아래 정보를 바탕으로 아이들이 푹 빠져들 수 있는 재미있는 동화를 써주세요.

[동화 설정]
- 제목: {title}
- 장르: {genre}
- 배경: {world}
- 주제: {theme}
- 주인공: {hero}

[페이지별 가이드]
{pages_text}

[작성 필수 규칙]
1. 독자: 5~8세 어린이 (이해하기 쉽지만 표현력이 풍부한 어휘 사용)
2. 문체: 친절하고 부드러운 '해요체' (예: ~했어요, ~했답니다)
3. **분량**: 각 페이지당 **최소 4문장 ~ 최대 8문장**으로 풍성하게 작성하세요.
4. **묘사**: 주인공의 **대사(말)**와 주변의 **소리, 냄새, 느낌**을 반드시 포함하세요.
5. **[중요] 절대 설정 정보를 쓰지 마세요**: 
   - 1페이지라고 해서 제목, 장르, 주인공 소개를 목록(List)으로 적지 마세요.
   - 바로 "옛날 어느 마을에..." 하고 이야기를 시작하세요.
   - 메타데이터(제목 등)는 오직 참고용입니다.
6. {context_instruction}
7. 응답 형식: 반드시 아래 JSON 포맷을 지켜주세요.

[응답 예시]
[
  {{ "index": {target_indices[0]}, "text": "옛날 어느 맑은 연못가에 아기 오리 '둥둥이'가 살고 있었어요. 둥둥이는 물장구치는 것을 가장 좋아했답니다. \\"야호! 물이 정말 시원해!\\" 둥둥이는 첨벙첨벙 소리를 내며 친구들을 불렀어요." }}
]
"""

    def translate_prompt_for_image(self, korean_text: str) -> str:
        if not self.is_available() or not korean_text:
            return korean_text

        model = genai.GenerativeModel(self.model_name)
        system_instruction = (
            "You are a professional prompt engineer for AI Image Generator (Flux/Midjourney). "
            "Convert the Korean story text into a highly detailed English visual prompt. "
            "Include: Subject look, Action, Environment, Lighting, Color tone, Art style. "
            "Output format: comma-separated keywords ONLY. No sentences."
        )

        max_retries = 2
        import time
        for attempt in range(max_retries + 1):
            try:
                prompt = f"{system_instruction}\nInput Text: {korean_text}"
                response = model.generate_content(prompt)
                english_prompt = response.text.strip()
                print(f"[Gemini] Prompt Translated: {english_prompt[:40]}...")
                return english_prompt
            except Exception as e:
                print(f"[Gemini] Translation Error: {e}")
                if attempt < max_retries:
                    time.sleep(1)
                else:
                    return "storybook illustration, fantasy style"

    def translate_prompts_bulk(self, korean_texts: List[str]) -> List[str]:
        if not self.is_available() or not korean_texts:
            return korean_texts

        model = genai.GenerativeModel(self.model_name)
        input_text_block = ""
        for i, txt in enumerate(korean_texts):
            input_text_block += f"{i}. {txt}\n"

        system_instruction = (
            "Convert these Korean story sentences into detailed English visual prompts for AI image generation. "
            "Focus on visual description. Return ONLY a JSON array of strings."
        )
        prompt = f"{system_instruction}\n[Inputs]\n{input_text_block}"

        try:
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            parsed = json.loads(response.text)
            if isinstance(parsed, list) and len(parsed) == len(korean_texts):
                print(f"🔤 Bulk Translation Success: {len(parsed)} items")
                return parsed
            else:
                return korean_texts
        except Exception:
            return korean_texts

    def _parse_response(self, text: str, expected_count: int) -> List[Dict[str, str]]:
        try:
            clean_text = text.strip()
            if clean_text.startswith("```json"): clean_text = clean_text[7:]
            if clean_text.endswith("```"): clean_text = clean_text[:-3]
            data = json.loads(clean_text)  # 여기서 전역 json 모듈을 사용합니다.
            if not isinstance(data, list): data = [data] if data else []

            results = []
            for item in data:
                idx = item.get("index")
                txt = item.get("text", "")

                # [안전장치] 객체(Object)가 오면 문자열로 변환 (중복 import 삭제함)
                if isinstance(txt, dict) or isinstance(txt, list):
                    txt = json.dumps(txt, ensure_ascii=False)

                if idx is not None:
                    results.append({"index": int(idx), "text": str(txt)})
            results.sort(key=lambda x: x["index"])
            return results
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing failed: {text}")
            raise ValueError("AI 응답 오류") from e