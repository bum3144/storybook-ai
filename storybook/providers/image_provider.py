# storybook/providers/image_provider.py
from __future__ import annotations
from typing import List
from urllib.parse import quote
import random


class ImageProvider:
    """
    이미지 프롬프트 → URL 생성기.
    Pollinations AI를 사용하며, 한글/영어 혼용 시에도 스타일을 강제 적용합니다.
    """
    # Pollinations 기본 URL
    BASE = "https://image.pollinations.ai/prompt/"

    @staticmethod
    def build_image_url(prompt: str, seed: int = None) -> str:
        """
        프롬프트를 받아 이미지 URL을 생성합니다.
        seed를 붙여서 매번 새로운 이미지가 생성되도록 유도합니다.
        """
        # 1. 화질 및 스타일 강조 (프롬프트 앞단에 배치)
        # 고품질 이미지를 생성하기 위해 디테일 관련 키워드를 강제로 추가합니다.
        quality_booster = "best quality, masterpiece, highly detailed, 8k resolution, vibrant colors, sharp focus, artstation trend"

        # api.py에서 이미 스타일이 포함된 경우와 아닌 경우를 구분하여 처리
        if "style" not in prompt:
            # 스타일이 없는 경우 기본 동화책 느낌 추가
            enriched_prompt = f"children's storybook illustration, soft colors, {quality_booster}, {prompt}"
        else:
            # api.py에서 "(style), text" 형태로 넘어온 경우
            enriched_prompt = f"{quality_booster}, {prompt}"

        # 2. 랜덤 시드 추가 (중복 방지 핵심)
        # 시드 값이 없으면 랜덤하게 생성
        if seed is None:
            seed = random.randint(0, 999999)

        # URL 인코딩 (한글 및 특수문자 처리)
        encoded_prompt = quote(enriched_prompt)

        # 3. 해상도 및 모델 설정
        # 기존 768에서 1024로 상향 조정하여 화질 개선
        # model=flux 파라미터를 추가하여 프롬프트 반영도 및 디테일 향상
        final_url = f"{ImageProvider.BASE}{encoded_prompt}?nospam=1&seed={seed}&width=1024&height=1024&model=flux"

        return final_url

    def images_for_keywords(self, keywords: List[str], limit: int) -> List[str]:
        # (호환성을 위한 레거시 메서드)
        limit = max(1, min(int(limit or 1), 5))
        kws = [k.strip() for k in (keywords or []) if k and k.strip()]
        if not kws:
            kws = [f"scene {i + 1}" for i in range(limit)]
        urls = []
        for i in range(limit):
            kw = kws[i] if i < len(kws) else f"scene {i + 1}"
            urls.append(self.build_image_url(kw))
        return urls