四年级数学阶段测试：续作工程包
整理日期：2026-11-19（北京时间）

一、这个包对应什么
本包仅对应本对话上传的两张“2026—2027学年度第一学期阶段测试”四年级数学试卷照片。
现行版本为 ctexart / XeLaTeX / TikZ：试卷版和答案版各2页，A3横向，420×297毫米。
全部题目、答案和作图已经完成，没有待解答的下一页或下一题。
包内包含原始照片、最新成品、完整现行可编辑源码、编译入口、字体与中文依赖、校验工具、接续状态和关键纠错。

二、先看哪些文件
outputs/：已经交付的两份最新PDF，可直接查看或打印。
src/exam_template.tex：统一模板，是同时维护试卷与答案的入口。
src/四年级数学阶段测试_LaTeX试卷版.tex、答案版.tex：两份完整独立源码。
originals/：用户最初上传的两张照片，保留原始字节。
docs/接续状态.json：完成状态、真实验证结果、已知限制和下一步。
docs/内容校正与答案索引.txt：已确认的数学答案与不能回退的题意校正。
vendor/texmf/：原版使用的Fandol、Latin Modern字体及CTeX/xeCJK/zhnumber支持文件，含来源和许可证。
reference/：早期七页详解和上次交付说明，仅供参考，不作为当前版式入口。

三、在新对话中继续
将整个ZIP上传到新对话，复制“新对话接续指令.txt”的内容给新对话。
新对话应先解压、读取说明和接续状态、运行校验和编译，再根据你的新要求修改。
不需要依赖旧对话的临时工作目录，也不需要重新输入全部试题。

四、运行要求
1. Python 3.10或以上。
2. TeX Live提供的XeLaTeX、kpsewhich及标准LaTeX/TikZ/AMS/fontspec等宏包。
   本包携带中文宏包与字体，但不携带每种操作系统的TeX编译器二进制。
3. 完整PDF检查需要PyMuPDF；本次使用1.26.6。可运行：
   python -m pip install -r requirements.txt
编译入口本身只使用Python标准库，不自动下载、不联网。

五、校验与重新编译
完整解压ZIP，进入math_exam_project目录后运行：
   python verify.py --require-pdf
   python build.py --doctor
   python build.py
   python verify.py --require-pdf --pdf-dir build/pdf --compare-pdf-dir outputs
Linux/macOS也可运行：sh build.sh
Windows可运行：build.cmd（需要已安装Python及TeX Live，且相关命令在PATH中）。

新生成的PDF放在build/pdf/，不会覆盖outputs/中已经交付的版本。
每份PDF连续编译两次，以固定TikZ页边框、密封线等位置。
首次遇到缺少xelatex.fmt时，脚本会用当前机器的XeLaTeX在build/texmf-var中生成，不使用旧机器的格式缓存。
脚本通过类选项固定fontset=fandol，以复现现行Linux默认字体；无需把字体安装到操作系统。
直接双击或单独编译TEX时，其他系统的CTeX自动字体可能不同，应使用本包build.py来复现版面。

六、修改后怎么做
优先编辑src/exam_template.tex，再运行：
   python build.py --sync-sources
这会从统一模板更新两份独立TEX。若直接改过独立TEX，请先合并回模板，避免被覆盖。
修改后进行版式检查：
   python verify.py --skip-manifest --require-pdf --pdf-dir build/pdf
源文件改动后原清单哈希变化是正常现象；不要把原清单仍有效当成新版本已核验。
逐页检查两份PDF的全部四页。确认后再将新PDF复制到outputs/，更新docs/接续状态.json和检查记录。
重新打包时运行：
   python package_project.py --output ../四年级数学阶段测试_续作工程包_更新版.zip
该命令会刷新文件校验清单，只收入工程文件，省略build/缓存与临时工具。

七、真实状态与边界
本轮已恢复现行LaTeX工程与两张原图，恢复后的两份源码可重新编译。
现行TEX在两个版本中仅答案开关不同，所有图形都在源码中，不依赖外部图片。
试卷TEX为了统一维护仍含条件隐藏的答案；给学生使用的是outputs/中的试卷PDF。
早期七页详解PDF已保留，但其旧ReportLab生成脚本没有恢复，不属于本次可重新生成的现行LaTeX工程。
Windows/macOS尚未实机验证；本轮实际检查的平台、结果及检查时点均写在docs/中。
PDF重新编译后可能因元数据导致文件哈希不同，应结合文本和渲染比较判断内容是否一致。

打印：A3、横向、实际大小100%。

八、本轮实测结果（2026-11-19）
已将工程ZIP解压到含中文和空格的全新目录，从工程目录之外启动build.py。
已由新目录内的编译入口自行生成格式文件并将两份源码各编译两次。
两版仍为各2页A3，重编译四页与最新成品的文字和144dpi渲染像素全部一致。
清单、文件大小、SHA-256、源码同步、PDF尺寸及红色答案检查均通过。
编译输入记录未引用旧工作目录；详细证据在docs/迁移运行检查_20261119.json。
