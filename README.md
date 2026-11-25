# 20261104龙口市红旗小学四年级数学期中考试试卷

根据原始试卷照片整理的四年级数学试卷与答案 LaTeX 工程。现行试卷版和答案版各 **2 页，A3 横向（420 × 297 毫米）**，保持原卷双栏顺序，题图用 TikZ 绘制。

仓库中文标题及日期采用用户指定的名称；原卷印刷标题为“2026—2027学年度第一学期阶段测试”，工程内原文件名和题目内容保持原样。GitHub 仓库路径采用英文名称，以满足平台的 ASCII 命名限制。

## 直接查看或打印

| 文件 | 用途 |
| --- | --- |
| [试卷版 PDF](outputs/四年级数学阶段测试_LaTeX试卷版.pdf) | 学生使用，无答案 |
| [答案版 PDF](outputs/四年级数学阶段测试_LaTeX答案版.pdf) | 含红色答案、计算步骤和作图 |
| [统一 LaTeX 模板](src/exam_template.tex) | 维护题目、答案及全部 TikZ 图形 |
| [试卷版 TEX](src/四年级数学阶段测试_LaTeX试卷版.tex) | 独立试卷源码 |
| [答案版 TEX](src/四年级数学阶段测试_LaTeX答案版.tex) | 独立答案源码 |

打印设置：**A3、横向、实际大小 100%**。试卷 TEX 为便于统一维护，仍含条件隐藏的答案；发给学生请使用试卷 PDF。

## 工程目录

| 路径 | 内容 |
| --- | --- |
| `src/` | 统一模板、两份独立 TEX；图形全部在源码中 |
| `outputs/` | 当前交付的试卷和答案 PDF |
| `originals/` | 两张原始照片 |
| `docs/` | 接续状态、关键纠错、答案索引、来源、依赖及验证记录 |
| `vendor/texmf/` | Fandol、Latin Modern 字体，CTeX、xeCJK、zhnumber 文件及上游许可证 |
| `reference/` | 早期七页详解 PDF 和历史交付说明 |
| `build.py`、`build.sh`、`build.cmd` | 编译入口 |
| `verify.py` | 离线检查文件清单、源码、PDF 尺寸和答案颜色 |
| `package_project.py` | 刷新校验清单并生成完整续作 ZIP |
| `manifest_sha256.json` | 文件大小和 SHA-256 清单 |

本仓库直接保存展开后的全部工程文件。使用 GitHub 的 **Code → Download ZIP** 即可下载完整目录；也可以用 Git 克隆。

## 环境与编译

需要 Python 3.10 或以上，以及提供 XeLaTeX、`kpsewhich`、标准 LaTeX/TikZ/AMS/fontspec 等组件的 TeX Live。工程已携带字体和中文支持文件，但不包含操作系统相关的 TeX 引擎二进制或完整 TeX 发行版。

在工程根目录运行：

```sh
python -m pip install -r requirements.txt
python verify.py --require-pdf
python build.py --doctor
python build.py
python verify.py --require-pdf --pdf-dir build/pdf --compare-pdf-dir outputs
```

`build.py` 使用 Python 标准库，编译过程不自动下载依赖。PyMuPDF 用于完整 PDF 检查。新生成的 PDF 位于 `build/pdf/`，不会覆盖 `outputs/` 中的交付版本。每份源码连续编译两次；入口固定使用 Fandol 字体，并在必要时为当前机器生成 XeLaTeX 格式文件。

Linux/macOS 可用 `sh build.sh`，Windows 可用 `build.cmd`。**Windows 和 macOS 尚未实机验证**。

## 继续修改与在新对话中接续

先读 [README_先读我.txt](README_先读我.txt)、[接续状态](docs/接续状态.json)、[内容校正与答案索引](docs/内容校正与答案索引.txt) 和 [AGENTS.md](AGENTS.md)。全部题目和答案已经完成，没有待解答的下一题。

下载完整 ZIP 后，可把它上传到新对话，并发送 [新对话接续指令.txt](新对话接续指令.txt) 中的文字。新对话也可直接从本仓库克隆工程。不要只上传 PDF；源码、字体、编译入口和接续记录须一起保留。

优先编辑 `src/exam_template.tex`，然后同步两份源码：

```sh
python build.py --sync-sources
```

若独立 TEX 已有改动，先合并回模板再同步。修改后检查两份 PDF 的全部四页，确认题图、栏间续题、行距及作答区，再更新成品和状态记录。重新打包：

```sh
python package_project.py --output ../math_exam_project_updated.zip
```

## 关键内容约定

- 选择题二4答案为 **B**，仅①②正确。保留原题“大小一样”，本工程按已确认的“面积相等”解释，不据此推定两个三角形全等。
- 保留“团圆虎”“碳素笔”“石膏、藿香、柴胡”等已核实文字。
- 保持 A3 横向、双栏、各两页、`ctexart`、XeLaTeX、Fandol 和 TikZ；所有题意处理详见答案索引。

## 验证记录与已知边界

- **2026-11-19 的历史实测**：在含中文和空格的新目录重编译，两份 PDF 的全部四页与交付成品在提取文字和 144 dpi RGB 像素上完全一致。记录见 [迁移运行检查](docs/迁移运行检查_20261119.json)。
- **2026-11-25 发布前核验**：从续作 ZIP 恢复的原工程为 237 个文件，共 50,544,632 字节；原清单 236 条逐项匹配，`verify.py --require-pdf` 的 257 项检查全部通过。本轮未重新编译或修改试题、答案、版式与字体。
- GitHub 发布新增首页、Git 配置和发布说明，打包脚本及清单相应更新；详情见 [GitHub发布说明](docs/GitHub发布说明.txt)。
- 早期七页详解 PDF 保存在 `reference/`，其旧 ReportLab 生成脚本未恢复；当前两页 A3 LaTeX 工程源码完整。
- 字体与依赖保留各自上游许可证。本次发布未为试题及原创工程另行指定开源许可证。
