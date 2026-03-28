import os
import time
import subprocess

BASE_PATH = "/data"
JOBS_PATH = f"{BASE_PATH}/jobs"
RENDER_PATH = f"{BASE_PATH}/renders"

os.makedirs(RENDER_PATH, exist_ok=True)

def process_job(job_id):
    job_dir = f"{JOBS_PATH}/{job_id}"
    if not os.path.exists(f"{job_dir}/job.txt"):
        return

    with open(f"{job_dir}/job.txt") as f:
        filename = f.read().strip()

    blend_path = f"{job_dir}/{filename}"

    # --- Diagnostics ---
    size = os.path.getsize(blend_path)
    with open(blend_path, "rb") as f:
        magic = f.read(10)
    print(f"[DEBUG] File: {blend_path}")
    print(f"[DEBUG] Size: {size} bytes")
    print(f"[DEBUG] Magic bytes: {magic}")
    # -------------------

    if size == 0:
        print("[ERROR] File is empty — upload/mount issue")
        return

    output_path = f"{RENDER_PATH}/{job_id}_####"

    print(f"Rendering {blend_path}")

    subprocess.run([
        "blender",
        "-b", blend_path,
        "-o", output_path,
        "-a",
        "--",
        "--cycles-device", "CUDA"
    ])

    os.remove(f"{job_dir}/job.txt")

while True:
    jobs = os.listdir(JOBS_PATH)

    for job_id in jobs:
        process_job(job_id)

    time.sleep(5)
