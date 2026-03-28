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
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    
    print(f"[DEBUG] Filename: {file.filename}")
    print(f"[DEBUG] Content-Type: {file.content_type}")
    print(f"[DEBUG] Size: {len(contents)} bytes")
    print(f"[DEBUG] Magic bytes: {contents[:10]}")
    
    # Temporarily remove the magic check so we can inspect
    job_id = str(uuid.uuid4())
    job_dir = f"{JOBS_PATH}/{job_id}"
    os.makedirs(job_dir, exist_ok=True)
    file_path = f"{job_dir}/{file.filename}"

    if not (contents[:7] == b"BLENDER" or 
            contents[:2] == b"\x1f\x8b" or 
            contents[:4] == b"\x28\xb5\x2f\xfd"):
        shutil.rmtree(job_dir)
        return {"error": "Invalid .blend file"}

    with open(file_path, "wb") as f:
        f.write(contents)

    with open(f"{job_dir}/job.txt", "w") as f:
        f.write(file.filename)

    return {
        "message": "Job submitted",
        "job_id": job_id,
        "size": len(contents),
        "magic": str(contents[:10]),
    }