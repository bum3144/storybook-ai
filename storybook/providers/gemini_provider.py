# storybook/providers/gemini_provider.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

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

    def suggest_story(
        self,
        meta: Dict[str, str],
        pages: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """
        스토리 전체 메타 + 페이지별 정보 기반으로
        페이지별 한 줄 요약을 생성하는 LLM 엔트리 포인트.

        실제 LLM 연동 시에는 이 메서드 내부를 교체하면 된다.
        지금은 간단한 규칙 기반 목업을 사용한다.
        """
        title = (meta.get("title") or "").strip()
        hero = (meta.get("hero") or "").strip() or "주인공"
        genre = (meta.get("genre") or "").strip()
        world = (meta.get("world") or "").strip()
        theme = (meta.get("theme") or "").strip()

        stage_texts = [
            "이야기의 문을 여는 시작 장면입니다.",
            "모험이 본격적으로 펼쳐지는 장면입니다.",
            "뜻밖의 사건이 일어나 흐름이 크게 바뀌는 장면입니다.",
            "가장 긴장되는 클라이맥스 장면입니다.",
            "조용히 정리되고 따뜻하게 마무리되는 장면입니다.",
        ]

        total = max(1, len(pages))
        results: List[Dict[str, str]] = []

        for i, page in enumerate(pages):
            idx = int(page.get("index", i))
            kws = [str(k).strip() for k in page.get("keywords") or [] if str(k).strip()]
            prev_text = (page.get("previous_text") or "").strip()
            cont = bool(page.get("continue", True))

            if kws:
                focus = "’, ‘".join(kws)
                focus = f"‘{focus}’"
            elif genre:
                focus = f"‘{genre}’"
            else:
                focus = "이 장면"

            if total == 1:
                stage_idx = 0
            else:
                stage_idx = round((i / (total - 1)) * (len(stage_texts) - 1))
            stage_idx = min(max(stage_idx, 0), len(stage_texts) - 1)

            if i == 0:
                prefix = f"‘{hero}’의 "
                if genre:
                    prefix += f"{genre} "
                prefix += "이야기가 시작되는 장면에서, "
            else:
                if cont and prev_text:
                    prefix = "앞선 장면을 이어, "
                else:
                    prefix = "새로운 장면에서, "

            world_part = f"{world}를 배경으로 " if world else ""
            base = (
                f"{prefix}{world_part}{focus}을(를) 중심으로 "
                f"{stage_texts[stage_idx]}"
            )

            if theme:
                base += f" 이 장면 역시 '{theme}'라는 주제를 담고 있습니다."

            results.append({"index": idx, "text": base})

        return results

        # 실제 Gemini 연동 예시 (의존성 없도록 주석 처리):
        # if self.api_key:
        #     import google.genai as genai
        #     client = genai.Client(api_key=self.api_key)
        #     prompt = self._build_prompt(meta, pages)
        #     resp = client.models.generate_content(
        #         model="gemini-1.5-flash",
        #         contents=prompt,
        #     )
        #     # resp.text를 페이지별로 파싱하여 results 형태로 변환 후 반환
