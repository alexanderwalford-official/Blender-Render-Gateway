import os
import time
import subprocess
import zstandard as zstd
import shutil
import json


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


def get_frame_range(blend_path):
    """Ask Blender to print the frame range without rendering."""
    result = subprocess.run([
        "blender",
        "-b", blend_path,
        "--python-expr",
        "import bpy, json; s=bpy.context.scene; print('FRAMERANGE:' + json.dumps({'start': s.frame_start, 'end': s.frame_end}))"
    ], capture_output=True, text=True)
    
    for line in result.stdout.splitlines():
        if line.startswith("FRAMERANGE:"):
            return json.loads(line[len("FRAMERANGE:"):])
    
    return None

def process_job(job_id):
    job_dir = f"{JOBS_PATH}/{job_id}"
    if not os.path.exists(f"{job_dir}/job.txt"):
        return

    with open(f"{job_dir}/job.txt") as f:
        filename = f.read().strip()

    blend_path = f"{job_dir}/{filename}"

    if not os.path.exists(blend_path):
        print(f"[ERROR] Blend file not found: {blend_path}")
        return

    decompress_if_needed(blend_path)

    # Remap paths
    subprocess.run([
        "blender", "-b", blend_path,
        "-P", "/app/remap_paths.py",
        "--", job_dir
    ])

    # Get frame range and write to meta.json
    frame_range = get_frame_range(blend_path)
    if frame_range:
        print(f"[INFO] Frame range: {frame_range['start']} - {frame_range['end']}")
        with open(f"{job_dir}/meta.json", "w") as f:
            json.dump(frame_range, f)

    output_path = f"{RENDER_PATH}/{job_id}_####"
    subprocess.run([
        "blender", "-b", blend_path,
        "-o", output_path,
        "-a",
        "--", "--cycles-device", "CUDA"
    ])

    shutil.rmtree(job_dir)

while True:
    jobs = os.listdir(JOBS_PATH)

    for job_id in jobs:
        process_job(job_id)

    time.sleep(5)
