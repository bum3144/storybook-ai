import google.generativeai as genai
import os
import sys

# [수정] 여기에 아까 발급받은 '유료 프로젝트 키(AIza...)'를 따옴표 안에 붙여넣으세요!
# api_key = ""
# PyCharm 환경변수에서 키 가져오기
api_key = os.environ.get("GEMINI_API_KEY")

print(f"🐍 Python Executable: {sys.executable}")
print(f"📦 Google Generative AI Version: {genai.__version__}")

if not api_key:
    print("❌ API Key가 없습니다. 환경변수를 확인해주세요.")
else:
    genai.configure(api_key=api_key)
    print(f"🔑 API Key: {api_key[:5]}... (확인됨)")

    print("\n📋 사용 가능한 모델 목록:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
    except Exception as e:
        print(f"❌ 목록 조회 실패: {e}")