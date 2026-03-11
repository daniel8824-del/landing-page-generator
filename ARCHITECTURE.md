# 상세페이지 자동 생성기 - 클로드 코드 오케스트레이터

## 개요

제품 정보를 입력하면 13개 섹션으로 구성된 상세페이지 이미지를 자동 생성하는 파이프라인.
Claude(텍스트/기획) + Gemini(이미지 생성) 멀티모델 조합으로 동작한다.

## 파이프라인 흐름

```
① 기획팀 (서브에이전트)
   ├── 01-intake.md    → 입력 수집
   └── 02-research.md  → 리서치
          │
    ┌─────┴─────┐
    ▼            ▼
② 카피팀        ③ 디자인팀       ← 병렬 실행
  03-copy.md      04-design.md
    │            │
    └─────┬─────┘
          ▼
④ 개발팀 (Claude 서브에이전트 + Python)
   05-prompt.md
          │
          ▼
⑤ 스크립트 실행
   gemini_api.py / stitch_images.py
          │
          ▼
⑥ 최종 결과물 (상세페이지 이미지)
```

## 단계별 상세

### 1단계: 기획팀 (서브에이전트)

| 항목 | 내용 |
|------|------|
| 도구 | Claude 서브에이전트 |
| 입력 | 사용자 제품 정보 (제품명, 카테고리, 특징, 타겟 등) + 참고 이미지(선택) |
| 산출물 | `01-intake.md`, `00-style-reference.md`(선택) |

- **01-intake.md**: 사용자 입력을 구조화하여 정리
- **00-style-reference.md**: 참고 이미지 업로드 시 Gemini 멀티모달 분석 수행 → 컬러/레이아웃/타이포/무드 분석

### 2단계: 리서치팀 (서브에이전트)

| 항목 | 내용 |
|------|------|
| 도구 | Claude 서브에이전트 |
| 입력 | `01-intake.md` |
| 산출물 | `02-research.md` |

- **02-research.md**: 네이버 쇼핑 검색 API + 데이터랩 API로 시장 데이터 자동 수집
- 유사 상품 검색, 카테고리 트렌드 분석, 경쟁사 가격/특징 정리

### 3단계: 카피팀 (Claude 서브에이전트)

| 항목 | 내용 |
|------|------|
| 도구 | Claude 서브에이전트 |
| 입력 | `01-intake.md`, `02-research.md` |
| 산출물 | `03-copy.md` |

- 13개 섹션별 마케팅 카피 생성
- 헤드라인, 서브카피, CTA 등 포함

### 4단계: 디자인팀 (Claude 서브에이전트)

| 항목 | 내용 |
|------|------|
| 도구 | Claude 서브에이전트 |
| 입력 | `01-intake.md`, `02-research.md` |
| 산출물 | `04-design.md` |

- 전체 스타일 방향 결정
- 컬러 팔레트, 폰트 스타일, 레이아웃 가이드

> **참고**: 3단계와 4단계는 병렬로 동시 실행된다.

### 5단계: 개발팀 (Claude 서브에이전트 + Python)

| 항목 | 내용 |
|------|------|
| 도구 | Claude 서브에이전트 + Python |
| 입력 | `03-copy.md`, `04-design.md` |
| 산출물 | `05-prompt.md` |

- 카피 + 디자인 결과를 병합
- Gemini 이미지 생성용 프롬프트 13개 작성

### 6단계: 스크립트 실행

| 항목 | 내용 |
|------|------|
| 도구 | Python 스크립트 |
| 입력 | `05-prompt.md` |
| 산출물 | 섹션별 이미지 파일 (13장) + 합성 이미지 |

- **gemini_api.py**: Gemini API로 13개 섹션 이미지 개별 생성
- **stitch_images.py**: 생성된 이미지들을 세로로 합성

### 7단계: 최종 결과물

| 항목 | 스펙 |
|------|------|
| 포맷 | PNG + PDF |
| 해상도 | **1200px x 7000px** |
| 섹션당 높이 | 400~800px (섹션별 상이, design_specs.md 참조) |
| 색상 모드 | sRGB |

- 13개 섹션이 합쳐진 완성된 상세페이지
- PNG (웹 업로드용) + PDF (인쇄/공유용) 동시 출력

## 중간 산출물 구조

```
Page/
├── ARCHITECTURE.md          ← 이 문서
├── CLAUDE.md                ← Claude Code 가이드
├── app.py                   ← Flask 웹 서버 (모니터링 UI)
├── orchestrator.py          ← 에이전트 파이프라인 오케스트레이션
├── requirements.txt         ← Python 의존성
├── .env.example             ← 환경변수 템플릿
│
├── scripts/                 ← 실행 스크립트
│   ├── gemini_api.py        ← Gemini 3 Pro 이미지 생성 + 멀티모달 분석
│   ├── naver_search.py      ← 네이버 쇼핑 검색 + 데이터랩 API
│   └── stitch_images.py     ← 이미지 합성 (Pillow)
│
├── agents/                  ← 에이전트 정의
│   ├── AGENTS.md            ← 팀 정의서
│   └── {에이전트별}.md      ← 에이전트 프롬프트/스펙
│
├── docs/                    ← 참조 문서
│   ├── section_guide.md     ← 13섹션 구조/역할
│   ├── copy_patterns.md     ← 카피 패턴/공식
│   ├── design_specs.md      ← 디자인 스펙/사이즈
│   ├── prompt_patterns.md   ← Gemini 프롬프트 패턴
│   └── diagram_preset.md    ← 다이어그램 스타일
│
├── templates/index.html     ← 모니터링 웹 UI
│
└── output/{job_id}/         ← 생성 결과물 (job별)
    ├── 00-style-reference.md  ← [생성됨] 참고 이미지 스타일 분석 (선택)
    ├── 00-market.md           ← [생성됨] 네이버 시장 분석 결과
    ├── 01-intake.md           ← [생성됨] 입력 정리
    ├── 02-research.md         ← [생성됨] 리서치
    ├── 03-copy.md             ← [생성됨] 13섹션 카피
    ├── 04-design.md           ← [생성됨] 디자인 가이드
    ├── 05-prompt.md           ← [생성됨] Gemini 프롬프트 13개
    ├── sections/            ← 개별 섹션 이미지
    │   ├── 01_hero.png
    │   ├── 02_pain.png
    │   ├── 03_problem.png
    │   ├── 04_story.png
    │   ├── 05_solution.png
    │   ├── 06_how_it_works.png
    │   ├── 07_social_proof.png
    │   ├── 08_authority.png
    │   ├── 09_benefits.png
    │   ├── 10_risk_removal.png
    │   ├── 11_comparison.png
    │   ├── 12_target_filter.png
    │   └── 13_final_cta.png
    ├── final_detail_page.png   ← 합성 상세페이지 (1200x7000px)
    ├── final_detail_page.pdf   ← PDF 버전
    └── preview.png             ← 축소 미리보기
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| 오케스트레이션 | Claude Code (서브에이전트) |
| 텍스트 생성 | Claude (카피, 기획, 프롬프트) |
| 이미지 생성 | Gemini API |
| 스크립트 | Python |
| 이미지 합성 | Python (Pillow 등) |
| 중간 데이터 | Markdown 파일 |

## 이미지 생성 필수 규칙

| 규칙 | 내용 |
|------|------|
| 너비 고정 | **1200px** (절대 변경 금지) |
| 스타일 | **실사 사진** (일러스트/카툰/벡터 절대 금지) |
| 한글 폰트 | **Pretendard Bold (weight 700+)** |
| 한글 길이 | 한 문장 15자 이내 (긴 문장은 Gemini가 뭉갬) |
| px 수치 금지 | 프롬프트에 px 단위(14px, 24px 등) 넣지 말 것 — Gemini가 이미지에 렌더링 |
| CSS 스펙 금지 | border-radius, rgba, shadow 등 CSS 값 넣지 말 것 |
| 크기 표현 | "large", "medium", "standard" 등 상대적 표현만 사용 |
