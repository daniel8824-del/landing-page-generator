# landing-page-generator

제품 정보만 입력하면 AI가 13개 섹션 상세페이지 이미지를 자동으로 만들어주는 Claude Code 스킬입니다.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 뭘 할 수 있나요?

- 제품명, 특징, 타겟 고객만 알려주면 **상세페이지 이미지 13장**이 자동 생성됩니다
- 최종 결과물은 **1200px 너비의 세로 합성 이미지** (PNG + PDF)
- 참고 이미지를 주면 그 스타일을 분석해서 반영합니다
- 네이버 쇼핑 API로 시장 데이터도 자동 수집합니다 (선택)

## 설치 방법

```bash
git clone https://github.com/daniel8824-del/landing-page-generator ~/.claude/skills/landing-page-generator
cd ~/.claude/skills/landing-page-generator
bash install.sh
```

설치 스크립트가 알아서:
1. Python 패키지 설치
2. API 키 설정 안내
3. 스킬 등록

## 사용 방법

Claude Code에서:
```
/landing-page-generator 셀 바이탈 리뉴얼 크림
```

필요한 정보가 부족하면 AI가 물어봅니다.

## API 키 설정

`.env` 파일에 설정 (`.env.example` 참고):
```
GEMINI_API_KEY=필수
NAVER_CLIENT_ID=선택 (시장 리서치용)
NAVER_CLIENT_SECRET=선택 (시장 리서치용)
```

## 생성되는 13개 섹션

| # | 섹션 | 역할 |
|---|------|------|
| 01 | Hero | 첫인상 — 헤드라인, CTA 버튼 |
| 02 | Pain | 고객의 고민/불편함 자극 |
| 03 | Problem | 진짜 원인 짚어주기 |
| 04 | Story | 사용 전 → 사용 후 변화 |
| 05 | Solution | 제품 한 줄 소개 |
| 06 | How It Works | 이렇게 쓰면 됩니다 |
| 07 | Social Proof | 후기, 판매 수치 |
| 08 | Authority | 만든 사람/브랜드 소개 |
| 09 | Benefits | 혜택, 보너스 구성 |
| 10 | Risk Removal | 환불 보장, FAQ |
| 11 | Comparison | 비교표 |
| 12 | Target Filter | 이런 분께 추천/비추천 |
| 13 | Final CTA | 지금 바로 구매하세요 |

## 작동 순서

```
1. 정보 수집 → 2. 시장 리서치 → 3. 카피+디자인(동시) → 4. 프롬프트 생성 → 5. 이미지 생성 → 6. 합성
```

자세한 구조는 [ARCHITECTURE.md](ARCHITECTURE.md) 참고.

## 라이선스

MIT — 자유롭게 사용하세요.
