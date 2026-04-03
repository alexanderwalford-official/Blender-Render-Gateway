from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
import uuid
import zipfile
import io
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()
BASE_PATH = "/data"
JOBS_PATH = f"{BASE_PATH}/jobs"
RENDER_PATH = f"{BASE_PATH}/renders"
os.makedirs(JOBS_PATH, exist_ok=True)
os.makedirs(RENDER_PATH, exist_ok=True)

app.mount("/renders", StaticFiles(directory=RENDER_PATH), name="renders")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()

    is_zip = contents[:2] == b'PK'
    is_blend = (contents[:7] == b"BLENDER" or
                contents[:2] == b"\x1f\x8b" or
                contents[:4] == b"\x28\xb5\x2f\xfd")

    if not (is_zip or is_blend):
        return {"error": "Upload must be a .blend or .zip file"}

    job_id = str(uuid.uuid4())
    job_dir = f"{JOBS_PATH}/{job_id}"
    os.makedirs(job_dir, exist_ok=True)

    if is_zip:
        zip_path = f"{job_dir}/upload.zip"
        with open(zip_path, "wb") as f:
            f.write(contents)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(job_dir)
        os.remove(zip_path)

        # Find the .blend file inside the ZIP
        blend_file = None
        for root, dirs, files in os.walk(job_dir):
            for f in files:
                if f.endswith(".blend"):
                    blend_file = f
                    # Move to job root if it's in a subfolder
                    src = os.path.join(root, f)
                    dst = f"{job_dir}/{f}"
                    if src != dst:
                        shutil.move(src, dst)
                    break
            if blend_file:
                break

        if not blend_file:
            shutil.rmtree(job_dir)
            return {"error": "No .blend file found in ZIP"}

        filename = blend_file
    else:
        filename = file.filename
        with open(f"{job_dir}/{filename}", "wb") as f:
            f.write(contents)

    with open(f"{job_dir}/job.txt", "w") as f:
        f.write(filename)

    return RedirectResponse(url=f"/job/{job_id}", status_code=303)

@app.get("/status/{job_id}")
def status(job_id: str):
    job_dir = f"{JOBS_PATH}/{job_id}"
    renders = sorted([f for f in os.listdir(RENDER_PATH) if f.startswith(job_id)])
    pending = os.path.exists(f"{job_dir}/job.txt")

    frame_range = None
    meta_path = f"{job_dir}/meta.json"
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            frame_range = json.load(f)

    return {
        "status": "rendering" if pending else "done",
        "renders": renders,
        "frame_range": frame_range
    }

@app.get("/download/{job_id}")
def download_zip(job_id: str):
    renders = sorted([f for f in os.listdir(RENDER_PATH) if f.startswith(job_id)])
    if not renders:
        return {"error": "No renders found for this job"}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in renders:
            zf.write(f"{RENDER_PATH}/{filename}", arcname=filename)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.read()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=render_{job_id[:8]}.zip"}
    )

@app.get("/job/{job_id}", response_class=HTMLResponse)
def job_page(request: Request, job_id: str):
    return templates.TemplateResponse(request, "rendering.html", {"job_id": job_id})

@app.get("/delete-all")
def delete_all():    
    for job_id in os.listdir(JOBS_PATH):
        shutil.rmtree(f"{JOBS_PATH}/{job_id}", ignore_errors=True)
    
    for filename in os.listdir(RENDER_PATH):
        os.remove(f"{RENDER_PATH}/{filename}")
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/jobs")
def list_jobs():
    seen = set()
    jobs = []
    for filename in os.listdir(RENDER_PATH):
        if filename.endswith(".png"):
            job_id = filename.rsplit("_", 1)[0]
            if job_id not in seen:
                seen.add(job_id)
                frames = sorted([f for f in os.listdir(RENDER_PATH) if f.startswith(job_id)])
                jobs.append({
                    "job_id": job_id,
                    "frames": len(frames),
                    "preview": frames[0] if frames else None
                })
    return sorted(jobs, key=lambda x: x["job_id"], reverse=True)