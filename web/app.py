from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
import uuid
import zipfile
import io
from fastapi.templating import Jinja2Templates

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

    if not (contents[:7] == b"BLENDER" or
            contents[:2] == b"\x1f\x8b" or
            contents[:4] == b"\x28\xb5\x2f\xfd"):
        return {"error": "Invalid .blend file"}

    job_id = str(uuid.uuid4())
    job_dir = f"{JOBS_PATH}/{job_id}"
    os.makedirs(job_dir, exist_ok=True)
    with open(f"{job_dir}/{file.filename}", "wb") as f:
        f.write(contents)
    with open(f"{job_dir}/job.txt", "w") as f:
        f.write(file.filename)

    return RedirectResponse(url=f"/job/{job_id}", status_code=303)

@app.get("/status/{job_id}")
def status(job_id: str):
    job_dir = f"{JOBS_PATH}/{job_id}"
    renders = sorted([f for f in os.listdir(RENDER_PATH) if f.startswith(job_id)])
    pending = os.path.exists(f"{job_dir}/job.txt")
    return {
        "status": "rendering" if pending else "done",
        "renders": renders
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
    return RedirectResponse(url="/", status_code=303)