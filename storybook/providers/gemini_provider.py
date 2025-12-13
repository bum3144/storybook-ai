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
            # [핵심 수정] 인덱스 강제 보정 (AI의 착각 방지)
            # 요청한 페이지가 1개뿐인데 결과도 1개가 왔다면,
            # AI가 번호를 헷갈렸을 수 있으므로 요청했던 원본 인덱스로 덮어씌웁니다.
            # ---------------------------------------------------------------
            if len(pages) == 1 and len(results) == 1:
                req_idx = int(pages[0].get("index", 0))
                res_idx = int(results[0].get("index", 0))

                if req_idx != res_idx:
                    logging.info(f"AI Index Mismatch Fix: AI({res_idx}) -> Req({req_idx})")
                    results[0]["index"] = req_idx

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