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
        # 1. 스타일 강조 (앞단에 배치)
        # 동화책 느낌을 살리기 위해 영어 키워드들을 앞에 붙여줍니다.
        # (children's book illustration, cute, soft colors 등)

        # 만약 프롬프트에 이미 스타일(괄호)이 포함되어 있다면 그대로 두고,
        # 아니라면 기본 스타일을 붙입니다.
        if "style" not in prompt:
            enriched_prompt = f"children's storybook illustration, soft colors, masterpiece, {prompt}"
        else:
            # api.py에서 넘겨준 "(style), text" 형태를 조금 더 보강
            enriched_prompt = f"best quality, {prompt}"

        # 2. 랜덤 시드 추가 (중복 방지 핵심!)
        # 시드 값이 없으면 랜덤하게 생성
        if seed is None:
            seed = random.randint(0, 999999)

        # URL 뒤에 ?nospam=1&seed={seed} 파라미터를 붙여서 캐싱을 방지합니다.
        # quote()를 사용해 한글/특수문자를 URL 인코딩합니다.
        encoded_prompt = quote(enriched_prompt)
        # final_url = f"{ImageProvider.BASE}{encoded_prompt}?nospam=1&seed={seed}&width=1024&height=1024"

        # 기존: width=1024&height=1024
        # 수정: width=768&height=768 로 변경하여 속도 향상
        final_url = f"{ImageProvider.BASE}{encoded_prompt}?nospam=1&seed={seed}&width=768&height=768"
        return final_url

    def images_for_keywords(self, keywords: List[str], limit: int) -> List[str]:
        # (이 메서드는 현재 api.py에서 직접 build_image_url을 호출하므로 사용되지 않지만,
        #  호환성을 위해 남겨둡니다.)
        limit = max(1, min(int(limit or 1), 5))
        kws = [k.strip() for k in (keywords or []) if k and k.strip()]
        if not kws:
            kws = [f"scene {i + 1}" for i in range(limit)]
        urls = []
        for i in range(limit):
            kw = kws[i] if i < len(kws) else f"scene {i + 1}"
            urls.append(self.build_image_url(kw))
        return urls