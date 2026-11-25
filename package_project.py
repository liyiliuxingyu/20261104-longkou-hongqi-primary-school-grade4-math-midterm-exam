#!/usr/bin/env python3
"""Refresh checksums and create a continuation archive; no caches or credentials."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
DIRS = ["src", "outputs", "originals", "reference", "docs", "vendor"]
FILES = ["README.md", ".gitignore", ".gitattributes", "README_先读我.txt", "新对话接续指令.txt", "AGENTS.md", "build.py", "build.sh", "build.cmd", "verify.py", "package_project.py", "requirements.txt"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="../四年级数学阶段测试_续作工程包.zip")
    args = parser.parse_args()
    paths = []
    for name in FILES:
        file = ROOT / name
        if not file.is_file():
            raise SystemExit("缺少必要文件：" + name)
        paths.append(file)
    for name in DIRS:
        directory = ROOT / name
        if not directory.is_dir():
            raise SystemExit("缺少目录：" + name)
        for file in directory.rglob("*"):
            if file.is_symlink():
                raise SystemExit("包内不接受外部软链接：" + str(file))
            if file.is_file() and "__pycache__" not in file.parts:
                paths.append(file)
    paths = sorted(set(paths), key=lambda p: p.relative_to(ROOT).as_posix())
    records = [{"path": p.relative_to(ROOT).as_posix(), "size": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
    manifest = ROOT / "manifest_sha256.json"
    manifest.write_text(json.dumps({"format": 1, "files": records},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target = Path(args.output)
    if not target.is_absolute():
        target = ROOT / target
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in paths + [manifest]:
            archive.write(file, "math_exam_project/" + file.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:
        corrupt = archive.testzip()
        if corrupt:
            raise SystemExit("ZIP CRC检查失败：" + corrupt)
    print(json.dumps({"archive": str(target), "files": len(paths) + 1,
                      "size_bytes": target.stat().st_size,
                      "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                      "zip_crc": "passed"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
