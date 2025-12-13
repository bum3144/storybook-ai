# storybook/providers/gemini_provider.py
from __future__ import annotations
import os
import json
import logging
from typing import List, Dict, Any, Optional

# google-generativeai 라이브러리가 필요합니다.
# pip install google-generativeai
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

            # [최종 확정]
            # 목록에 확실히 존재하는 '2.0-flash'를 사용합니다.
            # 유료 계정이므로 Limit: 0 에러 없이 작동할 겁니다.
            self.model_name = "gemini-2.0-flash"

            print(f"👀 [Storybook] 모델명: {self.model_name} (유료모드: 저비용)")

    def is_available(self) -> bool:
        """API 키가 설정되어 있고 사용 가능한지 확인"""
        return bool(self._configured)

    def generate_story(
            self,
            meta: Dict[str, str],
            pages: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """
        Gemini에게 프롬프트를 보내고, JSON 응답을 파싱하여 반환합니다.
        """
        if not self.is_available():
            raise ValueError("Gemini API Key가 설정되지 않았습니다.")

        # 1. 프롬프트 구성
        prompt = self._build_prompt(meta, pages)

        # 2. 모델 설정 및 호출
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

            # ---------------------------------------------------------------
            # [핵심 수정 1] 단일 페이지 재생성 시 인덱스 고정
            # ---------------------------------------------------------------
            if len(pages) == 1 and len(results) == 1:
                req_idx = int(pages[0].get("index", 0))
                results[0]["index"] = req_idx

            # ---------------------------------------------------------------
            # [핵심 수정 2] 전체 플롯 생성 시 인덱스 순차 정렬 (0, 1, 2...)
            # AI가 {"index": 1} 부터 시작해서 보내더라도, 무조건 0부터 채워넣도록 강제합니다.
            # ---------------------------------------------------------------
            elif len(pages) > 1 and results:
                # 일단 AI가 보낸 인덱스 순서대로 정렬은 하되...
                results.sort(key=lambda x: x.get("index", 0))

                # 강제로 0, 1, 2... 순서표를 다시 붙입니다.
                for i, res in enumerate(results):
                    # 요청한 페이지 수보다 넘치지 않게 방어
                    if i < len(pages):
                        res["index"] = int(pages[i].get("index", i))

            return results

        except Exception as e:
            logging.error(f"Gemini generation failed: {e}")
            raise e
    def _build_prompt(self, meta: Dict[str, str], pages: List[Dict[str, Any]]) -> str:
        """LLM에게 보낼 프롬프트를 작성합니다. (페이지별 재생성 고려)"""
        title = meta.get("title", "제목 없음")
        genre = meta.get("genre", "동화")
        world = meta.get("world", "상상 속 세상")
        theme = meta.get("theme", "모험")
        hero = meta.get("hero", "주인공")

        # 페이지별 정보 구성
        pages_info = []
        target_indices = []

        for p in pages:
            idx = int(p.get("index", 0))
            # 0부터 시작하므로 1을 더해 '1페이지', '2페이지'로 표현
            display_idx = idx + 1
            kws = p.get("keywords") or []
            kw_str = ", ".join(kws) if kws else "자유 주제"

            # 힌트: 페이지 번호에 따라 이야기의 흐름을 암시해 줍니다.
            stage_hint = ""
            if display_idx == 1:
                stage_hint = "(이야기의 시작, 도입부)"
            elif display_idx == 2:
                stage_hint = "(모험의 시작, 전개)"
            elif display_idx == 3:
                stage_hint = "(위기 또는 새로운 사건 발생)"
            elif display_idx == 4:
                stage_hint = "(절정, 클라이맥스)"
            elif display_idx >= 5:
                stage_hint = "(결말, 마무리)"

            pages_info.append(f"- 페이지 {display_idx} {stage_hint}: 키워드 [{kw_str}]")
            target_indices.append(idx)

        pages_text = "\n".join(pages_info)

        # 단일 페이지 재생성인지, 전체 생성인지 구분하여 지시사항을 다르게 줍니다.
        is_partial = len(pages) == 1
        context_instruction = ""

        if is_partial:
            context_instruction = (
                f"주의: 사용자가 {pages[0].get('index', 0) + 1}페이지의 내용만 다시 쓰기를 원합니다. "
                f"전체 이야기의 흐름({genre}, {theme})에 맞게 해당 페이지만 자연스럽게 작성해주세요."
            )

        return f"""
역할: 당신은 아이들을 위한 창의적이고 따뜻한 동화 작가입니다.
임무: 아래 제공된 메타 정보와 페이지별 키워드를 바탕으로 동화의 내용을 작성해주세요.

[동화 기본 정보]
- 제목: {title}
- 장르: {genre}
- 배경: {world}
- 주제: {theme}
- 주인공: {hero}

[작성 대상 페이지]
{pages_text}

[작성 규칙]
1. 독자는 5~8세 어린이입니다. 이해하기 쉽고 상상력을 자극하는 표현을 써주세요.
2. 문체는 '해요체'(~해요, ~했습니다)를 사용해서 부드럽게 작성해주세요.
3. {context_instruction}
4. 각 페이지 분량은 1~2문장으로 간결하게 작성하세요.
5. 반드시 아래 JSON 형식으로만 응답해주세요.

[응답 예시 포맷]
[
  {{ "index": {target_indices[0]}, "text": "작성된 내용..." }}
]
"""

    # Gemini에게 "한글 문장 -> 영어 그림 묘사 키워드"로 변환해달라는 새로운 기능을 추가
    def translate_prompt_for_image(self, korean_text: str) -> str:
        """
        한글 동화 텍스트를 이미지 생성용 영어 프롬프트로 변환합니다.
        실패 시 최대 2회 재시도합니다.
        """
        if not self.is_available() or not korean_text:
            return korean_text

        model = genai.GenerativeModel(self.model_name)

        system_instruction = (
            "You are a prompt engineer for Stable Diffusion. "
            "Convert the given Korean story sentence into a detailed English visual prompt. "
            "Focus on visual elements (subjects, action, setting, lighting). "
            "Use comma-separated keywords. Do not explain, just output the prompt."
        )

        # 최대 2번 재시도 (총 3회 시도)
        max_retries = 2
        import time

        for attempt in range(max_retries + 1):
            try:
                prompt = f"{system_instruction}\nInput: {korean_text}"
                response = model.generate_content(prompt)
                english_prompt = response.text.strip()
                print(f"[Gemini] Prompt Translated: {english_prompt[:30]}...")
                return english_prompt
            except Exception as e:
                print(f"[Gemini] Translation Error (Attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(1.5)  # 실패 시 1.5초 대기 후 재시도
                else:
                    # 최종 실패 시 기본 영어 키워드 반환 (한글을 보내면 100% 실패하므로)
                    return "storybook illustration, fantasy style, cute characters"

    def translate_prompts_bulk(self, korean_texts: List[str]) -> List[str]:
        """
        [최적화] 여러 문장을 한 번의 API 호출로 모두 영어 프롬프트로 변환합니다.
        입력: ["문장1", "문장2", ...]
        출력: ["prompt1", "prompt2", ...]
        """
        if not self.is_available() or not korean_texts:
            return korean_texts

        # 무조건 self.model_name을 써야 합니다!
        model = genai.GenerativeModel(self.model_name)

        # 번역할 문장들을 번호 매겨서 나열
        input_text_block = ""
        for i, txt in enumerate(korean_texts):
            input_text_block += f"{i}. {txt}\n"

        system_instruction = (
            "You are a prompt engineer. Convert the given Korean story sentences into detailed English visual prompts.\n"
            "Return ONLY a JSON array of strings, strictly matching the order of input.\n"
            "Example input:\n0. 안녕\n1. 바다\n"
            "Example output:\n[\"hello, greeting\", \"ocean, blue water\"]\n"
        )

        prompt = f"{system_instruction}\n[Input Sentences]\n{input_text_block}"

        try:
            # 한 번에 요청!
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            parsed = json.loads(response.text)

            # 개수 검증
            if isinstance(parsed, list) and len(parsed) == len(korean_texts):
                print(f"🔤 Bulk Translation Success: {len(parsed)} items")
                return parsed
            else:
                print("⚠️ Bulk Translation Count Mismatch. Fallback to raw text.")
                return korean_texts  # 실패 시 원본 반환

        except Exception as e:
            print(f"❌ Bulk Translation Failed: {e}")
            return korean_texts

    def _parse_response(self, text: str, expected_count: int) -> List[Dict[str, str]]:
        """JSON 문자열을 파싱하여 리스트로 변환합니다."""
        try:
            # 혹시 모를 마크다운 코드 블록 제거
            clean_text = text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]

            data = json.loads(clean_text)

            if not isinstance(data, list):
                # 리스트가 아니면 단일 객체일 수 있으니 리스트로 감쌈
                data = [data] if data else []

            # 인덱스 정렬 및 키 정리
            results = []
            for item in data:
                idx = item.get("index")
                txt = item.get("text", "")
                if idx is not None:
                    results.append({"index": int(idx), "text": str(txt)})

            # 인덱스 순 정렬
            results.sort(key=lambda x: x["index"])
            return results

        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing failed: {text}")
            raise ValueError("AI 응답을 해석할 수 없습니다.") from e