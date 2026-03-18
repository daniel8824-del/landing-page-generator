"""
landing-page-app — 상세페이지 자동 생성 웹앱
"""
import asyncio
import os
import re
import uuid
import zipfile
import io
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Request, Form, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.writer import (
    write_intake, write_research, write_copy,
    write_design, write_prompts,
)
from app.research import analyze_market
from app.file_parser import extract_reviews

app = FastAPI(title="Landing Page Generator", version="1.0")

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

jobs: dict = {}

WORKSPACE = os.environ.get("WORKSPACE", "/mnt/c/Users/daniel/Desktop/상세페이지/workspace")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/start")
async def start_generation(
    background_tasks: BackgroundTasks,
    product_name: str = Form(...),
    features: str = Form(""),
    target_customer: str = Form(""),
    category: str = Form(""),
    original_price: str = Form(""),
    sale_price: str = Form(""),
    style_preset: str = Form("Minimal"),
    extra_info: str = Form(""),
    reference_images: list[UploadFile] = File([]),
    review_files: list[UploadFile] = File([]),
):
    """상세페이지 생성 시작"""
    job_id = str(uuid.uuid4())[:8]
    # 제품명 기반 폴더 (bizplan 패턴)
    safe_name = "".join(c for c in product_name if c.isalnum() or c in "_ -").strip().replace(" ", "_")[:30]
    project_dir = os.path.join(WORKSPACE, f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M')}")
    os.makedirs(os.path.join(project_dir, "sections"), exist_ok=True)

    # 참고 이미지 저장 (다중)
    ref_image_path = None
    for idx, ref_img in enumerate(reference_images):
        if ref_img and ref_img.filename:
            ext = os.path.splitext(ref_img.filename)[1] or ".png"
            path = os.path.join(project_dir, f"reference_image_{idx+1}{ext}")
            with open(path, "wb") as f:
                content = await ref_img.read()
                f.write(content)
            if ref_image_path is None:
                ref_image_path = path  # 첫 번째 이미지를 스타일 분석용으로 사용

    # 리뷰 데이터 저장 및 파싱 (다중)
    review_text = ""
    for idx, rev_file in enumerate(review_files):
        if rev_file and rev_file.filename:
            ext = os.path.splitext(rev_file.filename)[1] or ".csv"
            review_path = os.path.join(project_dir, f"reviews_{idx+1}{ext}")
            with open(review_path, "wb") as f:
                content = await rev_file.read()
                f.write(content)
            text = extract_reviews(review_path)
            if text:
                review_text += f"\n\n--- {rev_file.filename} ---\n{text}"
    if review_text:
        with open(os.path.join(project_dir, "00-reviews.md"), "w", encoding="utf-8") as f:
            f.write(review_text)

    product_info = {
        "product_name": product_name,
        "features": [f.strip() for f in features.split(",") if f.strip()],
        "target_customer": target_customer,
        "category": category,
        "original_price": original_price,
        "sale_price": sale_price,
        "style_preset": style_preset,
        "extra_info": extra_info,
        "review_text": review_text,
    }

    jobs[job_id] = {
        "status": "started",
        "phase": "Phase 1: 정보 수집",
        "progress": 0,
        "project_dir": project_dir,
        "results": {},
    }

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return JSONResponse({"error": "OPENROUTER_API_KEY가 설정되지 않았습니다."}, status_code=400)

    background_tasks.add_task(
        run_pipeline, job_id, product_info, api_key, ref_image_path
    )

    return {"job_id": job_id, "status": "started"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """진행 상태 조회"""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return {
        "status": job["status"],
        "phase": job["phase"],
        "progress": job["progress"],
        "results": job.get("results", {}),
    }


@app.get("/api/download/{job_id}/all")
async def download_all(job_id: str):
    """전체 결과 ZIP 다운로드"""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    project_dir = job["project_dir"]
    if not os.path.isdir(project_dir):
        return JSONResponse({"error": "Output not found"}, status_code=404)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(project_dir)):
            fpath = os.path.join(project_dir, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, fname)
        sections_dir = os.path.join(project_dir, "sections")
        if os.path.isdir(sections_dir):
            for fname in sorted(os.listdir(sections_dir)):
                fpath = os.path.join(sections_dir, fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, os.path.join("sections", fname))
    buf.seek(0)

    from starlette.responses import StreamingResponse
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=detail_page_{job_id}.zip"},
    )


@app.get("/api/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    """개별 파일 다운로드"""
    if ".." in filename or "/" in filename or "\\" in filename:
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    project_dir = job["project_dir"]
    file_path = os.path.join(project_dir, filename)
    if not os.path.isfile(file_path):
        file_path = os.path.join(project_dir, "sections", filename)
    if not os.path.isfile(file_path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    real_path = os.path.realpath(file_path)
    real_project = os.path.realpath(project_dir)
    if not real_path.startswith(real_project):
        return JSONResponse({"error": "Access denied"}, status_code=403)

    return FileResponse(file_path)


@app.get("/api/files/{job_id}")
async def list_files(job_id: str):
    """프로젝트 디렉토리의 모든 파일 목록"""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    project_dir = job["project_dir"]
    if not os.path.isdir(project_dir):
        return JSONResponse({"error": "Directory not found"}, status_code=404)

    files = []
    for fname in sorted(os.listdir(project_dir)):
        fpath = os.path.join(project_dir, fname)
        if os.path.isfile(fpath) and not fname.startswith('.'):
            size = os.path.getsize(fpath)
            files.append({"name": fname, "size": size})

    # sections/ subdirectory
    sections_dir = os.path.join(project_dir, "sections")
    if os.path.isdir(sections_dir):
        for fname in sorted(os.listdir(sections_dir)):
            fpath = os.path.join(sections_dir, fname)
            if os.path.isfile(fpath):
                files.append({"name": f"sections/{fname}", "size": os.path.getsize(fpath)})

    return {"files": files}


@app.post("/api/regenerate/{job_id}/{section_num}")
async def regenerate_section(job_id: str, section_num: int):
    """개별 섹션 재생성"""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    project_dir = job["project_dir"]
    prompt_path = os.path.join(project_dir, "05-prompt.md")
    sections_dir = os.path.join(project_dir, "sections")

    if not os.path.isfile(prompt_path):
        return JSONResponse({"error": "프롬프트 파일 없음"}, status_code=404)

    names = {
        1: "hero", 2: "pain", 3: "problem", 4: "story",
        5: "solution", 6: "how_it_works", 7: "social_proof",
        8: "authority", 9: "benefits", 10: "risk_removal",
        11: "comparison", 12: "target_filter", 13: "final_cta",
    }
    heights = {
        1: 800, 2: 600, 3: 500, 4: 700, 5: 400,
        6: 600, 7: 800, 8: 500, 9: 700, 10: 500,
        11: 400, 12: 400, 13: 600,
    }

    if section_num not in names:
        return JSONResponse({"error": f"유효하지 않은 섹션: {section_num}"}, status_code=400)

    content = open(prompt_path, encoding="utf-8").read()
    sections = re.split(r"## Section (\d+)[:\s]", content)
    prompt_text = None
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections) and int(sections[i]) == section_num:
            raw = sections[i + 1].strip()
            raw = re.sub(r"^```\w*\n", "", raw)
            raw = re.sub(r"\n```$", "", raw)
            prompt_text = raw.strip()
            break

    if not prompt_text:
        return JSONResponse({"error": f"섹션 {section_num} 프롬프트 없음"}, status_code=404)

    name = names[section_num]
    height = heights[section_num]
    filename = f"{section_num:02d}_{name}.png"
    out_path = os.path.join(sections_dir, filename)

    try:
        from scripts.gemini_api import generate_image
        result = generate_image(prompt_text, out_path, 1200, height)
        if not result:
            return JSONResponse({"error": "이미지 생성 실패"}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    try:
        from scripts.stitch_images import stitch_all
        stitch_all(project_dir)
    except Exception as e:
        return JSONResponse({"error": f"합성 오류: {e}", "image_ok": True}, status_code=500)

    return {"success": True, "file": filename}


# ── Pipeline ──

async def run_pipeline(job_id: str, product_info: dict,
                       api_key: str, ref_image_path: str = None):
    """전체 파이프라인 실행"""
    job = jobs[job_id]
    project_dir = job["project_dir"]

    try:
        # Phase 1: 정보 수집
        job["phase"] = "Phase 1: 제품 정보 분석"
        job["progress"] = 5

        # 참고 이미지 분석 (선택)
        style_reference = ""
        if ref_image_path and os.path.exists(ref_image_path):
            try:
                from scripts.gemini_api import analyze_image_style
                style_ref_path = os.path.join(project_dir, "00-style-reference.md")
                analyze_image_style(ref_image_path, style_ref_path)
                if os.path.exists(style_ref_path):
                    style_reference = open(style_ref_path, encoding="utf-8").read()
            except Exception as e:
                print(f"[WARN] Style analysis failed: {e}")

        intake = await write_intake(product_info, api_key=api_key)
        _save(project_dir, "01-intake.md", intake)
        job["results"]["intake"] = "완료"
        job["progress"] = 15

        # Phase 1.5: 네이버 시장 리서치 (선택)
        job["phase"] = "Phase 1.5: 시장 리서치"
        job["progress"] = 18
        market_data = ""
        try:
            market_path = await analyze_market(
                product_info.get("product_name", ""),
                product_info.get("category", ""),
                project_dir,
            )
            if market_path and os.path.exists(market_path):
                market_data = open(market_path, encoding="utf-8").read()
                job["results"]["market"] = "완료"
        except Exception as e:
            print(f"[WARN] Naver research skipped: {e}")
            job["results"]["market"] = "스킵 (API 키 없음)"

        # Phase 2: 리서치 분석
        job["phase"] = "Phase 2: 리서치 분석"
        job["progress"] = 25
        review_context = product_info.get("review_text", "")
        research = await write_research(intake, market_data, review_context=review_context, api_key=api_key)
        _save(project_dir, "02-research.md", research)
        job["results"]["research"] = "완료"
        job["progress"] = 35

        # Phase 3: 카피 + 디자인 (병렬)
        job["phase"] = "Phase 3: 카피 + 디자인 (병렬)"
        job["progress"] = 40

        copy_result, design_result = await asyncio.gather(
            write_copy(intake, research, review_context=review_context, api_key=api_key),
            write_design(
                intake, research,
                style_preset=product_info.get("style_preset", "Minimal"),
                style_reference=style_reference,
                api_key=api_key,
            ),
        )

        _save(project_dir, "03-copy.md", copy_result)
        _save(project_dir, "04-design.md", design_result)
        job["results"]["copy"] = "완료"
        job["results"]["design"] = "완료"
        job["progress"] = 55

        # Phase 4: 프롬프트 생성
        job["phase"] = "Phase 4: Gemini 프롬프트 생성"
        job["progress"] = 60
        prompts = await write_prompts(copy_result, design_result, api_key=api_key)
        _save(project_dir, "05-prompt.md", prompts)
        job["results"]["prompts"] = "완료"
        job["progress"] = 65

        # Phase 5: 이미지 생성 (sync, in thread)
        job["phase"] = "Phase 5: Gemini 이미지 생성"
        job["progress"] = 68

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, _generate_images, job_id, project_dir
        )
        job["progress"] = 90

        # Phase 6: 합성
        job["phase"] = "Phase 6: 이미지 합성"
        job["progress"] = 92

        from scripts.stitch_images import stitch_all
        stitch_all(project_dir)

        job["results"]["stitch"] = "완료"
        job["status"] = "completed"
        job["phase"] = "완료"
        job["progress"] = 100

    except Exception as e:
        job["status"] = "error"
        job["phase"] = f"에러: {str(e)[:200]}"
        print(f"[ERROR] Pipeline failed: {e}")


def _generate_images(job_id: str, project_dir: str):
    """Gemini 이미지 생성 (sync — run_in_executor에서 호출)"""
    from scripts.gemini_api import generate_image
    import time

    prompt_path = os.path.join(project_dir, "05-prompt.md")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError("05-prompt.md not found")

    sections_dir = os.path.join(project_dir, "sections")
    os.makedirs(sections_dir, exist_ok=True)

    content = open(prompt_path, encoding="utf-8").read()
    section_splits = re.split(r"## Section (\d+)[:\s]", content)

    heights = {
        1: 800, 2: 600, 3: 500, 4: 700, 5: 400,
        6: 600, 7: 800, 8: 500, 9: 700, 10: 500,
        11: 400, 12: 400, 13: 600,
    }
    names = {
        1: "hero", 2: "pain", 3: "problem", 4: "story",
        5: "solution", 6: "how_it_works", 7: "social_proof",
        8: "authority", 9: "benefits", 10: "risk_removal",
        11: "comparison", 12: "target_filter", 13: "final_cta",
    }

    prompts = []
    for i in range(1, len(section_splits), 2):
        if i + 1 < len(section_splits):
            num = int(section_splits[i])
            raw = section_splits[i + 1].strip()
            raw = re.sub(r"^```\w*\n", "", raw)
            raw = re.sub(r"\n```$", "", raw)
            prompts.append({"num": num, "prompt": raw.strip()})

    job = jobs.get(job_id)
    total = len(prompts)
    generated = 0

    for idx, sec in enumerate(prompts, 1):
        num = sec["num"]
        name = names.get(num, f"section_{num}")
        height = heights.get(num, 600)
        filename = f"{num:02d}_{name}.png"
        out_path = os.path.join(sections_dir, filename)

        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            generated += 1
            continue

        if job:
            job["phase"] = f"Phase 5: 이미지 생성 [{idx}/{total}] {name}"

        result = generate_image(sec["prompt"], out_path, 1200, height)
        if result:
            generated += 1

        if idx < total:
            time.sleep(1)

    if job:
        job["results"]["images"] = f"{generated}/{total}개 생성"


def _save(project_dir: str, filename: str, content: str):
    path = os.path.join(project_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
