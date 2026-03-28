from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
import uuid

app = FastAPI()

BASE_PATH = "/data"
JOBS_PATH = f"{BASE_PATH}/jobs"
RENDER_PATH = f"{BASE_PATH}/renders"

os.makedirs(JOBS_PATH, exist_ok=True)
os.makedirs(RENDER_PATH, exist_ok=True)

# Serve rendered files
app.mount("/renders", StaticFiles(directory=RENDER_PATH), name="renders")


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Blender Render Server</title>
        </head>
        <body>
            <h1>Upload Blender File</h1>
            <form action="/upload" enctype="multipart/form-data" method="post">
                <input name="file" type="file" accept=".blend">
                <button type="submit">Upload & Render</button>
            </form>
        </body>
    </html>
    """


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = f"{JOBS_PATH}/{job_id}"
    os.makedirs(job_dir, exist_ok=True)

    file_path = f"{job_dir}/{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # mark job
    with open(f"{job_dir}/job.txt", "w") as f:
        f.write(file.filename)

    return {
        "message": "Job submitted",
        "job_id": job_id,
        "check_renders": f"/renders/"
    }
