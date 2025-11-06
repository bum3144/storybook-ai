# storybook/providers/image_provider.py
from __future__ import annotations
from typing import List
from urllib.parse import quote

class ImageProvider:
    """
    간단한 이미지 프롬프트 → URL 생성기.
    기본은 Pollinations. 추후 Imagen/DeepAI로 교체 가능.
    """
    BASE = "https://image.pollinations.ai/prompt/"

    @staticmethod
    def build_image_url(prompt: str) -> str:
        # 동화 일러스트 스타일로 기본 프롬프트 보강
        enriched = f"{prompt}, cute storybook illustration, soft colors, simple background"
        return ImageProvider.BASE + quote(enriched)

    def images_for_keywords(self, keywords: List[str], limit: int) -> List[str]:
        limit = max(1, min(int(limit or 1), 5))
        kws = [k.strip() for k in (keywords or []) if k and k.strip()]
        if not kws:
            kws = [f"장면 {i+1}" for i in range(limit)]
        urls = []
        for i in range(limit):
            kw = kws[i] if i < len(kws) else f"장면 {i+1}"
            urls.append(self.build_image_url(kw))
        return urls
