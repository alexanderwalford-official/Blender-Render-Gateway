# 🎬 Blender Render Gateway

A self-hosted GPU render farm in a box. Upload a `.blend` file, watch it render in real time, and download your frames as a ZIP — all from a browser.

Built with FastAPI, Docker, and NVIDIA CUDA. Runs Blender headlessly on your GPU.

[![Build Blender Render Containers](https://github.com/alexanderwalford-official/Blender-Render-Gateway/actions/workflows/docker-build.yml/badge.svg)](https://github.com/alexanderwalford-official/Blender-Render-Gateway/actions/workflows/docker-build.yml)

---

## ✨ Features

- **Browser-based upload** — drag in a `.blend` file and go
- **Live render progress** — polls frame-by-frame as Blender works
- **Frame gallery** — thumbnail preview of every rendered frame on completion
- **One-click ZIP download** — grab all frames in a single archive
- **GPU accelerated** — runs on NVIDIA CUDA via Docker
- **Format agnostic** — handles raw, gzip, and zstd-compressed blend files (Blender 2.x through 5.x)

---

## 🏗️ Architecture

```
┌─────────────────┐        /data (shared volume)       ┌──────────────────┐
│   blender-web   │ ──── writes job + .blend file ───► │  blender-worker  │
│   (FastAPI)     │ ◄─── reads rendered frames ──────  │  (Blender 5.1)   │
│   port 8000     │                                     │  CUDA GPU        │
└─────────────────┘                                     └──────────────────┘
```

- **`blender-web`** — FastAPI app that handles uploads, serves the UI, and exposes a status/download API
- **`blender-worker`** — Python process that polls for new jobs and invokes Blender headlessly
- **`/data`** — shared Docker volume for job queuing and render output

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/)
- NVIDIA GPU with drivers installed
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

### Run it

```bash
git clone https://github.com/AlexanderColen/Blender-Render-Gateway.git
cd Blender-Render-Gateway
docker compose up --build
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 📁 Project Structure

```
Blender-Render-Gateway/
├── docker-compose.yml
├── web/
│   ├── Dockerfile
│   ├── app.py               # FastAPI app
│   ├── requirements.txt
│   └── templates/
│       ├── index.html       # Upload page
│       └── rendering.html   # Live render status + results
└── worker/
    ├── Dockerfile
    ├── worker.py            # Job poller + Blender invoker
    └── requirements.txt
```

---

## 🔌 API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Upload page |
| `POST` | `/upload` | Submit a `.blend` file for rendering |
| `GET` | `/job/{job_id}` | Live render progress page |
| `GET` | `/status/{job_id}` | JSON status + list of rendered frames |
| `GET` | `/download/{job_id}` | Download all frames as a `.zip` |
| `GET` | `/renders/{filename}` | Direct access to a rendered frame |

### Status response

```json
{
  "status": "rendering",
  "renders": [
    "a1b2c3d4-..._0001.png",
    "a1b2c3d4-..._0002.png"
  ]
}
```

`status` is either `"rendering"` or `"done"`.

---

## ⚙️ Configuration

The worker renders using **EEVEE** by default (as configured in the `.blend` file). To force **Cycles** with CUDA, edit `worker/worker.py`:

```python
subprocess.run([
    "blender",
    "-b", blend_path,
    "-E", "CYCLES",
    "-o", output_path,
    "-a",
    "--",
    "--cycles-device", "CUDA"
])
```

---

## 🐳 Docker Details

Both containers share a `/data` volume:

- `/data/jobs/` — queued jobs (`.blend` file + `job.txt` marker)
- `/data/renders/` — output frames (`{job_id}_{frame}.png`)

The worker polls `/data/jobs/` every 5 seconds for new work and cleans up after itself when done.

---

## 🛠️ Development

To rebuild after code changes:

```bash
docker compose down --rmi all
docker compose build --no-cache
docker compose up
```

To inspect the worker live:

```bash
docker exec blender-worker ls -lh /data/renders/
docker logs blender-worker --follow
```

---

## 📄 License

[Apache](LICENSE)