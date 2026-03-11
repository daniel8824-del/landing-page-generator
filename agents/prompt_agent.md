# 프롬프팅 에이전트 (Prompt Agent)

## 역할
카피와 디자인 결과를 병합하여 Gemini 3 Pro 이미지 생성용 프롬프트 13개를 작성합니다.

## Claude Code 매핑
- 서브에이전트: `executor`
- 모델: `sonnet`

## 입력
- `03-copy.md`, `04-design.md`

## 산출물
- `05-prompt.md`

## 참조 문서
- `docs/prompt_patterns.md` - 프롬프트 템플릿, 필수 사항, 체크리스트
- `docs/design_specs.md` - 섹션별 높이, 컬러 사용 가이드

## 프롬프트 구조 (각 섹션)

```
## Section XX: [섹션명] (1200x[HEIGHT])

Create a professional [section type] section for a Korean landing page.

=== CRITICAL REQUIREMENTS ===
1. EXACT DIMENSIONS: 1200x[HEIGHT] pixels
2. FULL BLEED: Content fills ENTIRE 1200px width
3. WIDTH LOCK: Image width MUST be exactly 1200 pixels

=== PHOTOGRAPHY STYLE (MANDATORY) ===
- REALISTIC PHOTOGRAPHY, NOT illustrations
- REAL HUMAN MODELS with natural skin texture
- Professional photography lighting
- Style reference: Sulwhasoo, Innisfree, Laneige quality

[LAYOUT - 04-design.md 기반]
[CONTENT - 03-copy.md 카피 텍스트]
[STYLE - 컬러, 타이포, 무드]

=== STYLE ANCHOR ===
[04-design.md에서 추출한 공통 스타일 문구]

=== SERIES CONTEXT ===
Section XX of 13 in a landing page series.

=== FINAL CHECKLIST ===
✓ EXACTLY 1200x[HEIGHT] pixels
✓ Full width, NO side margins
✓ Realistic photos, NOT illustrations
✓ Korean text clear and readable
✓ Professional advertising quality
```

## 섹션별 높이 (필수)
| 섹션 | 높이 |
|------|------|
| 01 Hero | 800px |
| 02 Pain | 600px |
| 03 Problem | 500px |
| 04 Story | 700px |
| 05 Solution | 400px |
| 06 How | 600px |
| 07 Proof | 800px |
| 08 Authority | 500px |
| 09 Benefits | 700px |
| 10 Risk | 500px |
| 11 Compare | 400px |
| 12 Filter | 400px |
| 13 CTA | 600px |

## 한글 렌더링 규칙 (매우 중요!)
- 한글 폰트: **Pretendard Bold (weight 700+)** — STYLE ANCHOR Typography에 반드시 포함
- 본문 텍스트: 최소 28pt 이상, 헤드라인: 48pt 이상
- 한 문장 15자 이내로 짧게 (긴 문장은 Gemini가 뭉갬)
- 숫자 + 키워드 조합 권장 (예: "택시비 0원!", "3초 접이")
- 리뷰/후기: 핵심 한 줄만 (3줄 이상 금지)
- Q&A 답변: 10자 이내 간결하게

## 프롬프트 작성 금지 사항 (필수!)
- **px 단위 수치 금지** (14px, 24px, 40px 등) — Gemini가 이미지에 그대로 렌더링함
- **CSS 스펙 값 금지** (border-radius, rgba, shadow, padding 등)
- 텍스트 크기는 "large", "medium", "standard" 등 **상대적 표현만** 사용

## 품질 기준
- 모든 프롬프트 영문 작성 (Gemini 효과적)
- 한국어 텍스트는 따옴표 안에 명시
- 4개 필수 블록 포함 (CRITICAL, PHOTOGRAPHY, ANCHOR, CHECKLIST)
- STYLE ANCHOR에 `Pretendard Bold (weight 700+)` 포함 필수
- FINAL CHECKLIST에 `Korean text uses Pretendard Bold, all characters are valid Hangul` 포함 필수
- 스타일 일관성 유지
