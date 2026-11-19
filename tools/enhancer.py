import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".md", ".txt"}

def enhance_digital_asset(file_path):
    path = Path(file_path)

    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        return False

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(f"[ERROR] Unsupported file type: {path.suffix}")
        return False

    print(f"[INFO] Inspecting asset: {path}")

    # utf-8-sig strips a leading BOM instead of keeping it as U+FEFF. Windows
    # editors write BOMs; concatenating one after the header put a non-printable
    # character in the middle of the generated .py and Python refused to import
    # it (CI's compileall caught exactly that, 2026-11-19). lstrip is the guard
    # for a BOM that survived decoding for any other reason.
    content = path.read_text(encoding="utf-8-sig").lstrip("\ufeff")

    header = (
        "# ==========================================\n"
        "# GALAXY FORGE — ASSET ENHANCER\n"
        "# Generated enhancement copy — REVIEW REQUIRED\n"
        "# ==========================================\n\n"
    )

    output_path = path.with_name(
        f"{path.stem}_enhanced{path.suffix}"
    )

    if output_path.exists():
        print(f"[ERROR] Output already exists: {output_path}")
        return False

    output_path.write_text(
        header + content,
        encoding="utf-8"
    )

    print(f"[SUCCESS] Enhanced copy created: {output_path}")
    print("[STATUS] Review required before production use.")
    return True


if __name__ == "__main__":
    print("Galaxy Forge Asset Enhancer")
    print("SAFE LOCAL MODE — no publishing, no git operations.")
