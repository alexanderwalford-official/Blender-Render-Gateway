import os
import time
import subprocess
import zstandard as zstd
import shutil

BASE_PATH = "/data"
JOBS_PATH = f"{BASE_PATH}/jobs"
RENDER_PATH = f"{BASE_PATH}/renders"

os.makedirs(RENDER_PATH, exist_ok=True)

# On startup, clean up any jobs left over from a previous run
print("[INFO] Cleaning up orphaned jobs from previous run...")
for job_id in os.listdir(JOBS_PATH):
    job_dir = f"{JOBS_PATH}/{job_id}"
    shutil.rmtree(job_dir, ignore_errors=True)
    print(f"[INFO] Removed orphaned job: {job_id}")

def decompress_if_needed(blend_path):
    with open(blend_path, "rb") as f:
        magic = f.read(4)
    
    if magic[:2] == b'\x1f\x8b':
        import gzip
        print("[INFO] Decompressing gzip blend")
        tmp = blend_path + ".tmp"
        with gzip.open(blend_path, "rb") as f_in, open(tmp, "wb") as f_out:
            f_out.write(f_in.read())
        os.replace(tmp, blend_path)

    elif magic[:4] == b'\x28\xb5\x2f\xfd':
        print("[INFO] Decompressing zstd blend")
        tmp = blend_path + ".tmp"
        dctx = zstd.ZstdDecompressor()
        with open(blend_path, "rb") as f_in, open(tmp, "wb") as f_out:
            dctx.copy_stream(f_in, f_out)
        os.replace(tmp, blend_path)

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

    decompress_if_needed(blend_path)

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
