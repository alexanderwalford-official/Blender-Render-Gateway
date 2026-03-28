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
