# landing-page-generator

Claude Code 스킬 — 제품 정보를 입력하면 AI가 13개 섹션 상세페이지 이미지를 자동 생성합니다.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- **자동 파이프라인** — 6단계 오케스트레이션으로 정보 수집부터 이미지 합성까지 자동 처리
- **Gemini 3 Pro 통합** — REST API 기반 초고해상도 실사 이미지 생성 (1200×~7000px)
- **병렬 처리** — 카피라이팅과 디자인을 동시 진행으로 처리 시간 단축
- **네이버 쇼핑 연동** — 시장 분석 데이터 자동 수집 (선택)
- **웹 UI** — Flask 기반 실시간 진행 상태 모니터링

## Quick Start

### 스킬 설치

```bash
git clone https://github.com/daniel8824-del/landing-page-generator ~/.claude/skills/landing-page-generator
cd ~/.claude/skills/landing-page-generator
bash install.sh
```

### 기본 사용법

Claude Code에서:
```
/landing-page-generator 제품명
```

### 환경 설정

`.env` 파일 생성 (`.env.example` 참조):
```
GEMINI_API_KEY=your-api-key
NAVER_CLIENT_ID=optional
NAVER_CLIENT_SECRET=optional
```

## Web UI (선택)

```bash
python app.py
```

브라우저에서 `http://localhost:5000` 접속. 실시간 진행 상태 및 이미지 미리보기 확인.

## 13개 섹션 구조

| # | 섹션명 | 역할 |
|---|--------|------|
| 01 | Hero | 헤드라인, CTA, 긴급성 배지 |
| 02 | Pain | 페인포인트 자극 |
| 03 | Problem | 진짜 원인, 구조적 문제 |
| 04 | Story | Before→After 변화 |
| 05 | Solution | 제품 한 줄 정의 |
| 06 | How It Works | 단계별 프로세스 |
| 07 | Social Proof | 후기, 수치 |
| 08 | Authority | 제작자/브랜드 소개 |
| 09 | Benefits | 혜택, 보너스 |
| 10 | Risk Removal | 환불 정책, FAQ |
| 11 | Comparison | Before/After 비교 |
| 12 | Target Filter | 추천/비추천 대상 |
| 13 | Final CTA | 최종 구매 유도 |

## 필수 규칙

- **이미지 너비**: 정확히 **1200px** (절대 변경 금지)
- **이미지 스타일**: **실사 사진** (일러스트/카툰/벡터 금지)
- **폰트**: Pretendard Bold (기본)
- **텍스트 제한**: 섹션별 최대 **15자** 헤드라인

## 아키텍처

상세 구조는 [ARCHITECTURE.md](ARCHITECTURE.md) 참조.
- Phase 1: 정보 수집 (analyst)
- Phase 2: 리서치 (document-specialist) + 네이버 API
- Phase 3: 카피라이팅 (writer) ∥ 디자인 (designer) — 병렬
- Phase 4: 프롬프팅 (executor)
- Phase 5: Gemini 이미지 생성
- Phase 6: Pillow 합성 (PNG/PDF)

## 명령어 참고

```bash
pip install -r requirements.txt          # 의존성 설치
python app.py                            # 웹 서버 시작
python scripts/gemini_api.py 05-prompt.md output/  # 이미지 생성만
python scripts/stitch_images.py output/sections    # 합성만
python scripts/naver_search.py "제품명" "카테고리" output/  # 시장 분석만
```

## License

MIT License. [LICENSE](LICENSE) 파일 참조.
