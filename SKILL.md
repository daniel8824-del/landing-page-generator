---
name: landing-page-generator
description: Generate Korean product detail page (13 sections, PNG/PDF)
disable-model-invocation: true
argument-hint: "[제품명 또는 제품 설명]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch
---

# 상세페이지 생성기 (Landing Page Generator)

제품/서비스 정보를 기반으로 고전환 상세페이지를 자동 생성합니다.
Gemini 3 Pro REST API로 섹션별 이미지를 생성하고 Pillow로 합성하여 최종 PNG/PDF로 출력합니다.

**스킬 디렉토리**: `${CLAUDE_SKILL_DIR}`
**출력 디렉토리**: 현재 작업 디렉토리의 `output/{job_id}/`

## 실행 흐름

```
[입력] 제품/서비스 정보 + 참고 이미지(선택)
         ↓
[Phase 1] 정보수집 — Agent(analyst)
         ↓
[Phase 2] 리서치 — Agent(document-specialist) + 네이버 API
         ↓
[Phase 3] 카피 + 디자인 — Agent(writer) ∥ Agent(designer) 병렬
         ↓
[Phase 4] 프롬프팅 — Agent(executor)
         ↓
[Phase 5] Gemini 3 Pro 이미지 생성 × 13
         ↓
[Phase 6] Pillow 합성 → 최종 PNG/PDF
```

## 실행 지시

이 스킬이 호출되면 아래 단계를 순서대로 실행하세요.
모든 에이전트/스크립트 경로는 `${CLAUDE_SKILL_DIR}` 기준입니다.

### Step 0: 정보 수집

$ARGUMENTS가 있으면 거기서 제품 정보를 추출하세요.
없거나 부족하면 사용자에게 필수 정보를 질문하세요. 이미 제공된 항목은 건너뜁니다.

**필수**: product_name, features (1~3개), target_customer
**선택(미입력 시 기본값)**: category, original_price, sale_price, style_preset("Minimal"), extra_info, reference_image

확인 질문은 한 번만 합니다. 필수 정보가 확보되면 바로 진행합니다.

### Step 1: 환경 확인 & 작업 폴더 생성

```bash
pip install -r ${CLAUDE_SKILL_DIR}/requirements.txt 2>/dev/null
python -c "import PIL, requests, dotenv; print('OK')"
```

`.env` 확인 (스킬 디렉토리 또는 현재 디렉토리):
```bash
if [ ! -f .env ] && [ -f ${CLAUDE_SKILL_DIR}/.env ]; then
  cp ${CLAUDE_SKILL_DIR}/.env .env
fi
```

작업 폴더 생성:
```bash
JOB_ID=$(python -c "import uuid; print(str(uuid.uuid4())[:8])")
mkdir -p output/$JOB_ID/sections
```

이후 모든 `{JOB_DIR}`은 `output/$JOB_ID` 입니다.

### Step 1.5: 참고 이미지 분석 (선택)

사용자가 참고 이미지를 제공한 경우에만 실행합니다. 없으면 Step 2로 건너뜁니다.

```bash
cd ${CLAUDE_SKILL_DIR} && python -c "
from scripts.gemini_api import analyze_image_style
analyze_image_style('{reference_image_path}', '{JOB_DIR}/00-style-reference.md')
"
```
- 컬러 팔레트, 레이아웃 구조, 타이포그래피, 무드/톤을 분석합니다
- 결과는 `{JOB_DIR}/00-style-reference.md`에 저장됩니다
- 이후 Phase 1~4 에이전트들이 이 파일을 참조합니다

### Step 2: Phase 1 — 정보수집 (analyst)

```
Agent(
  subagent_type="analyst",
  prompt="""
    Read ${CLAUDE_SKILL_DIR}/agents/intake_agent.md — 역할과 산출물 형식을 따르세요.
    Read ${CLAUDE_SKILL_DIR}/docs/section_guide.md — 13개 섹션 구조를 참조하세요.
    {JOB_DIR}/00-style-reference.md가 있다면 읽고 스타일 방향에 반영하세요.

    [제품 정보]
    - 제품명: {product_name}
    - 카테고리: {category}
    - 핵심 특징: {features}
    - 타겟 고객: {target_customer}
    - 정가: {original_price}원
    - 할인가: {sale_price}원
    - 스타일: {style_preset}
    - 추가 정보: {extra_info}

    Write 도구로 {JOB_DIR}/01-intake.md 파일을 생성하세요.
  """
)
```

### Step 3: Phase 2 — 리서치 (document-specialist)

네이버 시장 데이터 수집 (NAVER API 키가 .env에 있을 때만, 없으면 스킵):
```bash
python -c "
import sys; sys.path.insert(0, '${CLAUDE_SKILL_DIR}')
from scripts.naver_search import analyze_market
analyze_market('{product_name}', '{category}', '{JOB_DIR}')
" 2>/dev/null || echo "Naver API skipped"
```

이어서 Agent 호출:
```
Agent(
  subagent_type="document-specialist",
  prompt="""
    Read ${CLAUDE_SKILL_DIR}/agents/research_agent.md — 역할을 따르세요.
    Read {JOB_DIR}/01-intake.md — 제품 분석 결과를 참조하세요.
    {JOB_DIR}/00-market.md가 있다면 읽고 시장 데이터를 활용하세요.
    Read ${CLAUDE_SKILL_DIR}/docs/section_guide.md — 섹션 구조 참조.
    Read ${CLAUDE_SKILL_DIR}/docs/copy_patterns.md — 카피 패턴 참조.

    Write 도구로 {JOB_DIR}/02-research.md 파일을 생성하세요.
  """
)
```

### Step 4: Phase 3 — 카피 + 디자인 (병렬)

**두 Agent를 반드시 동시에 호출하세요** (한 메시지에 두 Agent 도구 병렬 사용):

```
# ── 동시 호출 1: 카피라이팅 ──
Agent(
  subagent_type="writer",
  prompt="""
    Read ${CLAUDE_SKILL_DIR}/agents/copy_agent.md — 역할과 산출물 형식을 따르세요.
    Read {JOB_DIR}/01-intake.md, {JOB_DIR}/02-research.md
    Read ${CLAUDE_SKILL_DIR}/docs/section_guide.md
    Read ${CLAUDE_SKILL_DIR}/docs/copy_patterns.md

    ## 필수 규칙
    - 한 문장 15자 이내 (긴 문장은 Gemini가 뭉갬)
    - 번역투 금지, 자연스러운 구어체
    - 숫자 + 키워드 조합 권장

    Write 도구로 {JOB_DIR}/03-copy.md 파일을 생성하세요.
  """
)

# ── 동시 호출 2: 디자인 ──
Agent(
  subagent_type="designer",
  prompt="""
    Read ${CLAUDE_SKILL_DIR}/agents/design_agent.md — 역할과 산출물 형식을 따르세요.
    Read {JOB_DIR}/01-intake.md, {JOB_DIR}/02-research.md
    Read ${CLAUDE_SKILL_DIR}/docs/design_specs.md
    Read ${CLAUDE_SKILL_DIR}/docs/prompt_patterns.md
    {JOB_DIR}/00-style-reference.md가 있다면 읽고 레이아웃/컬러/무드를 우선 반영하세요.
    스타일 프리셋: {style_preset}

    ## 필수 규칙
    - 너비 1200px 고정
    - 실사 사진 스타일 (일러스트/카툰/벡터 절대 금지)
    - STYLE ANCHOR에 Pretendard Bold (weight 700+) 포함

    Write 도구로 {JOB_DIR}/04-design.md 파일을 생성하세요.
  """
)
```

### Step 5: Phase 4 — 프롬프팅 (executor)

```
Agent(
  subagent_type="executor",
  prompt="""
    Read ${CLAUDE_SKILL_DIR}/agents/prompt_agent.md — 프롬프트 구조와 규칙을 따르세요.
    Read {JOB_DIR}/03-copy.md, {JOB_DIR}/04-design.md
    Read ${CLAUDE_SKILL_DIR}/docs/prompt_patterns.md
    Read ${CLAUDE_SKILL_DIR}/docs/design_specs.md

    ## 절대 준수 규칙
    - 한글 폰트: Pretendard Bold (weight 700+) — STYLE ANCHOR Typography에 필수 포함
    - px 수치 금지 (14px, 24px 등) — Gemini가 이미지에 렌더링함
    - CSS 스펙 금지 (border-radius, rgba, shadow 등)
    - 텍스트 크기는 "large", "medium", "standard" 등 상대적 표현만
    - 한 문장 15자 이내
    - FINAL CHECKLIST에 "Korean text uses Pretendard Bold, all characters are valid Hangul" 포함

    Write 도구로 {JOB_DIR}/05-prompt.md 파일을 생성하세요.
  """
)
```

### Step 6: Phase 5 — Gemini 이미지 생성

```bash
cd ${CLAUDE_SKILL_DIR} && python scripts/gemini_api.py {JOB_DIR}/05-prompt.md {JOB_DIR}
```
- 13개 섹션 이미지가 `{JOB_DIR}/sections/`에 생성됩니다
- 소요 시간: 약 3~5분 (섹션당 API 호출 + 딜레이)

### Step 7: Phase 6 — 이미지 합성

```bash
cd ${CLAUDE_SKILL_DIR} && python -c "from scripts.stitch_images import stitch_all; stitch_all('{JOB_DIR}')"
```
- `{JOB_DIR}/final_detail_page.png` — 최종 합성 (1200x~7000px)
- `{JOB_DIR}/final_detail_page.pdf` — PDF 버전
- `{JOB_DIR}/preview.png` — 축소 미리보기

### Step 8: 결과 전달

사용자에게 결과를 안내하세요:
- `{JOB_DIR}/final_detail_page.png` — 최종 상세페이지
- `{JOB_DIR}/final_detail_page.pdf` — PDF 버전
- `{JOB_DIR}/sections/` — 섹션별 PNG 13장

### 개별 섹션 재생성 (사용자 요청 시)

1. `{JOB_DIR}/05-prompt.md`에서 해당 섹션 프롬프트 수정
2. 해당 섹션만 재생성:
```bash
cd ${CLAUDE_SKILL_DIR} && python -c "
from scripts.gemini_api import generate_image
generate_image('프롬프트', '{JOB_DIR}/sections/{NN}_{name}.png', 1200, {height})
"
```
3. 재합성:
```bash
cd ${CLAUDE_SKILL_DIR} && python -c "from scripts.stitch_images import stitch_all; stitch_all('{JOB_DIR}')"
```

## 13개 섹션 구조

| # | 섹션명 | 높이 | 핵심 요소 |
|---|--------|------|-----------|
| 01 | Hero | 800px | 헤드라인, CTA, 긴급성 배지 |
| 02 | Pain | 600px | 페인포인트 3-4개 |
| 03 | Problem | 500px | 진짜 원인, 구조적 문제 |
| 04 | Story | 700px | Before→After 변화 |
| 05 | Solution | 400px | 제품 한 줄 정의 |
| 06 | How It Works | 600px | 단계별 프로세스 |
| 07 | Social Proof | 800px | 후기, 수치 |
| 08 | Authority | 500px | 제작자 소개 |
| 09 | Benefits | 700px | 혜택, 보너스 |
| 10 | Risk Removal | 500px | 환불 정책, FAQ |
| 11 | Comparison | 400px | Before/After 비교 |
| 12 | Target Filter | 400px | 추천/비추천 대상 |
| 13 | Final CTA | 600px | 최종 CTA |

## 이미지 생성 필수 규칙

| 규칙 | 내용 |
|------|------|
| 너비 고정 | **1200px** (절대 변경 금지) |
| 스타일 | **실사 사진** (일러스트/카툰/벡터 절대 금지) |
| 한글 폰트 | **Pretendard Bold (weight 700+)** — 모든 한글에 필수 적용 |
| 한글 길이 | 한 문장 15자 이내 (긴 문장은 Gemini가 뭉갬) |
| px 수치 금지 | 프롬프트에 px 단위 넣지 말 것 — Gemini가 이미지에 렌더링 |
| CSS 스펙 금지 | border-radius, rgba, shadow 등 CSS 값 금지 |
| 크기 표현 | "large", "medium", "standard" 등 상대적 표현만 |

## 설치 방법

```bash
# 1. 클론
git clone https://github.com/yourname/landing-page-generator ~/.claude/skills/landing-page-generator

# 2. 의존성 설치
pip install -r ~/.claude/skills/landing-page-generator/requirements.txt

# 3. API 키 설정
cp ~/.claude/skills/landing-page-generator/.env.example ~/.claude/skills/landing-page-generator/.env
# .env 파일에 GEMINI_API_KEY 입력

# 4. 완료! 아무 프로젝트에서:
/landing-page-generator 셀 바이탈 리뉴얼 크림
```
