from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.responses import 
import zipfile
import io
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

app.mount("/renders", StaticFiles(directory=RENDER_PATH), name="renders")

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head>
        <title>Blender Render Server</title>
        <style>
            body { font-family: sans-serif; max-width: 600px; margin: 80px auto; padding: 0 20px; background: #111; color: #eee; }
            h1 { color: #ff6400; }
            input[type=file] { margin: 20px 0; }
            button { background: #ff6400; color: white; border: none; padding: 10px 24px; font-size: 16px; cursor: pointer; border-radius: 4px; }
            button:hover { background: #e05500; }
        </style>
    </head>
    <body>
        <h1>🎬 Blender Render Server</h1>
        <form action="/upload" enctype="multipart/form-data" method="post">
            <input name="file" type="file" accept=".blend"><br>
            <button type="submit">Upload & Render</button>
        </form>
    </body>
    </html>
    """

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()

    BLEND_MAGIC = b"BLENDER"
    GZIP_MAGIC = b"\x1f\x8b"
    ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
    if not (contents[:7] == BLEND_MAGIC or
            contents[:2] == GZIP_MAGIC or
            contents[:4] == ZSTD_MAGIC):
        return {"error": "Invalid .blend file"}

    job_id = str(uuid.uuid4())
    job_dir = f"{JOBS_PATH}/{job_id}"
    os.makedirs(job_dir, exist_ok=True)
    file_path = f"{job_dir}/{file.filename}"
    with open(file_path, "wb") as f:
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

@app.get("/job/{job_id}", response_class=HTMLResponse)
def job_page(job_id: str):
    return f"""
    <html>
    <head>
        <title>Rendering...</title>
        <style>
            body {{ font-family: sans-serif; max-width: 700px; margin: 80px auto; padding: 0 20px; background: #111; color: #eee; }}
            h1 {{ color: #ff6400; }}
            #bar-wrap {{ background: #333; border-radius: 8px; height: 28px; margin: 24px 0; overflow: hidden; }}
            #bar {{ height: 100%; width: 0%; background: #ff6400; transition: width 0.4s ease; border-radius: 8px; }}
            #status-text {{ color: #aaa; margin-bottom: 16px; }}
            #results {{ display: none; }}
            #results h2 {{ color: #ff6400; }}
            .frame-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-top: 16px; }}
            .frame-card {{ background: #1e1e1e; border-radius: 6px; overflow: hidden; text-align: center; }}
            .frame-card img {{ width: 100%; display: block; }}
            .frame-card a {{ display: block; padding: 6px; color: #ff6400; text-decoration: none; font-size: 13px; }}
            .frame-card a:hover {{ text-decoration: underline; }}
            #back {{ display: inline-block; margin-top: 24px; color: #ff6400; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>🎬 Rendering Job</h1>
        <p style="color:#666; font-size:13px;">Job ID: {job_id}</p>
        <div id="status-text">Starting render...</div>
        <div id="bar-wrap"><div id="bar"></div></div>
        <div id="results">
            <h2>✅ Render Complete</h2>
            <div class="frame-grid" id="frame-grid"></div>
        </div>
        <a href="/" id="back">← Render another file</a>

        <script>
            const jobId = "{job_id}";
            let known = 0;
            let done = false;

            async function poll() {{
                const res = await fetch(`/status/${{jobId}}`);
                const data = await res.json();

                const renders = data.renders;
                const total = renders.length;

                if (total > known) {{
                    known = total;
                    const bar = document.getElementById("bar");
                    // animate bar — we don't know total frames so pulse when rendering
                    bar.style.width = done ? "100%" : Math.min(95, total * 2) + "%";
                    document.getElementById("status-text").textContent =
                        `Rendering... ${{total}} frame${{total !== 1 ? "s" : ""}} saved so far`;
                }}

                if (data.status === "done") {{
                    done = true;
                    document.getElementById("bar").style.width = "100%";
                    document.getElementById("status-text").textContent = `Done! ${{total}} frame${{total !== 1 ? "s" : ""}} rendered.`;
                    document.getElementById("results").style.display = "block";

                    const grid = document.getElementById("frame-grid");
                    grid.innerHTML = "";
                    for (const f of renders) {{
                        const url = `/renders/${{f}}`;
                        const card = document.createElement("div");
                        card.className = "frame-card";
                        card.innerHTML = `
                            <img src="${{url}}" loading="lazy">
                            <a href="${{url}}" download="${{f}}">⬇ ${{f}}</a>
                        `;
                        grid.appendChild(card);
                    }}
                    return;
                }}

                setTimeout(poll, 2000);
            }}

            poll();
        </script>
    </body>
    </html>
    """

@app.get("/download/{job_id}")
def download_zip(job_id: str):
    renders = sorted([f for f in os.listdir(RENDER_PATH) if f.startswith(job_id)])
    if not renders:
        return {"error": "No renders found for this job"}

    def generate_zip():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename in renders:
                filepath = f"{RENDER_PATH}/{filename}"
                zf.write(filepath, arcname=filename)
        buf.seek(0)
        yield buf.read()

    return StreamingResponse(
        generate_zip(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=render_{job_id[:8]}.zip"}
    )