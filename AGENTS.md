# Landing Page Generator

상세페이지(쇼핑몰 제품 상세 이미지) 자동 생성 파이프라인.
제품 정보를 입력하면 에이전트가 카피/디자인/프롬프트를 생성하고,
Gemini 3 Pro로 13개 섹션 이미지를 만든 뒤 Pillow로 합성합니다.

## Skills

- `landing-page`: 상세페이지 생성 스킬 (/landing-page, "상세페이지", "랜딩페이지")

## Commands

```bash
pip install -r requirements.txt          # 의존성 설치
uvicorn app.main:app --port 8000         # 웹앱 실행
python scripts/gemini_api.py             # 이미지 생성
python -c "from scripts.stitch_images import stitch_all; stitch_all('output/')"  # 합성
```

## Critical Rules

- 이미지 너비: **1200px 고정**
- 스타일: **실사 사진** (일러스트/카툰 금지)
- 한글 폰트: **Pretendard Bold (weight 700+)**
- 한 문장 **15자 이내**
- Gemini 프롬프트에 px/CSS 값 금지
