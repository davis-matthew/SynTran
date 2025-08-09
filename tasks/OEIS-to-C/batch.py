import os
import shutil

def split_folder(source_dir, batch_size=10000, prefix="batch"):
    with os.scandir(source_dir) as entries:
        files = [entry for entry in entries if entry.is_file()]

    total_files = len(files)
    print(f"Found {total_files} files in '{source_dir}'")

    for i in range(0, total_files, batch_size):
        batch = files[i:i + batch_size]
        batch_folder = os.path.join(source_dir, f"{prefix}_{i // batch_size + 1}")
        os.makedirs(batch_folder, exist_ok=True)

        for entry in batch:
            dst = os.path.join(batch_folder, entry.name)
            shutil.move(entry.path, dst)

        print(f"Moved {len(batch)} files to '{batch_folder}'")

# Example usage
split_folder("/storage/home/hcoda1/7/mdavis438/GANESH-SHARED/OEIS")