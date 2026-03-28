from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
import uuid
import zipfile
import io

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
            <input name="file" type="file" accept=".blend"><br><br>
            <button type="submit">Upload & Render</button>
        </form>
    </body>
    </html>
    """

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
def job_page(job_id: str):
    return f"""
    <html>
    <head>
        <title>Rendering...</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: 80px auto; padding: 0 20px; background: #111; color: #eee; }}
            h1 {{ color: #ff6400; }}
            #bar-wrap {{ background: #333; border-radius: 8px; height: 28px; margin: 24px 0; overflow: hidden; }}
            #bar {{ height: 100%; width: 0%; background: #ff6400; transition: width 0.5s ease; border-radius: 8px; }}
            #status-text {{ color: #aaa; margin-bottom: 16px; }}
            #results {{ display: none; margin-top: 24px; }}
            #results h2 {{ color: #ff6400; }}
            .zip-btn {{ display: inline-block; margin-bottom: 20px; background: #ff6400; color: white;
                        padding: 10px 22px; border-radius: 4px; text-decoration: none; font-size: 15px; }}
            .zip-btn:hover {{ background: #e05500; }}
            .frame-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-top: 16px; }}
            .frame-card {{ background: #1e1e1e; border-radius: 6px; overflow: hidden; text-align: center; }}
            .frame-card img {{ width: 100%; display: block; background: #2a2a2a; min-height: 90px; }}
            .frame-card a {{ display: block; padding: 6px; color: #ff6400; text-decoration: none; font-size: 12px; }}
            .frame-card a:hover {{ text-decoration: underline; }}
            #back {{ display: inline-block; margin-top: 28px; color: #aaa; text-decoration: none; font-size: 14px; }}
            #back:hover {{ color: #fff; }}
        </style>
    </head>
    <body>
        <h1>🎬 Render Job</h1>
        <p style="color:#555; font-size:12px; margin-top:-12px;">ID: {job_id}</p>
        <div id="status-text">Waiting for render to start...</div>
        <div id="bar-wrap"><div id="bar"></div></div>

        <div id="results">
            <h2>✅ Render Complete</h2>
            <a class="zip-btn" id="zip-link" href="/download/{job_id}">⬇ Download All Frames (ZIP)</a>
            <div class="frame-grid" id="frame-grid"></div>
        </div>

        <a href="/" id="back">← Render another file</a>

        <script>
            const jobId = "{job_id}";
            let lastCount = 0;
            let totalFrames = 0;

            async function poll() {{
                let data;
                try {{
                    const res = await fetch(`/status/${{jobId}}`);
                    data = await res.json();
                }} catch(e) {{
                    setTimeout(poll, 3000);
                    return;
                }}

                const renders = data.renders;
                const count = renders.length;

                if (count > lastCount) {{
                    lastCount = count;
                    document.getElementById("status-text").textContent =
                        `Rendering... ${{count}} frame${{count !== 1 ? "s" : ""}} done so far`;
                    // progress bar pulses toward 90% until we know we're done
                    const pct = data.status === "done" ? 100 : Math.min(90, (count / Math.max(count + 5, 10)) * 100);
                    document.getElementById("bar").style.width = pct + "%";
                }}

                if (data.status === "done") {{
                    document.getElementById("bar").style.width = "100%";
                    document.getElementById("status-text").textContent =
                        `✅ Done — ${{count}} frame${{count !== 1 ? "s" : ""}} rendered`;
                    document.getElementById("results").style.display = "block";

                    const grid = document.getElementById("frame-grid");
                    grid.innerHTML = "";
                    for (const filename of renders) {{
                        const url = `/renders/${{filename}}`;
                        const frameNum = filename.replace(/.*_(\d+)\.png$/, "Frame $1");
                        const card = document.createElement("div");
                        card.className = "frame-card";
                        card.innerHTML = `
                            <a href="${{url}}" target="_blank">
                                <img src="${{url}}" loading="lazy" alt="${{frameNum}}">
                            </a>
                            <a href="${{url}}" download="${{filename}}">⬇ ${{frameNum}}</a>
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