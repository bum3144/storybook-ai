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

        # [수정] 목록에서 확인된 최신 Flash 모델 사용!
        self.model_name = "gemini-2.5-flash"

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
        실패 시(키 없음, 파싱 에러 등) 예외를 발생시키거나 빈 리스트를 반환할 수 있습니다.
        """
        if not self.is_available():
            raise ValueError("Gemini API Key가 설정되지 않았습니다.")

        # 1. 프롬프트 구성
        prompt = self._build_prompt(meta, pages)

        # 2. 모델 설정 및 호출
        model = genai.GenerativeModel(self.model_name)

        # 안전 설정 (동화책이므로 보수적으로 설정하되, 너무 막히지 않게 조절)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        try:
            # JSON 모드로 응답 요청 (프롬프트에서 JSON 형식을 강제하지만, response_mime_type을 쓰면 더 확실합니다)
            response = model.generate_content(
                prompt,
                safety_settings=safety_settings,
                generation_config={"response_mime_type": "application/json"}
            )

            # 3. 응답 파싱
            return self._parse_response(response.text, len(pages))

        except Exception as e:
            logging.error(f"Gemini generation failed: {e}")
            raise e

    def _build_prompt(self, meta: Dict[str, str], pages: List[Dict[str, Any]]) -> str:
        """LLM에게 보낼 프롬프트를 작성합니다."""
        title = meta.get("title", "제목 없음")
        genre = meta.get("genre", "동화")
        world = meta.get("world", "상상 속 세상")
        theme = meta.get("theme", "모험")
        hero = meta.get("hero", "주인공")

        # 페이지별 키워드 정리
        pages_info = []
        for p in pages:
            idx = p.get("index", 0) + 1
            kws = p.get("keywords") or []
            kw_str = ", ".join(kws) if kws else "자유 주제"
            pages_info.append(f"- 페이지 {idx}: {kw_str}")

        pages_text = "\n".join(pages_info)

        return f"""
역할: 당신은 아이들을 위한 창의적이고 따뜻한 동화 작가입니다.
임무: 아래 제공된 메타 정보와 페이지별 키워드를 바탕으로 동화의 각 페이지 내용을 작성해주세요.

[동화 정보]
- 제목: {title}
- 장르: {genre}
- 배경: {world}
- 주제: {theme}
- 주인공: {hero}

[페이지 구성 요청]
총 {len(pages)}페이지 분량입니다. 각 페이지에 해당하는 내용을 한두 문장으로 서술적으로 작성해주세요.
{pages_text}

[작성 규칙]
1. 독자는 5~8세 어린이입니다. 이해하기 쉽고 상상력을 자극하는 표현을 써주세요.
2. 문체는 '해요체'(~해요, ~했습니다)를 사용해서 부드럽게 작성해주세요.
3. 각 페이지 내용은 자연스럽게 이어져야 하며, 기승전결(시작-전개-위기/절정-결말)이 느껴지도록 구성해주세요.
4. 반드시 아래 JSON 형식으로만 응답해주세요. 다른 멘트는 추가하지 마세요.

[응답 예시 포맷]
[
  {{ "index": 0, "text": "첫 번째 페이지 내용..." }},
  {{ "index": 1, "text": "두 번째 페이지 내용..." }}
]
"""

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