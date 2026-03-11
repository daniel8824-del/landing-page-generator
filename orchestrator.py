import subprocess
import json
import os
import sys
import threading
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
AGENTS_DIR = BASE_DIR / "agents"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "_temp"

# Reference to app.py's job store – set by init_jobs()
_jobs = None


def init_jobs(jobs_dict: dict):
    """Connect to app.py's shared job store"""
    global _jobs
    _jobs = jobs_dict


def update_job(job_id: str, phase: str, status: str, message: str):
    """Update job progress"""
    if _jobs is None or job_id not in _jobs:
        return
    _jobs[job_id]["phase"] = phase
    _jobs[job_id]["progress"].append({
        "phase": phase,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })


def run_claude_agent(agent_type: str, prompt_file: str, output_file: str,
                     job_output_dir: str = None) -> str:
    """Run a Claude Code sub-agent via CLI.

    prompt_file: temp file containing the full prompt (avoids Windows CLI length limit)
    output_file: expected output file name (e.g. '01-intake.md')
    job_output_dir: if set, write output directly here (no root folder pollution)
    """
    # Determine actual output path
    if job_output_dir:
        actual_output = str(Path(job_output_dir) / output_file)
    else:
        actual_output = str(BASE_DIR / output_file)

    # Short CLI prompt — tells Claude to read the temp file and write to exact path
    short_prompt = (
        f"Read the file {prompt_file} and follow all instructions in it exactly. "
        f"Write your complete output to {actual_output}. "
        f"Working directory: {BASE_DIR}"
    )

    cmd = [
        "claude", "-p", short_prompt,
        "--allowedTools", "Write,Read,WebSearch,WebFetch",
        "--output-format", "text"
    ]

    # Remove CLAUDECODE env var to allow nested CLI invocation
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    use_shell = sys.platform == "win32"

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(BASE_DIR),
        timeout=600,
        shell=use_shell,
        env=env
    )

    actual_path = Path(actual_output)
    root_path = BASE_DIR / output_file
    content = ""

    # Check actual output path first
    if actual_path.exists():
        content = actual_path.read_text(encoding="utf-8")
        if len(content.strip()) <= 50:
            content = ""

    # Fallback: check root (claude may ignore the full path)
    if not content and root_path.exists() and root_path != actual_path:
        content = root_path.read_text(encoding="utf-8")
        if len(content.strip()) > 50:
            # Move to correct location
            actual_path.write_text(content, encoding="utf-8")
            root_path.unlink()
            print(f"[MOVE] {output_file} root → {actual_path}")
        else:
            content = ""

    # Fallback: save stdout if file wasn't created or is too short
    if not content:
        stdout = result.stdout.strip()
        if stdout and len(stdout) > 50:
            actual_path.write_text(stdout, encoding="utf-8")
            content = stdout
        else:
            print(f"[WARN] Agent '{agent_type}' produced minimal output for {output_file}")
            if result.stderr:
                print(f"[WARN] stderr: {result.stderr[:500]}")
            return stdout or ""

    print(f"[OK] {output_file} → {actual_path}")
    return content


def write_temp_prompt(name: str, content: str) -> str:
    """Write a prompt to a temp file, return the file path."""
    TEMP_DIR.mkdir(exist_ok=True)
    path = TEMP_DIR / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    return str(path)


def run_pipeline(job_id: str, product_info: dict, reference_image_path: str = None):
    """Main pipeline orchestration - runs all phases"""
    try:
        job_output_dir = OUTPUT_DIR / job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)
        TEMP_DIR.mkdir(exist_ok=True)

        # ===== Phase 1: Intake Agent (analyst) =====
        update_job(job_id, "intake", "running", "제품 정보를 분석하고 있습니다...")

        # Style reference analysis (if image provided)
        style_ref_section = ""
        if reference_image_path and os.path.exists(reference_image_path):
            from scripts.gemini_api import analyze_image_style
            style_ref_path = str(job_output_dir / "00-style-reference.md")
            analyze_image_style(reference_image_path, style_ref_path)
            if (job_output_dir / "00-style-reference.md").exists():
                style_ref_section = f"\n\n[스타일 레퍼런스]\n{style_ref_path} 파일을 Read로 읽어서 참고하세요."

        features_str = ", ".join(product_info.get("features", []))

        intake_prompt = f"""# 정보수집 에이전트 지시사항

## 역할
당신은 제품 분석 전문가입니다. 아래 제품 정보를 분석하고 13개 섹션 상세페이지에 필요한 정보를 구조화하세요.

## 에이전트 정의
agents/intake_agent.md 파일을 Read로 읽고 역할과 산출물 형식을 따르세요.

## 참조 문서
docs/section_guide.md 파일을 Read로 읽고 13개 섹션 구조를 참조하세요.

## 사용자 제품 정보
- 제품명: {product_info.get('product_name', '')}
- 카테고리: {product_info.get('category', '')}
- 핵심 특징: {features_str}
- 타겟 고객: {product_info.get('target_customer', '')}
- 정가: {product_info.get('original_price', '')}원
- 할인가: {product_info.get('sale_price', '')}원
- 스타일 프리셋: {product_info.get('style_preset', 'Minimal')}
- 추가 정보: {product_info.get('extra_info', '')}
{style_ref_section}

## 산출물
01-intake.md 파일에 다음을 포함하여 작성:
1. 제품 개요 정리
2. 타겟 고객 페르소나 (구체적 상황 묘사)
3. 핵심 메시지 방향 (한 줄 요약, 슬로건 후보)
4. 13개 섹션별 필요 정보 매핑
5. 톤앤매너 제안
6. 경쟁 우위 / 차별화 포인트

## 주의사항
- 반드시 Write 도구로 01-intake.md 파일을 생성하세요
- 모든 13개 섹션에 대한 정보가 빠짐없이 매핑되어야 합니다
- 구체적 숫자와 데이터를 포함하세요
- 타겟 고객의 언어로 작성하세요
"""

        prompt_path = write_temp_prompt("phase1_intake", intake_prompt)
        run_claude_agent("analyst", prompt_path, "01-intake.md", str(job_output_dir))
        update_job(job_id, "intake", "completed", "제품 정보 분석 완료")

        # ===== Phase 2: Research Agent (document-specialist) =====
        update_job(job_id, "research", "running", "시장 리서치를 진행하고 있습니다...")

        # Naver Shopping market data
        naver_section = ""
        try:
            from scripts.naver_search import analyze_market
            product_name = product_info.get('product_name', '')
            category = product_info.get('category', '')
            if product_name:
                market_path = analyze_market(product_name, category, str(job_output_dir))
                if market_path and os.path.exists(market_path):
                    naver_section = f"\n\n## 네이버 쇼핑 시장 데이터\n{market_path} 파일을 Read로 읽고 시장 분석에 활용하세요."
        except Exception as e:
            print(f"[WARN] Naver search failed (continuing without): {e}")

        research_prompt = f"""# 리서치 에이전트 지시사항

## 역할
당신은 시장 리서치 전문가입니다. 제품 정보를 바탕으로 시장 리서치를 수행하세요.

## 에이전트 정의
agents/research_agent.md 파일을 Read로 읽고 역할과 수행 작업을 따르세요.

## 이전 단계 산출물
{job_output_dir}/01-intake.md 파일을 Read로 읽고 제품 분석 결과를 참조하세요.

## 참조 문서
- docs/section_guide.md — 섹션별 필요 정보
- docs/copy_patterns.md — 신뢰 구축 표현, 숫자 활용법
위 파일들을 Read로 읽고 참조하세요.
{naver_section}

## 수행 작업
1. 해당 카테고리 시장 동향 분석
2. 경쟁사/유사 제품 3-5개 분석 (가격대, 포지셔닝)
3. 타겟 고객의 핵심 페인포인트 3-5개 (구체적 상황 묘사)
4. 차별화 포인트 도출
5. 마케팅 카피에 활용할 수치/데이터
6. 추천 키워드/훅 (감정을 자극하는 표현)

## 산출물
02-research.md 파일에 위 6개 항목을 상세히 작성하세요.

## 주의사항
- 반드시 Write 도구로 02-research.md 파일을 생성하세요
- 추상적 표현 금지, 구체적 상황과 숫자로 작성
- 카피에 바로 활용 가능한 형태로 정리
"""

        prompt_path = write_temp_prompt("phase2_research", research_prompt)
        run_claude_agent("document-specialist", prompt_path, "02-research.md", str(job_output_dir))
        update_job(job_id, "research", "completed", "시장 리서치 완료")

        # ===== Phase 3: Copy + Design Agents (parallel) =====
        update_job(job_id, "copy+design", "running", "카피라이팅과 디자인을 동시 진행합니다...")

        style = product_info.get('style_preset', 'Minimal')

        copy_prompt = f"""# 카피라이팅 에이전트 지시사항

## 역할
당신은 고전환 마케팅 카피라이터입니다. 13개 섹션별 마케팅 카피를 작성하세요.

## 에이전트 정의
agents/copy_agent.md 파일을 Read로 읽고 역할과 산출물 형식을 따르세요.

## 이전 단계 산출물 (반드시 Read로 읽으세요)
- {job_output_dir}/01-intake.md — 제품 분석
- {job_output_dir}/02-research.md — 시장 리서치

## 참조 문서 (반드시 Read로 읽으세요)
- docs/section_guide.md — 13개 섹션 구조, 감정 여정
- docs/copy_patterns.md — 헤드라인 공식, 공감 패턴, CTA

## 산출물
03-copy.md 파일에 각 섹션(01~13)별로:
- 섹션 번호와 이름
- 헤드라인 (한국어, 자연스러운 구어체)
- 서브헤드라인
- 본문 카피 (구체적 숫자, 상황 묘사 포함)
- CTA 문구 (해당 섹션)
- 뱃지/태그 텍스트 (해당 섹션)

## 품질 기준
- 번역투 절대 금지, 자연스러운 한국어
- 한 문장 15자 이내로 짧게 작성 (Gemini 이미지 생성 시 긴 문장은 뭉개짐)
- 숫자 + 키워드 조합 권장 (예: "택시비 0원!", "3초 접이")
- 리뷰/후기 카피: 핵심 한 줄만 (3줄 이상 금지)
- 구체적 숫자와 상황 묘사 필수
- 감정 여정: 주목 → 공감 → 이해 → 희망 → 신뢰 → 확신 → 행동
- 반드시 Write 도구로 03-copy.md 파일을 생성하세요
"""

        design_prompt = f"""# 디자인 에이전트 지시사항

## 역할
당신은 상세페이지 디자인 디렉터입니다. 전체 스타일 방향과 13개 섹션별 디자인 가이드를 작성하세요.

## 에이전트 정의
agents/design_agent.md 파일을 Read로 읽고 역할과 산출물 형식을 따르세요.

## 이전 단계 산출물 (반드시 Read로 읽으세요)
- {job_output_dir}/01-intake.md — 제품 분석
- {job_output_dir}/02-research.md — 시장 리서치

## 참조 문서 (반드시 Read로 읽으세요)
- docs/design_specs.md — 1200px 너비, 섹션별 높이, 스타일 프리셋
- docs/prompt_patterns.md — Gemini 프롬프트 필수 블록

## 선택된 스타일 프리셋: {style}
{style_ref_section}

## 산출물
04-design.md 파일에:
1. 스타일 프리셋 상세 ({style})
2. 컬러 팔레트 (Hex 코드: Primary, Secondary, Accent, Background, Text)
3. 타이포그래피 설정
4. STYLE ANCHOR 문구 (모든 Gemini 프롬프트에 공통 적용할 스타일 요약)
5. 13개 섹션별:
   - 배경 스타일 (색상/그라데이션)
   - 레이아웃 구조 (요소 배치)
   - 주요 비주얼 요소
   - 높이 (design_specs.md 참조)

## 필수 준수
- 너비 1200px 고정
- 실사 사진 스타일 (일러스트/카툰/벡터 절대 금지)
- 밝음/어두움 교차 배경 패턴
- 반드시 Write 도구로 04-design.md 파일을 생성하세요
"""

        copy_prompt_path = write_temp_prompt("phase3_copy", copy_prompt)
        design_prompt_path = write_temp_prompt("phase3_design", design_prompt)

        copy_thread = threading.Thread(
            target=run_claude_agent,
            args=("writer", copy_prompt_path, "03-copy.md", str(job_output_dir))
        )
        design_thread = threading.Thread(
            target=run_claude_agent,
            args=("designer", design_prompt_path, "04-design.md", str(job_output_dir))
        )

        copy_thread.start()
        design_thread.start()
        copy_thread.join(timeout=600)
        design_thread.join(timeout=600)

        update_job(job_id, "copy+design", "completed", "카피라이팅 & 디자인 완료")

        # ===== Phase 4: Prompt Agent (executor) =====
        update_job(job_id, "prompt", "running", "Gemini 이미지 프롬프트를 생성합니다...")

        prompt_gen = f"""# 프롬프팅 에이전트 지시사항

## 역할
당신은 AI 이미지 생성 프롬프트 엔지니어입니다.
카피와 디자인 결과를 병합하여 Gemini 3 Pro 이미지 생성용 프롬프트 13개를 작성하세요.

## 에이전트 정의
agents/prompt_agent.md 파일을 Read로 읽고 프롬프트 구조와 품질 기준을 따르세요.

## 이전 단계 산출물 (반드시 Read로 읽으세요)
- {job_output_dir}/03-copy.md — 카피라이팅 결과
- {job_output_dir}/04-design.md — 디자인 가이드

## 참조 문서 (반드시 Read로 읽으세요)
- docs/prompt_patterns.md — Gemini 프롬프트 템플릿, 필수 블록
- docs/design_specs.md — 섹션별 높이, 컬러 가이드

## 산출물 형식
05-prompt.md 파일에 각 섹션(01~13)별로 영문 프롬프트를 작성.
각 프롬프트는 반드시 다음 구조를 따르세요:

```
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

=== FINAL CHECKLIST ===
- Image is EXACTLY 1200x[HEIGHT] pixels
- Content fills full width with NO side margins
- People shown are realistic photos, NOT illustrations
- Korean text is clear and readable
```

## 필수 준수
- 모든 프롬프트는 영문으로 작성 (Gemini에 더 효과적)
- 한국어 텍스트(카피)는 따옴표 안에 명시
- 4개 필수 블록: CRITICAL REQUIREMENTS, PHOTOGRAPHY STYLE, STYLE ANCHOR, FINAL CHECKLIST
- 반드시 Write 도구로 05-prompt.md 파일을 생성하세요

## 한글 렌더링 규칙 (매우 중요! 반드시 준수!)
- 한글 폰트: Pretendard Bold (weight 700+) 명시 — STYLE ANCHOR의 Typography 항목에 반드시 포함
- 본문 텍스트: 최소 28pt, 헤드라인: 48pt 이상
- 한 문장 15자 이내로 짧게! 긴 문장은 Gemini가 글자를 뭉개므로 금지
- 숫자 + 키워드 조합 권장 (예: "택시비 0원!", "3초 접이")
- 리뷰/후기: 핵심 한 줄만 (3줄 이상 금지)
- Q&A 답변: 10자 이내 간결하게
- 프롬프트에 px 단위 수치(14px, 24px, 40px 등) 절대 넣지 말 것 — Gemini가 이미지에 그대로 렌더링함
- CSS 스펙 값(border-radius, rgba, shadow 등)도 넣지 말 것
- 텍스트 크기는 "large", "medium", "standard" 등 상대적 표현만 사용
- FINAL CHECKLIST에 "Korean text uses Pretendard Bold, all characters are valid Hangul" 포함할 것
"""

        prompt_path = write_temp_prompt("phase4_prompt", prompt_gen)
        run_claude_agent("executor", prompt_path, "05-prompt.md", str(job_output_dir))
        update_job(job_id, "prompt", "completed", "Gemini 프롬프트 13개 생성 완료")

        # ===== Phase 5: Image Generation =====
        update_job(job_id, "image_gen", "running", "Gemini 3 Pro로 이미지를 생성합니다...")

        prompt_md = job_output_dir / "05-prompt.md"
        if not prompt_md.exists():
            raise FileNotFoundError(
                f"05-prompt.md not found. Phase 4 agent failed to create it."
            )

        sections_dir = job_output_dir / "sections"
        sections_dir.mkdir(exist_ok=True)

        from scripts.gemini_api import generate_image
        import re as _re

        _content = prompt_md.read_text(encoding="utf-8")
        _sections = _re.split(r'## Section (\d+)[:\s]', _content)
        _heights = {
            1: 800, 2: 600, 3: 500, 4: 700, 5: 400,
            6: 600, 7: 800, 8: 500, 9: 700, 10: 500,
            11: 400, 12: 400, 13: 600
        }
        _names = {
            1: "hero", 2: "pain", 3: "problem", 4: "story",
            5: "solution", 6: "how_it_works", 7: "social_proof",
            8: "authority", 9: "benefits", 10: "risk_removal",
            11: "comparison", 12: "target_filter", 13: "final_cta"
        }

        _prompts = []
        for _i in range(1, len(_sections), 2):
            if _i + 1 < len(_sections):
                _num = int(_sections[_i])
                _raw = _sections[_i + 1].strip()
                _raw = _re.sub(r'^```\w*\n', '', _raw)
                _raw = _re.sub(r'\n```$', '', _raw)
                _prompts.append({"num": _num, "prompt": _raw.strip()})

        _total = len(_prompts)
        update_job(job_id, "image_gen", "running", f"총 {_total}개 섹션 이미지 생성 시작")
        _generated = 0

        for _idx, _sec in enumerate(_prompts, 1):
            _num = _sec["num"]
            _name = _names.get(_num, f"section_{_num}")
            _height = _heights.get(_num, 600)
            _filename = f"{_num:02d}_{_name}.png"
            _out = str(sections_dir / _filename)

            # 이미 생성된 이미지는 스킵
            if os.path.exists(_out) and os.path.getsize(_out) > 1000:
                _generated += 1
                update_job(job_id, "image_gen", "running",
                           f"[{_idx}/{_total}] Section {_num:02d} ({_name}) — 이미 존재, 스킵")
                continue

            update_job(job_id, "image_gen", "running",
                       f"[{_idx}/{_total}] Section {_num:02d} ({_name}) 생성 중...")

            _result = generate_image(_sec["prompt"], _out, 1200, _height)
            if _result:
                _generated += 1
                update_job(job_id, "image_gen", "running",
                           f"[{_idx}/{_total}] Section {_num:02d} 완료 ({_generated}개 성공)")
            else:
                update_job(job_id, "image_gen", "running",
                           f"[{_idx}/{_total}] Section {_num:02d} 실패 — 다음으로 진행")

            if _idx < _total:
                import time as _time
                _time.sleep(1)

        update_job(job_id, "image_gen", "completed",
                   f"이미지 생성 완료: {_generated}/{_total}개 성공")

        # ===== Phase 6: Stitch =====
        update_job(job_id, "stitch", "running", "이미지를 합성하고 있습니다...")

        from scripts.stitch_images import stitch_all
        stitch_all(str(job_output_dir))

        update_job(job_id, "stitch", "completed", "최종 이미지 합성 완료")

        # Complete
        output_files = [
            f for f in os.listdir(str(job_output_dir))
            if f.endswith('.png') or f.endswith('.pdf')
        ]
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["output_files"] = sorted(output_files)
        update_job(job_id, "done", "completed", f"완료! {len(output_files)}개 파일 생성")

    except Exception as e:
        if _jobs and job_id in _jobs:
            _jobs[job_id]["status"] = "failed"
        update_job(job_id, "error", "failed", f"오류 발생: {str(e)}")

    finally:
        # Clean up temp files
        if TEMP_DIR.exists():
            for f in TEMP_DIR.glob("*.md"):
                try:
                    f.unlink()
                except OSError:
                    pass
