import os
import uuid
import json
import time
import zipfile
import threading
import io
from flask import Flask, request, jsonify, render_template, Response, send_file

app = Flask(__name__)

# In-memory job store
jobs = {}

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_job(job_id: str, product_info: dict) -> dict:
    return {
        "id": job_id,
        "status": "running",
        "phase": "intake",
        "progress": [],
        "product_info": product_info,
        "output_files": [],
    }


def _push_progress(job_id: str, phase: str, status: str, message: str):
    """Append a progress entry and update current phase."""
    job = jobs.get(job_id)
    if job is None:
        return
    job["phase"] = phase
    job["progress"].append(
        {
            "phase": phase,
            "status": status,
            "message": message,
            "timestamp": time.time(),
        }
    )


# ── pipeline runner ───────────────────────────────────────────────────────────

def _run_pipeline(job_id: str, product_info: dict, reference_image_path: str = None):
    """Background thread: delegate to orchestrator, fall back to stub."""
    try:
        try:
            import orchestrator  # type: ignore
            orchestrator.init_jobs(jobs)
            orchestrator.run_pipeline(job_id, product_info, reference_image_path)
        except ImportError:
            _stub_pipeline(job_id, product_info)
    except Exception as exc:
        jobs[job_id]["status"] = "failed"
        _push_progress(job_id, jobs[job_id]["phase"], "error", str(exc))


def _stub_pipeline(job_id: str, product_info: dict):
    """Minimal stub that simulates phase progression when orchestrator is absent."""
    phases = [
        ("intake",   "정보 수집 중…"),
        ("research", "시장 리서치 중…"),
        ("copy+design", "카피 및 디자인 생성 중…"),
        ("prompt",   "프롬프트 생성 중…"),
        ("image_gen","이미지 생성 중…"),
        ("stitch",   "이미지 합성 중…"),
    ]
    for phase, message in phases:
        _push_progress(job_id, phase, "running", message)
        time.sleep(1.5)
        _push_progress(job_id, phase, "completed", message + " 완료")

    # Create a dummy output file so the download endpoint has something
    output_dir = os.path.join("output", job_id)
    os.makedirs(output_dir, exist_ok=True)
    dummy_path = os.path.join(output_dir, "sample_01.png")
    if not os.path.exists(dummy_path):
        open(dummy_path, "wb").close()

    jobs[job_id]["output_files"] = [
        f for f in os.listdir(output_dir) if not f.startswith(".")
    ]
    jobs[job_id]["status"] = "completed"
    jobs[job_id]["phase"] = "done"
    _push_progress(job_id, "done", "completed", "파이프라인 완료")


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    # multipart/form-data 또는 JSON 모두 지원
    if request.content_type and 'multipart/form-data' in request.content_type:
        product_info = json.loads(request.form.get('product_info', '{}'))
        reference_image = request.files.get('reference_image')
    else:
        product_info = request.get_json(force=True) or {}
        reference_image = None

    job_id = str(uuid.uuid4())
    job_output_dir = os.path.join("output", job_id)
    os.makedirs(job_output_dir, exist_ok=True)

    # 참고 이미지 저장
    reference_image_path = None
    if reference_image:
        ext = os.path.splitext(reference_image.filename)[1] or '.png'
        reference_image_path = os.path.join(job_output_dir, f'reference_image{ext}')
        reference_image.save(reference_image_path)

    jobs[job_id] = _make_job(job_id, product_info)

    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, product_info, reference_image_path),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id: str):
    """Server-Sent Events stream for pipeline progress."""
    if job_id not in jobs:
        return jsonify({"error": "job not found"}), 404

    def event_stream():
        sent_idx = 0
        while True:
            job = jobs.get(job_id)
            if job is None:
                break

            # Send any unsent progress entries
            while sent_idx < len(job["progress"]):
                entry = job["progress"][sent_idx]
                payload = {
                    "phase":   entry["phase"],
                    "status":  entry["status"],
                    "message": entry["message"],
                    "files":   job["output_files"],
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                sent_idx += 1

            if job["status"] in ("completed", "failed"):
                # Send final "done" event
                done_payload = {
                    "phase":   "done",
                    "status":  job["status"],
                    "message": "완료" if job["status"] == "completed" else "실패",
                    "files":   job["output_files"],
                }
                yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
                yield "event: done\ndata: {}\n\n"
                break

            time.sleep(0.4)

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/regenerate/<job_id>/<int:section_num>", methods=["POST"])
def regenerate_section(job_id: str, section_num: int):
    """Regenerate a single section image and re-stitch."""
    import re

    output_dir = os.path.join("output", job_id)
    prompt_path = os.path.join(output_dir, "05-prompt.md")
    sections_dir = os.path.join(output_dir, "sections")

    if not os.path.isfile(prompt_path):
        return jsonify({"error": "프롬프트 파일(05-prompt.md)을 찾을 수 없습니다."}), 404

    # Section name/height maps (same as orchestrator.py)
    names = {
        1: "hero", 2: "pain", 3: "problem", 4: "story",
        5: "solution", 6: "how_it_works", 7: "social_proof",
        8: "authority", 9: "benefits", 10: "risk_removal",
        11: "comparison", 12: "target_filter", 13: "final_cta"
    }
    heights = {
        1: 800, 2: 600, 3: 500, 4: 700, 5: 400,
        6: 600, 7: 800, 8: 500, 9: 700, 10: 500,
        11: 400, 12: 400, 13: 600
    }

    if section_num not in names:
        return jsonify({"error": f"유효하지 않은 섹션 번호: {section_num}"}), 400

    # Parse the prompt for this section
    content = open(prompt_path, encoding="utf-8").read()
    sections = re.split(r'## Section (\d+)[:\s]', content)

    prompt_text = None
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections) and int(sections[i]) == section_num:
            raw = sections[i + 1].strip()
            raw = re.sub(r'^```\w*\n', '', raw)
            raw = re.sub(r'\n```$', '', raw)
            prompt_text = raw.strip()
            break

    if not prompt_text:
        return jsonify({"error": f"섹션 {section_num}의 프롬프트를 찾을 수 없습니다."}), 404

    # Delete existing image so it gets regenerated
    name = names[section_num]
    height = heights[section_num]
    filename = f"{section_num:02d}_{name}.png"
    out_path = os.path.join(sections_dir, filename)

    if os.path.exists(out_path):
        os.remove(out_path)

    # Generate
    try:
        from scripts.gemini_api import generate_image
        result = generate_image(prompt_text, out_path, 1200, height)
        if not result:
            return jsonify({"error": "이미지 생성에 실패했습니다. 잠시 후 다시 시도해주세요."}), 500
    except Exception as e:
        return jsonify({"error": f"이미지 생성 오류: {str(e)}"}), 500

    # Re-stitch
    try:
        from scripts.stitch_images import stitch_all
        stitch_all(output_dir)
    except Exception as e:
        return jsonify({"error": f"합성 오류: {str(e)}", "image_ok": True}), 500

    return jsonify({"success": True, "file": filename})


@app.route("/download/<job_id>/all")
def download_all(job_id: str):
    """Return a ZIP archive of all output images for the job."""
    # Path traversal 방지
    if ".." in job_id or "/" in job_id or "\\" in job_id:
        return jsonify({"error": "invalid job_id"}), 400

    output_dir = os.path.join("output", job_id)
    if not os.path.isdir(output_dir):
        return jsonify({"error": "output not found"}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add root files (final composites)
        for fname in sorted(os.listdir(output_dir)):
            fpath = os.path.join(output_dir, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, fname)
        # Add sections/ subfolder files
        sections_dir = os.path.join(output_dir, "sections")
        if os.path.isdir(sections_dir):
            for fname in sorted(os.listdir(sections_dir)):
                fpath = os.path.join(sections_dir, fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, os.path.join("sections", fname))
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"detail_page_{job_id[:8]}.zip",
    )


@app.route("/download/<job_id>/<filename>")
def download_file(job_id: str, filename: str):
    """Serve a single generated image (checks sections/ subfolder too)."""
    # Path traversal 방지: filename에 .. 또는 / 포함 차단
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "invalid filename"}), 400

    output_dir = os.path.join("output", job_id)
    file_path = os.path.join(output_dir, filename)

    # Check root first, then sections/ subfolder
    if not os.path.isfile(file_path):
        file_path = os.path.join(output_dir, "sections", filename)

    if not os.path.isfile(file_path):
        return jsonify({"error": "file not found"}), 404

    # 최종 경로가 output 디렉토리 내에 있는지 확인
    real_path = os.path.realpath(file_path)
    real_output = os.path.realpath("output")
    if not real_path.startswith(real_output):
        return jsonify({"error": "access denied"}), 403

    return send_file(file_path, as_attachment=False)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    app.run(
        debug=True,
        threaded=True,
        port=5000,
        use_reloader=False,
    )
