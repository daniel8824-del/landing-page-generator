# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

상세페이지(쇼핑몰 제품 상세 이미지) 자동 생성 파이프라인. 제품 정보를 입력하면 5개 에이전트가 순차/병렬로 동작하여 13개 섹션 PNG 이미지를 생성하고, 최종적으로 세로 합성된 상세페이지 이미지(1200×~7000px)를 출력한다.

## Commands

```bash
pip install -r requirements.txt    # 의존성 설치
python app.py                      # Flask 웹 서버 시작 (localhost:5000)
python scripts/gemini_api.py 05-prompt.md output/  # 이미지만 생성
python scripts/stitch_images.py output/sections     # 합성만 실행
python scripts/naver_search.py "제품명" "카테고리" output/  # 시장 분석만 실행
```

환경변수: `.env` 파일에 `GEMINI_API_KEY` 필수, `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` 선택 설정 (`.env.example` 참조)

## Architecture

ARCHITECTURE.md에 전체 파이프라인이 정의되어 있다. 반드시 이 문서를 따를 것.

### Pipeline (6단계)

```
Phase 1 (순차): 정보수집(analyst)
Phase 2 (순차): 리서치(document-specialist) + 네이버 쇼핑 API 시장 데이터
Phase 3 (병렬): 카피라이팅(writer) ∥ 디자인(designer)
Phase 4 (순차): 프롬프팅(executor) — Gemini 프롬프트 13개 생성
Phase 5 (순차): Gemini 3 Pro REST API로 13개 섹션 이미지 생성
Phase 6 (순차): Pillow로 세로 합성 → final PNG/PDF
```

### Key Modules

- **app.py** — Flask 웹 서버. SSE로 파이프라인 진행 상태를 실시간 스트리밍. jobs dict를 orchestrator와 공유.
- **orchestrator.py** — 파이프라인 오케스트레이션. `init_jobs()`로 app.py의 jobs dict 참조를 받는다. `claude` CLI로 서브에이전트를 호출하고, 중간 산출물(01~05-*.md)을 생성한다. Phase 2의 카피+디자인은 threading으로 병렬 실행.
- **scripts/gemini_api.py** — Gemini 3 Pro REST API 직접 호출 (`requests` 사용, SDK 아님). 모델: `gemini-3-pro-image-preview`. 울트라 리얼리스틱 사진 스타일 프롬프트가 자동 래핑된다.
- **scripts/stitch_images.py** — Pillow 기반 이미지 합성. 모든 이미지를 1200px 너비로 강제 리사이즈 후 세로 합성. PNG + PDF + preview 출력.
- **scripts/naver_search.py** — 네이버 쇼핑 검색 API + DataLab API. 시장 리서치용 유틸리티 모듈. orchestrator Phase 2에서 호출.

### Agent → Claude Code Mapping

| 에이전트 | Claude Code 서브에이전트 | 산출물 |
|---------|----------------------|--------|
| 정보수집 | analyst | 01-intake.md |
| 리서치 | document-specialist | 02-research.md |
| 카피라이팅 | writer | 03-copy.md |
| 디자인 | designer | 04-design.md |
| 프롬프팅 | executor | 05-prompt.md |

### Reference Docs (docs/)

에이전트 프롬프트 작성 시 반드시 참조해야 하는 문서:
- `section_guide.md` — 13개 섹션 구조, 감정 여정, 필수 요소, 체크리스트
- `copy_patterns.md` — 헤드라인 공식, 공감 패턴, CTA, 긴급성/희소성 표현
- `design_specs.md` — 1200px 고정 너비, 섹션별 높이, 스타일 프리셋(Minimal/Sales/Premium/Community), 컬러/타이포/컴포넌트 스펙
- `prompt_patterns.md` — Gemini 프롬프트 템플릿, 필수 블록(CRITICAL REQUIREMENTS, PHOTOGRAPHY STYLE, STYLE ANCHOR, FINAL CHECKLIST)

## Critical Rules

- 이미지 너비는 **정확히 1200px** (절대 변경 금지)
- 이미지 스타일은 **실사 사진** (일러스트/카툰/벡터 절대 금지)
- 한국어 카피는 **번역투 금지**, 자연스러운 구어체 사용
- 파일명은 ARCHITECTURE.md에 정의된 것을 따를 것
- Gemini API는 `requests`로 REST 직접 호출 (google-genai SDK 사용하지 않음)
- `docs/` 폴더의 Python 파일은 참조용 원본이며, 실제 실행 코드는 `scripts/`에 있음
