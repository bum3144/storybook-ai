# storybook/providers/gemini_provider.py
from __future__ import annotations
from typing import List, Optional

class GeminiProvider:
    """
    추후 실제 Google Gemini API로 교체할 수 있도록 인터페이스만 유지.
    지금은 목업(로컬 생성)으로 동작.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def suggest_pages(self, keywords: List[str], page_count: int = 3) -> List[str]:
        page_count = max(1, min(int(page_count or 1), 5))
        kws = [k.strip() for k in (keywords or []) if k and k.strip()]
        if not kws:
            kws = [f"장면 {i+1}" for i in range(page_count)]

        lines: List[str] = []
        for i in range(page_count):
            kw = kws[i] if i < len(kws) else f"장면 {i+1}"
            lines.append(f"{i+1}. '{kw}'를(을) 주제로 한 장면.")
        return lines

    # 실제 연동시 예시 (참고용, 지금은 주석):
    # def suggest_pages(self, keywords, page_count=3):
    #     import google.genai as genai
    #     client = genai.Client(api_key=self.api_key)
    #     prompt = f"키워드: {', '.join(keywords)} / {page_count}장 분량의 아주 짧은 동화 한줄 요약을 페이지별로 만들어줘."
    #     resp = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    #     # resp.text를 페이지별로 파싱하여 리스트로 반환하도록 구현
    #     ...
