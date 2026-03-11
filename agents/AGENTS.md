# 상세페이지 에이전트 팀 정의

## 팀 구성

| 에이전트 | Claude Code 매핑 | 모델 | 역할 |
|---------|-----------------|------|------|
| 정보수집 | analyst | sonnet | 제품 정보 구조화 |
| 리서치 | document-specialist | sonnet | 시장/경쟁사 리서치 |
| 카피라이팅 | writer | sonnet | 13섹션 마케팅 카피 |
| 디자인 | designer | sonnet | 스타일/레이아웃 가이드 |
| 프롬프팅 | executor | sonnet | Gemini 이미지 프롬프트 |

## 파이프라인

```
Phase 1 (순차): 정보수집 (analyst)
Phase 2 (순차): 리서치 (document-specialist) + 네이버 쇼핑 API 시장 데이터
Phase 3 (병렬): 카피라이팅 (writer) ∥ 디자인 (designer)
Phase 4 (순차): 프롬프팅 (executor)
Phase 5 (순차): Gemini 3 Pro 이미지 생성 × 13
Phase 6 (순차): Pillow 이미지 합성
```

## 중간 산출물

- 01-intake.md → 정보수집 에이전트 산출물
- 02-research.md → 리서치 에이전트 산출물
- 03-copy.md → 카피라이팅 에이전트 산출물
- 04-design.md → 디자인 에이전트 산출물
- 05-prompt.md → 프롬프팅 에이전트 산출물

## 참조 문서

- docs/section_guide.md → 13섹션 구조/역할
- docs/copy_patterns.md → 카피 패턴/공식
- docs/design_specs.md → 디자인 스펙/사이즈
- docs/prompt_patterns.md → Gemini 프롬프트 패턴

## 전체 에이전트 공통 규칙

### 이미지 렌더링 규칙 (카피/디자인/프롬프팅 에이전트 필수)
- **한글 폰트**: Pretendard Bold (weight 700+) — 모든 한글에 필수 적용
- **한글 길이**: 한 문장 15자 이내 (긴 문장은 Gemini가 뭉갬)
- **px 수치 금지**: 프롬프트에 14px, 24px 등 px 단위 넣지 말 것 — Gemini가 이미지에 렌더링
- **CSS 스펙 금지**: border-radius, rgba, shadow 등 CSS 값 넣지 말 것
- **크기 표현**: "large", "medium", "standard" 등 상대적 표현만 사용
- **스타일**: 실사 사진 (일러스트/카툰/벡터 절대 금지)
- **너비**: 1200px 고정 (절대 변경 금지)

### 산출물 저장 위치
- 모든 중간 산출물(01~05-*.md)은 `output/{job_id}/` 폴더에 저장
- 프로젝트 루트에 산출물 파일을 생성하지 말 것
