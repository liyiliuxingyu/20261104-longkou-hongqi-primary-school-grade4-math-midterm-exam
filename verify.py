#!/usr/bin/env python3
"""Offline integrity, source, and PDF checks for this exam handoff project.

Python 3.9+ is sufficient for manifest and source checks. PyMuPDF is optional
unless --require-pdf or --compare-pdf-dir is requested. No packages are installed
and no network requests are made. A PDF byte mismatch is reported separately
from extracted-text and rendered-pixel mismatches.

Exit codes: 0 = available/requested checks passed (inspect explicit skips);
1 = an integrity or content check failed; 2 = a required capability or report
write failed, or command-line arguments were invalid.
"""

import argparse
import hashlib
import importlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


DOCUMENTS = (
    ("questions", "四年级数学阶段测试_LaTeX试卷版", "\\answersfalse"),
    ("answers", "四年级数学阶段测试_LaTeX答案版", "\\answerstrue"),
)
PLACEHOLDER = "% ANSWER_SWITCH"
PAGE_SIZE_MM = (420.0, 297.0)
SIZE_TOLERANCE_MM = 0.05


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def new_report(root):
    return {
        "format": 1,
        "tool": "verify.py",
        "started_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(root),
        "checks": [],
        "errors": [],
        "environment_errors": [],
        "warnings": [],
        "skipped_checks": [],
    }


def record(report, name, passed, details=None):
    item = {"name": name, "passed": bool(passed)}
    if details is not None:
        item["details"] = details
    report["checks"].append(item)
    if not passed:
        report["errors"].append(item)
    return passed


def is_within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def safe_manifest_path(root, name):
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError("清单路径必须是非空的 POSIX 相对路径")
    posix = PurePosixPath(name)
    if (posix.is_absolute() or name != posix.as_posix()
            or any(part in (".", "..") for part in posix.parts)
            or not posix.parts or ":" in posix.parts[0]):
        raise ValueError("清单路径含绝对路径、目录跳转或非规范分隔符")
    path = root.joinpath(*posix.parts)
    if not is_within(path.resolve(), root):
        raise ValueError("清单路径或符号链接越出工程目录")
    return path


def check_manifest(report, root, skip=False, report_path=None):
    manifest_path = root / "manifest_sha256.json"
    report["manifest"] = {"path": str(manifest_path), "skipped": bool(skip)}
    if skip:
        report["skipped_checks"].append("manifest: 由 --skip-manifest 显式跳过")
        report["warnings"].append("清单未校验；该运行不能证明工程文件传输完整。")
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        record(report, "manifest_readable", False, str(exc))
        return
    if not record(report, "manifest_schema", isinstance(manifest, dict)
                  and type(manifest.get("format")) is int
                  and manifest["format"] == 1
                  and isinstance(manifest.get("files"), list)
                  and bool(manifest["files"]),
                  "需要 format=1 且 files 为非空数组"):
        return

    listed = set()
    for index, entry in enumerate(manifest["files"]):
        label = "manifest_entry_{}".format(index + 1)
        if not isinstance(entry, dict):
            record(report, label, False, "清单条目不是对象")
            continue
        name, expected_hash, expected_size = (
            entry.get("path"), entry.get("sha256"), entry.get("size"))
        try:
            path = safe_manifest_path(root, name)
            if name in listed:
                raise ValueError("清单路径重复")
            if (not isinstance(expected_hash, str)
                    or re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash) is None):
                raise ValueError("sha256 必须为 64 位十六进制字符串")
            if type(expected_size) is not int or expected_size < 0:
                raise ValueError("size 必须为非负整数")
            listed.add(name)
            if not path.is_file():
                raise ValueError("文件缺失或不是普通文件")
            actual_size = path.stat().st_size
            actual_hash = sha256_file(path)
            record(report, "file:" + name,
                   actual_size == expected_size
                   and actual_hash == expected_hash.lower(),
                   {"size_expected": expected_size, "size_actual": actual_size,
                    "sha256_expected": expected_hash.lower(),
                    "sha256_actual": actual_hash})
        except (OSError, ValueError, TypeError) as exc:
            record(report, label, False, {"path": name, "error": str(exc)})

    required = {"verify.py", "src/exam_template.tex"}
    for _kind, stem, _switch in DOCUMENTS:
        required.add("src/" + stem + ".tex")
        required.add("outputs/" + stem + ".pdf")
    missing = sorted(required - listed)
    record(report, "manifest_covers_core_files", not missing,
           {"missing_entries": missing})
    unlisted = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if (not path.is_file() or relative.parts[0] in ("build", ".git")
                or "__pycache__" in relative.parts
                or path == manifest_path
                or (report_path is not None and path.resolve() == report_path)):
            continue
        name = relative.as_posix()
        if name not in listed:
            unlisted.append(name)
    report["manifest"].update({"entries": len(manifest["files"]),
                               "unlisted_files": sorted(unlisted)})
    if unlisted:
        report["warnings"].append("有 {} 个非核心文件未列入清单，不能据此确认这些文件的完整性。"
                                  .format(len(unlisted)))


def check_sources(report, root):
    template_path = root / "src" / "exam_template.tex"
    try:
        template = template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        record(report, "template_readable", False, str(exc))
        return
    if not record(report, "template_has_one_answer_switch",
                  template.count(PLACEHOLDER) == 1,
                  {"occurrences": template.count(PLACEHOLDER)}):
        return
    for kind, stem, switch in DOCUMENTS:
        path = root / "src" / (stem + ".tex")
        try:
            actual = path.read_text(encoding="utf-8")
            expected = template.replace(PLACEHOLDER, switch)
            details = {"path": str(path), "switch": switch,
                       "expected_characters": len(expected),
                       "actual_characters": len(actual)}
            if expected != actual:
                mismatch = next((i for i, pair in enumerate(zip(expected, actual))
                                 if pair[0] != pair[1]),
                                min(len(expected), len(actual)))
                details["first_difference_line"] = expected[:mismatch].count("\n") + 1
            record(report, kind + "_source_matches_template", expected == actual, details)
        except (OSError, UnicodeError) as exc:
            record(report, kind + "_source_readable", False, str(exc))


def load_pymupdf(report, required=False):
    reasons = []
    for module_name in ("pymupdf", "fitz"):
        try:
            module = importlib.import_module(module_name)
            if not all(hasattr(module, name) for name in ("open", "Matrix", "csRGB")):
                raise ImportError("该模块不是可用的 PyMuPDF")
            report["pymupdf"] = {"available": True,
                                  "version": str(getattr(module, "VersionBind", "unknown"))}
            return module
        except Exception as exc:
            reasons.append(module_name + ": " + str(exc))
    report["pymupdf"] = {"available": False, "reasons": reasons}
    report["skipped_checks"].append("pdf_content: PyMuPDF 不可用")
    message = "PyMuPDF 不可用，未检查 PDF 页数、尺寸、文字、颜色或渲染。"
    report["warnings"].append(message)
    if required:
        report["environment_errors"].append(message + " 本次命令明确要求 PDF 检查。")
    return None


def is_red_color(value):
    red, green, blue = (value >> 16) & 255, (value >> 8) & 255, value & 255
    return red >= 80 and red - green >= 35 and red - blue >= 35


def page_text(page):
    return page.get_text("text", sort=True).replace("\r\n", "\n").rstrip()


def check_pdfs(report, pdf_dir, fitz):
    report["pdf_dir"] = str(pdf_dir)
    report["pdfs"] = []
    for kind, stem, _switch in DOCUMENTS:
        path = pdf_dir / (stem + ".pdf")
        exists = path.is_file()
        record(report, kind + "_pdf_exists", exists, {"path": str(path)})
        if not exists or fitz is None:
            continue
        item = {"kind": kind, "path": str(path), "pages": []}
        report["pdfs"].append(item)
        try:
            item["sha256"] = sha256_file(path)
            with fitz.open(path) as document:
                item["page_count"] = len(document)
                record(report, kind + "_pdf_two_pages", len(document) == 2,
                       {"actual": len(document), "expected": 2})
                for index, page in enumerate(document):
                    width = page.rect.width * 25.4 / 72
                    height = page.rect.height * 25.4 / 72
                    text = page_text(page)
                    dense_length = len(re.sub(r"\s+", "", text))
                    spans = [span for block in page.get_text("dict")["blocks"]
                             for line in block.get("lines", [])
                             for span in line.get("spans", [])
                             if span.get("text", "").strip()]
                    red_spans = [span for span in spans
                                 if is_red_color(int(span.get("color", 0)))]
                    answer_marker = "答：" in text or "答:" in text
                    details = {"page": index + 1, "width_mm": round(width, 5),
                               "height_mm": round(height, 5),
                               "non_whitespace_characters": dense_length,
                               "red_text_spans": len(red_spans),
                               "has_answer_marker": answer_marker}
                    item["pages"].append(details)
                    label = "{}_page_{}".format(kind, index + 1)
                    record(report, label + "_a3_landscape",
                           abs(width - PAGE_SIZE_MM[0]) <= SIZE_TOLERANCE_MM
                           and abs(height - PAGE_SIZE_MM[1]) <= SIZE_TOLERANCE_MM,
                           details)
                    record(report, label + "_not_blank", dense_length >= 100,
                           {"non_whitespace_characters": dense_length, "minimum": 100})
                    if kind == "questions":
                        record(report, label + "_has_no_red_answer_text",
                               not red_spans and not answer_marker, details)
                    else:
                        record(report, label + "_has_red_answers", bool(red_spans), details)
        except Exception as exc:
            record(report, kind + "_pdf_readable", False,
                   {"path": str(path), "error": str(exc)})


def compare_pdfs(report, pdf_dir, reference_dir, fitz, render_dpi=144):
    report["compare_pdf_dir"] = str(reference_dir)
    report["pdf_comparisons"] = []
    report["comparison_method"] = {
        "text": "PyMuPDF get_text('text', sort=True); normalize CRLF and strip trailing whitespace",
        "render": "RGB, opaque background, annotations included, exact pixel bytes",
        "render_dpi": render_dpi,
        "byte_mismatch_alone_is_failure": False,
    }
    if fitz is None:
        report["skipped_checks"].append("pdf_comparison: PyMuPDF 不可用")
        return
    for kind, stem, _switch in DOCUMENTS:
        actual_path, reference_path = pdf_dir / (stem + ".pdf"), reference_dir / (stem + ".pdf")
        item = {"kind": kind, "actual": str(actual_path),
                "reference": str(reference_path), "pages": []}
        report["pdf_comparisons"].append(item)
        try:
            actual_hash, reference_hash = sha256_file(actual_path), sha256_file(reference_path)
            item.update({"actual_sha256": actual_hash, "reference_sha256": reference_hash,
                         "byte_identical": actual_hash == reference_hash})
            all_equal = True
            with fitz.open(actual_path) as actual, fitz.open(reference_path) as reference:
                same_count = len(actual) == len(reference)
                all_equal = all_equal and same_count
                record(report, kind + "_comparison_page_count", same_count,
                       {"actual": len(actual), "reference": len(reference)})
                for index in range(min(len(actual), len(reference))):
                    current_page, reference_page = actual[index], reference[index]
                    same_text = page_text(current_page) == page_text(reference_page)
                    matrix = fitz.Matrix(render_dpi / 72.0, render_dpi / 72.0)
                    current_pixels = current_page.get_pixmap(
                        matrix=matrix, colorspace=fitz.csRGB, alpha=False, annots=True)
                    reference_pixels = reference_page.get_pixmap(
                        matrix=matrix, colorspace=fitz.csRGB, alpha=False, annots=True)
                    actual_size = (current_pixels.width, current_pixels.height, current_pixels.n)
                    reference_size = (reference_pixels.width, reference_pixels.height, reference_pixels.n)
                    actual_samples, reference_samples = current_pixels.samples, reference_pixels.samples
                    same_pixels = actual_size == reference_size and actual_samples == reference_samples
                    details = {"page": index + 1, "text_identical": same_text,
                               "render_pixels_identical": same_pixels,
                               "actual_pixel_dimensions": list(actual_size),
                               "reference_pixel_dimensions": list(reference_size),
                               "actual_pixel_sha256": hashlib.sha256(actual_samples).hexdigest(),
                               "reference_pixel_sha256": hashlib.sha256(reference_samples).hexdigest()}
                    item["pages"].append(details)
                    record(report, "{}_page_{}_text_and_render_match".format(kind, index + 1),
                           same_text and same_pixels, details)
                    all_equal = all_equal and same_text and same_pixels
            item["text_and_render_identical"] = all_equal
            if not item["byte_identical"] and all_equal:
                item["interpretation"] = "PDF 字节不同，但提取文字和渲染像素一致；不据字节差异认定版式变化。"
            elif all_equal:
                item["interpretation"] = "PDF 字节、提取文字和渲染像素均一致。"
            else:
                item["interpretation"] = "发现文字、页数或渲染差异，需要人工复核。"
        except Exception as exc:
            item["error"] = str(exc)
            record(report, kind + "_pdf_comparison", False, item)


def main(argv=None):
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="离线校验续作工程的文件、源码和 PDF。")
    parser.add_argument("--skip-manifest", action="store_true", help="显式跳过清单，仅用于制作阶段的临时校验")
    parser.add_argument("--pdf-dir", type=Path, default=root / "outputs", help="待检查的两份 PDF 所在目录（默认 outputs）")
    parser.add_argument("--compare-pdf-dir", type=Path, nargs="?", const=root / "outputs",
                        help="对照文字及渲染；不给目录值时使用工程 outputs")
    parser.add_argument("--require-pdf", action="store_true", help="PyMuPDF 不可用时返回环境错误")
    parser.add_argument("--render-dpi", type=int, default=144, help="PDF 对照渲染分辨率，默认 144 dpi")
    parser.add_argument("--report", type=Path, help="写出完整 JSON 校验报告")
    args = parser.parse_args(argv)
    if not 36 <= args.render_dpi <= 600:
        parser.error("--render-dpi 必须在 36 至 600 之间")
    pdf_dir = args.pdf_dir.expanduser().resolve()
    reference_dir = args.compare_pdf_dir.expanduser().resolve() if args.compare_pdf_dir is not None else None
    report_path = args.report.expanduser().resolve() if args.report is not None else None
    report = new_report(root)
    check_manifest(report, root, skip=args.skip_manifest, report_path=report_path)
    check_sources(report, root)
    fitz = load_pymupdf(report, required=args.require_pdf or reference_dir is not None)
    check_pdfs(report, pdf_dir, fitz)
    if reference_dir is not None:
        compare_pdfs(report, pdf_dir, reference_dir, fitz, args.render_dpi)

    if report["environment_errors"]:
        exit_code, status = 2, "required_capability_unavailable"
    elif report["errors"]:
        exit_code, status = 1, "failed"
    elif report["skipped_checks"]:
        exit_code, status = 0, "passed_with_explicit_or_unavailable_checks_skipped"
    else:
        exit_code, status = 0, "passed"
    report.update({"status": status, "exit_code": exit_code,
                   "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    if report_path is not None:
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            print("无法写入校验报告：" + str(exc), file=sys.stderr)
            exit_code = 2
    print("校验状态：{}；通过 {} 项；失败 {} 项；跳过 {} 项。".format(
        status, sum(item["passed"] for item in report["checks"]),
        len(report["errors"]), len(report["skipped_checks"])))
    for item in report["errors"][:20]:
        print("失败：{} — {}".format(item["name"], json.dumps(item.get("details"), ensure_ascii=False)))
    if len(report["errors"]) > 20:
        print("其余失败项请查看 JSON 报告。")
    for message in report["environment_errors"]:
        print("环境：" + message)
    for message in report["warnings"]:
        print("提示：" + message)
    if report_path is not None and report_path.is_file():
        print("报告：" + str(report_path))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
