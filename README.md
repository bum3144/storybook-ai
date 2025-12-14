# Storybook AI

AI를 활용하여 사용자가 직접 또는 AI와 협업하여
한 권의 그림동화책을 제작할 수 있는 웹 기반 플랫폼입니다.

Storybook AI는 단순 텍스트 또는 이미지 생성에 그치지 않고,
**스토리 작성 → 삽화 생성 → 표지 제작 → 전자책(PDF) 출력**까지
동화 제작의 전체 과정을 하나의 통합된 워크플로우로 제공합니다.

---

## 🔥 주요 기능

- **직접 쓰기 / AI 협업 모드:** 사용자가 선택 가능한 두 가지 창작 방식
- **페이지 단위 관리:** 페이지별 스토리 생성 및 수정
- **AI 이미지 생성:** 페이지별 삽화 자동 생성 및 선택 이미지 재생성
- **표지 커스터마이징:** AI 기반 표지 이미지 생성 및 제목 배치
- **웹 미리보기:** 실제 책을 넘기는 듯한 펼침면 UI
- **전자책 저장:** 완성된 동화를 PDF 파일로 소장

---

## 🧰 기술 스택

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **AI (Text):** Google Gemini 2.0 Flash
- **AI (Image):** Pollinations.ai (Flux)
- **Database:** SQLite (data/storybook.db)
- **Others:** Flask Session, Fetch API, @media print (PDF Layout)

---

## 🏗️ 아키텍처 요약

- **Client(Web):** 사용자 입력 및 UI 렌더링, 비동기 데이터 처리
- **Flask Server:** AI 요청을 중앙 통제하는 API Gateway 역할
- **Provider Pattern:** 텍스트/이미지 생성 로직을 분리하여 관리
- **Data Storage:** JSON 파일 기반의 스토리 데이터 저장 및 관리

---

## 📂 프로젝트 구조도

```text
storybook-ai/
├── app.py                # 메인 실행 파일
├── requirements.txt      # 의존성 패키지 목록
├── .env.example          # 환경변수 예시 파일
├── README.md             # 프로젝트 설명서
└── storybook/            # 핵심 애플리케이션 소스
    ├── data/             # SQLite DB 파일 저장소
    ├── database/         # DB 모델 및 설정
    ├── providers/        # AI (Gemini, Flux) 연동 모듈
    ├── repositories/     # 데이터 접근 계층
    ├── routes/           # API 및 UI 라우팅
    ├── static/           # CSS, JS, 이미지 리소스
    └── templates/        # HTML 화면 템플릿
```

---

## 🚀 설치 및 실행 방법

### 1. 저장소 클론
```bash
git clone [https://github.com/bum3144/storybook-ai.git](https://github.com/bum3144/storybook-ai.git)
cd storybook-ai
```

2. 패키지 설치
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정
Google Gemini API Key가 필요합니다. 
프로젝트 루트에 .env 파일을 만들거나 환경변수를 등록하세요.

Windows:
```DOS
set GEMINI_API_KEY=your_api_key_here
```
Mac/Linux:
```Bash
export GEMINI_API_KEY=your_api_key_here
```

4. 서버 실행
```Bash
python app.py
```

5. 웹 접속
브라우저 주소창에 아래 주소를 입력하세요. 
http://127.0.0.1:5000


※ storybook/data/storybook.db 는
시연 및 데이터 구조 확인을 위한 샘플 데이터베이스이며,
실행 시 자동 생성되는 구조를 기반으로 합니다.
