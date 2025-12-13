# check_models.py
import os
import google.generativeai as genai

# 환경변수에서 키를 가져옵니다 (PyCharm 실행 설정 이용)
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ API 키가 없습니다. 실행 설정(Edit Configurations)을 확인하세요.")
else:
    try:
        genai.configure(api_key=api_key)
        print(f"🔑 API Key 확인됨: {api_key[:10]}...")
        print("📋 사용 가능한 모델 목록을 조회합니다...\n")

        found = False
        for m in genai.list_models():
            # 'generateContent' 기능(텍스트 생성)을 지원하는 모델만 출력
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                found = True

        if not found:
            print("\n⚠️ 텍스트 생성이 가능한 모델을 찾지 못했습니다.")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")