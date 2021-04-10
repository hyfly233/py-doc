import hashlib


def calculate_md5_file(file_path: str) -> str:
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hashlib.md5().update(chunk)
    return hashlib.md5().hexdigest()
