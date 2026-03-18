# Landing Page Generator

AI가 제품 정보만으로 13개 섹션 상세페이지 이미지를 자동 생성하는 Claude Code 스킬입니다.

## Features

- 제품명, 특징, 타겟 고객만 입력하면 **상세페이지 이미지 13장** 자동 생성
- 최종 결과물: **1200px 너비 세로 합성 이미지** (PNG + PDF)
- 참고 이미지 스타일 분석 반영
- 리뷰 데이터(.xlsx/.csv) 분석 및 카피 반영
- 네이버 쇼핑 API 시장 리서치 (선택)

## Installation

```bash
git clone https://github.com/daniel8824-del/landing-page-generator.git
cd landing-page-generator
bash install.sh
```

## API Keys

`.env` 파일에 설정:
```
GEMINI_API_KEY=필수
NAVER_CLIENT_ID=선택
NAVER_CLIENT_SECRET=선택
```

## Usage

Claude Code에서:
```
/landing-page 셀 바이탈 리뉴얼 크림
```

## 13 Sections

| # | Section | Height | Purpose |
|---|---------|--------|---------|
| 01 | Hero | 800px | 헤드라인, CTA |
| 02 | Pain | 600px | 고객 고민 공감 |
| 03 | Problem | 500px | 진짜 원인 |
| 04 | Story | 700px | Before→After |
| 05 | Solution | 400px | 제품 소개 |
| 06 | How It Works | 600px | 사용 방법 |
| 07 | Social Proof | 800px | 후기, 증거 |
| 08 | Authority | 500px | 전문성 |
| 09 | Benefits | 700px | 혜택, 보너스 |
| 10 | Risk Removal | 500px | 환불, FAQ |
| 11 | Comparison | 400px | 비교 |
| 12 | Target Filter | 400px | 추천 대상 |
| 13 | Final CTA | 600px | 최종 구매 |

## License

MIT
