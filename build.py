#!/usr/bin/env python3
"""Build both exam PDFs without absolute project paths or network access."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VARIANTS = {"questions": "四年级数学阶段测试_LaTeX试卷版", "answers": "四年级数学阶段测试_LaTeX答案版"}
SWITCHES = {"questions": r"\answersfalse", "answers": r"\answerstrue"}
REQUIRED = ["article.cls", "ctexart.cls", "xeCJK.sty", "zhnumber.sty", "tikz.sty", "geometry.sty", "amsmath.sty", "amssymb.sty", "fontspec.sty", "FandolSong-Regular.otf", "FandolHei-Regular.otf"]


def execute(args, *, env=None, cwd=ROOT, timeout=180):
    return subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, check=False)


def tool(name):
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"找不到 {name}。请安装 TeX Live（含 XeLaTeX、LaTeX 基础宏包和 TikZ），并加入 PATH。")
    return found


def add_search_path(env, name, directory):
    # A trailing path separator keeps the distribution's default lookup paths.
    old = env.get(name, "")
    env[name] = directory.as_posix() + "//" + os.pathsep + old + os.pathsep


def environment():
    env = os.environ.copy()
    vendor = ROOT / "vendor" / "texmf"
    if not (vendor / "tex" / "latex" / "ctex" / "ctexart.cls").is_file():
        raise RuntimeError("缺少 vendor/texmf 中的 CTeX 支持文件；请完整解压工程包。")
    kpse = tool("kpsewhich")
    previous = execute([kpse, "-var-value=TEXMF"], env=env).stdout.strip()
    if previous:
        # Keep all original TeX trees. Removing index-only markers also handles
        # restored cloud machines whose system ls-R indexes no longer exist.
        env["TEXMF"] = "{" + vendor.as_posix() + "," + previous.replace("!!", "") + "}"
    add_search_path(env, "TEXINPUTS", vendor / "tex")
    add_search_path(env, "OPENTYPEFONTS", vendor / "fonts" / "opentype")
    var = ROOT / "build" / "texmf-var"
    var.mkdir(parents=True, exist_ok=True)
    env["TEXMFVAR"] = var.as_posix()
    env["TEXMFCACHE"] = (ROOT / "build" / "texmf-cache").as_posix()
    # Generated formats stay in the project and are excluded from the archive.
    env["TEXFORMATS"] = var.as_posix() + "//" + os.pathsep + env.get("TEXFORMATS", "") + os.pathsep
    return env


def diagnose(env):
    kpse, engine = tool("kpsewhich"), tool("xelatex")
    versions = execute([engine, "--version"], env=env).stdout.splitlines()[:3]
    found = {}
    for item in REQUIRED:
        result = execute([kpse, item], env=env)
        found[item] = result.stdout.strip() if result.returncode == 0 else ""
    return {"python": sys.version.split()[0], "xelatex": versions,
            "dependencies": found, "missing": [k for k, v in found.items() if not v]}


def ensure_format(env):
    kpse = tool("kpsewhich")
    current = execute([kpse, "-engine=xetex", "-format=fmt", "xelatex.fmt"], env=env)
    if current.returncode == 0 and current.stdout.strip():
        return {"generated": False, "format": current.stdout.strip()}
    ini = execute([kpse, "xelatex.ini"], env=env)
    if ini.returncode or not ini.stdout.strip():
        raise RuntimeError("缺少 xelatex.ini，无法生成格式文件。请补齐 TeX Live 的 LaTeX/XeTeX 基础组件。")
    target = ROOT / "build" / "texmf-var"
    print("正在生成本机适用的 xelatex.fmt（仅首次需要）……", flush=True)
    result = execute([tool("xelatex"), "-ini", "-etex", "-interaction=nonstopmode",
                      "-halt-on-error", "-jobname=xelatex", "xelatex.ini"],
                     env=env, cwd=target)
    (target / "format_generation.log.txt").write_text(result.stdout, encoding="utf-8")
    if result.returncode or not (target / "xelatex.fmt").is_file():
        raise RuntimeError("格式生成失败，详见 build/texmf-var/format_generation.log.txt\n" + result.stdout[-2000:])
    return {"generated": True, "format": str(target / "xelatex.fmt")}


def sync_sources():
    template = (ROOT / "src" / "exam_template.tex").read_text(encoding="utf-8")
    if template.count("% ANSWER_SWITCH") != 1:
        raise RuntimeError("统一模板中必须恰有一个 % ANSWER_SWITCH 标记。")
    for key, name in VARIANTS.items():
        (ROOT / "src" / (name + ".tex")).write_text(
            template.replace("% ANSWER_SWITCH", SWITCHES[key]), encoding="utf-8")
    print("已根据统一模板同步两份独立 TEX。", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doctor", action="store_true", help="只检查编译器及依赖，不编译试卷")
    parser.add_argument("--sync-sources", action="store_true", help="先从统一模板重新生成两份独立 TEX")
    parser.add_argument("--variant", choices=["all", *VARIANTS], default="all")
    parser.add_argument("--out-dir", default="build/pdf", help="新 PDF 输出目录；默认不覆盖已交付的 outputs")
    args = parser.parse_args()
    if args.sync_sources:
        sync_sources()
    env = environment()
    report = diagnose(env)
    if report["missing"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise RuntimeError("缺少上列依赖。工程内已含中文支持与字体；标准 LaTeX/TikZ 宏包需由 TeX Live 提供。")
    if args.doctor:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    report["format"] = ensure_format(env)
    target = Path(args.out_dir)
    if not target.is_absolute():
        target = ROOT / target
    target.mkdir(parents=True, exist_ok=True)
    report["documents"] = []
    keys = list(VARIANTS) if args.variant == "all" else [args.variant]
    for key in keys:
        name = VARIANTS[key]
        source = ROOT / "src" / (name + ".tex")
        if not source.is_file():
            raise RuntimeError(f"缺少源码：{source.name}")
        # Pin the default fonts used in the accepted Linux edition. This does
        # not change the archived source files or require system font installs.
        tex_input = (r"\PassOptionsToClass{fontset=fandol}{ctexart}"
                     r"\input{\detokenize{" + source.as_posix() + "}}")
        cmd = [tool("xelatex"), "-no-shell-escape", "-interaction=nonstopmode",
               "-halt-on-error", "-file-line-error", "-recorder",
               "-output-directory=" + str(target), "-jobname=" + name, tex_input]
        for iteration in (1, 2):
            print(f"编译 {name}：第 {iteration}/2 次", flush=True)
            result = execute(cmd, env=env)
            (target / f"{name}.pass{iteration}.txt").write_text(result.stdout, encoding="utf-8")
            if result.returncode:
                raise RuntimeError(f"{name} 编译失败。日志在 {target}\n" + result.stdout[-2500:])
        log = (target / (name + ".log")).read_text(encoding="utf-8", errors="replace")
        problems = [line for line in log.splitlines() if "Overfull" in line or "Missing character" in line]
        if problems:
            raise RuntimeError(f"{name} 生成了PDF，但出现溢出或缺字：\n" + "\n".join(problems))
        info = {"variant": key, "pdf": str(target / (name + ".pdf")),
                "passes": 2, "layout_errors": problems,
                "panel_heights": re.findall(r"PANEL-[^\r\n]+", log)}
        report["documents"].append(info)
    (ROOT / "build" / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("编译完成。新 PDF：" + str(target))
    print("下一步：python verify.py --pdf-dir build/pdf --compare-pdf-dir outputs")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print("错误：" + str(exc), file=sys.stderr)
        raise SystemExit(1)
