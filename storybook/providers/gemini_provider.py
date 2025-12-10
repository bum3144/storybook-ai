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

    def suggest_story(
            self,
            meta: Dict[str, str],
            pages: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """
        스토리 전체 메타 + 페이지별 정보 기반으로
        페이지별 한 줄 요약을 생성하는 LLM 엔트리 포인트.

        지금은 규칙 기반 목업이지만,
        실제 LLM 연동 시 이 함수 내부만 교체하면 됨.
        """
        title = (meta.get("title") or "").strip()
        hero = (meta.get("hero") or "").strip() or "주인공"
        genre = (meta.get("genre") or "").strip()
        world = (meta.get("world") or "").strip()
        theme = (meta.get("theme") or "").strip()

        # 장면 단계 텍스트 (그대로 활용)
        stage_texts = [
            "이야기의 문을 여는 시작 장면입니다.",
            "모험이 본격적으로 펼쳐지는 장면입니다.",
            "뜻밖의 사건이 일어나 흐름이 크게 바뀌는 장면입니다.",
            "가장 긴장되는 클라이맥스 장면입니다.",
            "조용히 정리되고 따뜻하게 마무리되는 장면입니다.",
        ]

        total = max(1, len(pages))
        results: List[Dict[str, str]] = []

        def build_kw_parts(kws: List[str]) -> Tuple[str, str]:
            """
            첫 번째 키워드는 중심 키워드,
            나머지는 부가 키워드 문구로 묶는다.
            """
            if not kws:
                return "", ""
            main = kws[0]
            if len(kws) == 1:
                return main, ""
            rest = kws[1:]
            if len(rest) == 1:
                rest_phrase = rest[0]
            else:
                # A, B, C 그리고 D 형태
                rest_phrase = ", ".join(rest[:-1]) + " 그리고 " + rest[-1]
            return main, rest_phrase

        for i, page in enumerate(pages):
            idx = int(page.get("index", i))
            kws = [str(k).strip() for k in page.get("keywords") or [] if str(k).strip()]

            main_kw, rest_kw = build_kw_parts(kws)

            # 장면 단계 인덱스
            if total == 1:
                stage_idx = 0
            else:
                stage_idx = round((i / (total - 1)) * (len(stage_texts) - 1))
            stage_idx = min(max(stage_idx, 0), len(stage_texts) - 1)

            world_part = f"{world}를 배경으로 " if world else ""

            # --- 문장 조합 ---
            if i == 0:
                # 첫 장면: 이야기 시작
                if main_kw:
                    if rest_kw:
                        first = (
                            f"{world_part}{hero}는 {main_kw} 속에서 하루하루를 보내며, "
                            f"{rest_kw}에 대한 생각으로 가슴이 두근거립니다."
                        )
                    else:
                        first = (
                            f"{world_part}{hero}는 {main_kw}을(를) 바라보며 "
                            f"특별한 모험이 시작될 것 같은 예감을 받습니다."
                        )
                else:
                    first = (
                        f"{world_part}{hero}는 아직 정확히 알 수 없는 무언가를 향해 "
                        f"마음이 끌리는 것을 느낍니다."
                    )
            else:
                # 이후 장면들: 앞 내용과 자연스럽게 이어지는 느낌만,
                # '앞선 장면을 이어' 같은 템플릿 문구는 제거
                if main_kw:
                    if rest_kw:
                        first = (
                            f"{world_part}{hero}는 {main_kw}을(를) 따라가다 보니, "
                            f"{rest_kw}와(과) 얽힌 새로운 장면을 마주하게 됩니다."
                        )
                    else:
                        first = (
                            f"{world_part}{hero}는 {main_kw}과(와) 함께 "
                            f"조금 더 깊숙한 모험 속으로 들어갑니다."
                        )
                else:
                    first = (
                        f"{world_part}{hero}의 모험은 점점 더 깊어지고 있습니다."
                    )

            # 단계 요약 문구 추가
            second = stage_texts[stage_idx]
            text = first + " " + second

            # 주제(테마) 공통으로 덧붙이기
            if theme:
                text += f" 이 장면 역시 '{theme}'라는 주제를 담고 있습니다."

            results.append({"index": idx, "text": text})

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
