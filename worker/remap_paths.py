import bpy
import sys
import os

job_dir = sys.argv[sys.argv.index("--") + 1]
print(f"[REMAP] Remapping paths to: {job_dir}")

for image in bpy.data.images:
    if image.filepath:
        filename = os.path.basename(bpy.path.abspath(image.filepath))
        new_path = os.path.join(job_dir, filename)
        if os.path.exists(new_path):
            print(f"[REMAP] Image: {image.filepath} -> {new_path}")
            image.filepath = new_path
        else:
            print(f"[REMAP] WARNING: Asset not found: {filename}")

for sound in bpy.data.sounds:
    if sound.filepath:
        filename = os.path.basename(bpy.path.abspath(sound.filepath))
        new_path = os.path.join(job_dir, filename)
        if os.path.exists(new_path):
            print(f"[REMAP] Sound: {sound.filepath} -> {new_path}")
            sound.filepath = new_path

for movie in bpy.data.movieclips:
    if movie.filepath:
        filename = os.path.basename(bpy.path.abspath(movie.filepath))
        new_path = os.path.join(job_dir, filename)
        if os.path.exists(new_path):
            print(f"[REMAP] Clip: {movie.filepath} -> {new_path}")
            movie.filepath = new_path

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("[REMAP] Saved remapped blend file")