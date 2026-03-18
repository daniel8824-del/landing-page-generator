"""
OpenRouter API를 통한 랜딩페이지 콘텐츠 생성
"""
import os
import httpx
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"

SYSTEM_PROMPT = """당신은 한국 이커머스 상세페이지(쇼핑몰 제품 상세 이미지) 전문가입니다.
네이버 스마트스토어, 쿠팡, 카카오커머스 등에서 높은 전환율을 기록하는 상세페이지를 만드는 것이 목표입니다.

작성 규칙:
- 자연스러운 한국어 구어체 (번역투 금지)
- 한 문장 15자 이내 (Gemini 이미지 생성 시 긴 문장은 뭉개짐)
- 숫자 + 키워드 조합 권장 (예: "택시비 0원!", "3초 접이")
- 구체적 상황과 숫자로 표현 (추상적 표현 금지)
"""


def _load_doc(name: str) -> str:
    path = DOCS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


async def call_openrouter(
    prompt: str,
    model: str = "anthropic/claude-sonnet-4.6",
    system: str = SYSTEM_PROMPT,
    api_key: str = None,
    max_tokens: int = 8000,
) -> str:
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def write_intake(product_info: dict, api_key: str = None) -> str:
    """Phase 1: 제품 정보 분석 및 구조화"""
    section_guide = _load_doc("section_guide.md")
    features = ", ".join(product_info.get("features", []))

    prompt = f"""# 제품 정보 분석

아래 제품 정보를 분석하고 13개 섹션 상세페이지에 필요한 정보를 구조화하세요.

## 제품 정보
- 제품명: {product_info.get('product_name', '')}
- 카테고리: {product_info.get('category', '')}
- 핵심 특징: {features}
- 타겟 고객: {product_info.get('target_customer', '')}
- 정가: {product_info.get('original_price', '')}원
- 할인가: {product_info.get('sale_price', '')}원
- 스타일: {product_info.get('style_preset', 'Minimal')}
- 추가 정보: {product_info.get('extra_info', '')}

## 13개 섹션 구조 참조
{section_guide}

## 산출물 (마크다운)
1. 제품 개요 정리
2. 타겟 고객 페르소나 (구체적 상황 묘사)
3. 핵심 메시지 방향 (한 줄 요약, 슬로건 후보 3개)
4. 13개 섹션별 필요 정보 매핑
5. 톤앤매너 제안
6. 경쟁 우위 / 차별화 포인트

구체적 숫자와 데이터를 포함하세요. 타겟 고객의 언어로 작성하세요."""

    return await call_openrouter(prompt, api_key=api_key)


async def write_research(intake_data: str, market_data: str = "",
                         review_context: str = "",
                         api_key: str = None) -> str:
    """Phase 2: 시장 리서치 분석"""
    section_guide = _load_doc("section_guide.md")
    copy_patterns = _load_doc("copy_patterns.md")

    market_section = ""
    if market_data:
        market_section = f"\n## 네이버 쇼핑 시장 데이터\n{market_data}\n"

    review_section = ""
    if review_context:
        review_section = f"""
## 실제 고객 리뷰 데이터
{review_context}

위 리뷰 데이터에서 반복되는 키워드, 긍정/부정 패턴, 고객이 자주 언급하는 포인트를 분석하세요.
"""

    prompt = f"""# 시장 리서치 분석

## 이전 단계: 제품 분석 결과
{intake_data}
{market_section}
{review_section}

## 참조: 섹션 가이드
{section_guide}

## 참조: 카피 패턴
{copy_patterns}

## 수행 작업
1. 해당 카테고리 시장 동향 분석
2. 경쟁사/유사 제품 3-5개 분석 (가격대, 포지셔닝)
3. 타겟 고객의 핵심 페인포인트 3-5개 (구체적 상황 묘사)
4. 차별화 포인트 도출
5. 마케팅 카피에 활용할 수치/데이터
6. 추천 키워드/훅 (감정을 자극하는 표현)

추상적 표현 금지. 카피에 바로 활용 가능한 형태로 정리."""

    return await call_openrouter(prompt, api_key=api_key)


async def write_copy(intake_data: str, research_data: str,
                     review_context: str = "",
                     api_key: str = None) -> str:
    """Phase 3a: 13개 섹션 마케팅 카피 작성"""
    section_guide = _load_doc("section_guide.md")
    copy_patterns = _load_doc("copy_patterns.md")

    review_section = ""
    if review_context:
        review_section = f"""
## 실제 고객 리뷰 데이터
{review_context}

리뷰에서 추출한 실제 고객 표현과 키워드를 카피에 활용하세요. 특히 Social Proof(07) 섹션에 실제 리뷰 문구를 반영하세요.
"""

    prompt = f"""# 13개 섹션 마케팅 카피 작성

## 이전 단계 산출물
### 제품 분석
{intake_data}

### 시장 리서치
{research_data}
{review_section}

## 참조: 섹션 가이드
{section_guide}

## 참조: 카피 패턴
{copy_patterns}

## 산출물 형식
각 섹션(01~13)별로:
- 섹션 번호와 이름
- 헤드라인 (한국어, 자연스러운 구어체)
- 서브헤드라인
- 본문 카피 (구체적 숫자, 상황 묘사 포함)
- CTA 문구
- 뱃지/태그 텍스트

## 필수 규칙 (매우 중요!)
- 번역투 절대 금지, 자연스러운 한국어
- 한 문장 15자 이내로 짧게 (Gemini 이미지 생성 시 긴 문장은 뭉개짐)
- 숫자 + 키워드 조합 권장 (예: "택시비 0원!", "3초 접이")
- 리뷰/후기 카피: 핵심 한 줄만 (3줄 이상 금지)
- 감정 여정: 주목 → 공감 → 이해 → 희망 → 신뢰 → 확신 → 행동"""

    return await call_openrouter(prompt, api_key=api_key)


async def write_design(intake_data: str, research_data: str,
                       style_preset: str = "Minimal",
                       style_reference: str = "",
                       api_key: str = None) -> str:
    """Phase 3b: 디자인 가이드 작성"""
    design_specs = _load_doc("design_specs.md")
    prompt_patterns = _load_doc("prompt_patterns.md")

    ref_section = ""
    if style_reference:
        ref_section = f"\n## 스타일 레퍼런스 분석 결과\n{style_reference}\n이 스타일을 우선 반영하세요.\n"

    prompt = f"""# 상세페이지 디자인 가이드 작성

## 이전 단계 산출물
### 제품 분석
{intake_data}

### 시장 리서치
{research_data}

## 선택된 스타일 프리셋: {style_preset}
{ref_section}

## 참조: 디자인 스펙
{design_specs}

## 참조: 프롬프트 패턴
{prompt_patterns}

## 산출물
1. 스타일 프리셋 상세 ({style_preset})
2. 컬러 팔레트 (Hex: Primary, Secondary, Accent, Background, Text)
3. 타이포그래피 설정
4. STYLE ANCHOR 문구 (모든 Gemini 프롬프트에 공통 적용할 스타일 요약)
5. 13개 섹션별:
   - 배경 스타일 (색상/그라데이션)
   - 레이아웃 구조
   - 주요 비주얼 요소
   - 높이 (design_specs 참조)

## 필수 준수
- 너비 1200px 고정
- 실사 사진 스타일 (일러스트/카툰/벡터 절대 금지)
- STYLE ANCHOR의 Typography에 Pretendard Bold (weight 700+) 포함
- 밝음/어두움 교차 배경 패턴"""

    return await call_openrouter(prompt, api_key=api_key)


async def write_prompts(copy_data: str, design_data: str,
                        api_key: str = None) -> str:
    """Phase 4: Gemini 이미지 생성용 프롬프트 13개 작성"""
    prompt_patterns = _load_doc("prompt_patterns.md")
    design_specs = _load_doc("design_specs.md")

    prompt = f"""# Gemini 3 Pro 이미지 생성 프롬프트 작성

## 이전 단계 산출물
### 카피라이팅 결과
{copy_data}

### 디자인 가이드
{design_data}

## 참조: 프롬프트 패턴
{prompt_patterns}

## 참조: 디자인 스펙
{design_specs}

## 산출물 형식
각 섹션(01~13)별로 영문 프롬프트. 반드시 이 구조:

## Section XX: [섹션명] (1200x[HEIGHT])

[프롬프트 본문 — 영문]

=== CRITICAL REQUIREMENTS ===
1. EXACT DIMENSIONS: 1200x[HEIGHT] pixels
2. FULL BLEED: Content fills ENTIRE 1200px width
3. WIDTH LOCK: Width MUST be exactly 1200 pixels

=== PHOTOGRAPHY STYLE (MANDATORY) ===
- REALISTIC PHOTOGRAPHY, NOT illustrations or cartoons
- REAL HUMAN MODELS with natural skin texture
- Professional photography lighting

=== STYLE ANCHOR ===
[04-design.md에서 추출한 공통 스타일 문구]
Typography: Pretendard Bold (weight 700+) for ALL Korean text

=== FINAL CHECKLIST ===
- Image is EXACTLY 1200x[HEIGHT] pixels
- Content fills full width with NO side margins
- People shown are realistic photos, NOT illustrations
- Korean text uses Pretendard Bold, all characters are valid Hangul

## 섹션별 높이
01 Hero: 800, 02 Pain: 600, 03 Problem: 500, 04 Story: 700,
05 Solution: 400, 06 How It Works: 600, 07 Social Proof: 800,
08 Authority: 500, 09 Benefits: 700, 10 Risk Removal: 500,
11 Comparison: 400, 12 Target Filter: 400, 13 Final CTA: 600

## 절대 준수 규칙
- 모든 프롬프트 영문 작성 (Gemini에 더 효과적)
- 한국어 텍스트는 따옴표 안에 명시
- 4개 필수 블록: CRITICAL REQUIREMENTS, PHOTOGRAPHY STYLE, STYLE ANCHOR, FINAL CHECKLIST
- px 수치 금지 (14px, 24px 등) — Gemini가 이미지에 렌더링함
- CSS 스펙 금지 (border-radius, rgba, shadow 등)
- 텍스트 크기는 "large", "medium", "standard" 등 상대적 표현만
- 한 문장 15자 이내
- STYLE ANCHOR Typography에 Pretendard Bold (weight 700+) 필수"""

    return await call_openrouter(prompt, api_key=api_key, max_tokens=12000)
