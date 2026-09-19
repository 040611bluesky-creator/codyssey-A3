# 집밥요정 🧚

냉장고에 있는 재료만 알려주면, AI가 오늘 저녁 메뉴를 추천해주는 웹 서비스입니다.

## 배포 URL
https://codyssey-a3-topaz.vercel.app

## 서비스 소개
집밥요정은 냉장고 속 재료를 입력하면 AI(Google Gemini)가 인원, 조리 시간,
입맛 취향에 맞는 집밥 레시피를 2~3개 추천해주는 서비스입니다.
자취생, 요리 초보, "오늘 뭐 먹지" 고민하는 직장인을 타겟으로 합니다.

## 주요 기능
- 재료 태그 입력 (엔터로 추가/삭제, 자주 쓰는 재료 원클릭 추가)
- 인분 / 조리 시간 / 입맛 옵션 선택
- Google Gemini API 연동 AI 레시피 추천
- 반응형 디자인 (모바일/태블릿/데스크톱 대응)
- 다크 모드 지원 (localStorage로 설정 유지)
- 실패 처리: 빈 입력 안내, 식재료가 아닌 입력 감지, API 오류/지연 안내

## 페이지 구성
| 섹션 | 설명 |
|---|---|
| 메인 (Hero) | 서비스 소개 |
| AI 추천 | 재료 입력 + 레시피 추천 결과 |
| 소개 | 서비스 설명 및 이용 방법 |

## 기술 스택
- **프론트엔드**: HTML, CSS, JavaScript (바닐라, 프레임워크 미사용)
- **백엔드**: Python (Vercel Serverless Functions)
- **AI**: Google Gemini API (`gemini-3.6-flash`)
- **배포**: Vercel

## 프로젝트 구조
```
codyssey-A3/
├── index.html
├── css/
│   └── style.css
├── js/
│   └── main.js
├── api/
│   └── recommend.py
├── requirements.txt
└── vercel.json
```

## 로컬 실행 방법
1. 이 저장소를 클론합니다.
```bash
   git clone https://github.com/040611bluesky-creator/codyssey-A3.git
   cd codyssey-A3
```
2. Vercel CLI를 설치합니다.
```bash
   npm install -g vercel
```
3. 프로젝트 루트에 `.env` 파일을 만들고 아래 내용을 입력합니다.
```
   GEMINI_API_KEY=발급받은_API_키
```
4. 로컬 서버를 실행합니다.
```bash
   vercel dev
```
5. 터미널에 출력되는 주소(예: `http://localhost:3000`)로 접속합니다.

## 배포 방법
1. GitHub 저장소를 Vercel과 연동합니다.
2. Vercel 프로젝트의 **Settings → Environment Variables**에 `GEMINI_API_KEY`를 등록합니다.
   (Production, Preview, Development 환경 모두 체크)
3. `main` 브랜치에 push하면 자동으로 재배포됩니다.

## 환경 변수
| 이름 | 설명 |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio(aistudio.google.com)에서 발급받은 Gemini API 키 |

⚠️ API 키는 `.env` 파일과 Vercel 환경 변수에만 저장하며, 코드나 커밋 이력에 노출하지 않습니다.
`.env`는 `.gitignore`에 포함되어 GitHub에 업로드되지 않습니다.