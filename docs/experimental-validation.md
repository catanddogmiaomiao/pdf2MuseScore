# 实验审谱版本

分支：`experiment/music-validation`。保留原有 PyQt 界面与本地 Audiveris 流程。

## 试用

### 可操作的审谱工作台

点击“打开审谱工作台”，选择具体问题，查看原值、建议和操作说明。
可筛选谱号问题、待核对、已修复和已核对。
对于单项谱号疑点，直接选择“改为普通高音谱号”或“保留原样”。
不再要求先勾选确认。处理后进入下一项，撤销只在已修改的项目中显示。
界面只显示简短音乐说明，规则、评分和 XML 留在报告文件中。
修改立即保存到单独的 `.reviewed.musicxml`，支持逐项撤销。
“标记已核对”只记录审核状态，不改乐谱，支持恢复待核对。
操作与原因保存在 `.review-state.json`，下次打开继续审核。
处理后的报告另存为 `.reviewed.validation_report.json`，含修复前后值。

已有报告不需要重跑 OMR：未开始转换时点击工作台按钮，选择之前生成的
`.validation_report.json`（不是 TXT 摘要），并保留它对应的原始 MXL。
“打开原始 MXL”用于比较；“在 MuseScore 中打开处理结果”打开当前版本。
节奏、休止符和音高疑点由用户在 MuseScore 按识别小节编号修改。
本工具不能控制 MuseScore 光标定位，编号可能与 PDF 印刷编号不同。
MuseScore 中修改后请另存 MSCZ，后续谱号修复/撤销会从原始 MXL 重新生成 reviewed 文件。

选择 PDF 并开始识别。输出目录同时保留原始 MXL、`.validated.musicxml`、
`.validation_report.json` 和 `.validation_summary.txt`。界面显示修复数量与待检查数量，
点击“查看审谱报告”查看具体声部、小节、谱表、Voice、规则和理由。
MuseScore 默认打开 validated 文件。原始 MXL 可用于对照和恢复。

转换默认不修复八度谱号疑点。用户可在工作台逐项选择修复，
只移除 `clef-octave-change`，不移动 `pitch`，修复前后值写入报告。
原谱有合法八度标记的项目应保留原样。规则评分不是统计正确率。

## 已实现

- CLEF_OCTAVE_ANOMALY：高音谱号八度标记、文档级谱号分布、系统边界与乐器信息。
- MEASURE_DURATION：有理数时值、拍号变化、加法拍号、backup/forward、和弦、装饰音、弱起与声部内部空隙。
- VOICE_ANOMALY：游标越界、声部重叠、小提琴孤立额外声部提示。
- BEAM_STRUCTURE：分声部与符杠级别检查起止；不将符杠休止符直接视为错误。
- SUSPICIOUS_REST：符杠休止符、多拍与邻近音符共同出现才提示。
- OCTAVE_JUMP：仅在八度谱号疑点附近提示大音程。
- TIE_SLUR：线性 XML 顺序下延音线同音高配对、连音线编号配对。
- ACCIDENTAL_CONFLICT：显式升降号与 pitch/alter 矛盾提示。
- PATTERN_ANOMALY：同节奏同音级不同音区，且具有独立谱号疑点的基础重复小节提示。
- SYSTEMATIC_OMR_ERROR：重复八度谱号候选；不因为重复就擅自修改。

独立模块使用 Python 标准库，不增加模型、付费服务或大型依赖。
统一 Issue、集中阈值和 Reviewer 接口供后续扩展。

## 限制

这是第一版规则审谱，不能保证找到所有 OMR 错误。重复模式目前只比较小节，
没有实现完整乐句相似度；不自动删休止符、改声部或修音高。
跨小节符杠、跨声部连音线和反复路径可能被提示，需要人工判断。
小节编号来自识别结果，可能与 PDF 印刷编号不同。
仅支持 score-partwise MusicXML。时值检查依据 XML 的实际 duration，
不重新从 type/dot 推算演奏时值。末小节可能是弱起补足。
审谱异常会回退原始输出。多份乐谱输出暂时明确报错，避免只取最新一份。

## 回归测试

`python -m unittest discover -s tests -v`

涵盖用户要求的八项基础案例，及合法符杠休止符、时值、多声部、
原始文件保留与审谱失败回退。测试不能代替对真实 PDF 的音高和播放核对。

谱号和时值语义依据：

- https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/clef-octave-change/
- https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/duration/

## 本机样例验证（2026-09-16）

Audiveris 5.11.0，内置 Java 25.0.3+9-LTS。输入为用户提供的六页
MERRY GO ROUND OF LIFE.pdf，使用工作区副本 sample.pdf。
完整调用 `Audiveris.exe -batch -transcribe -export -save -output <独立工程目录> -- sample.pdf`。
第六页无五线谱，使用已保存 OMR 加 `-sheets 1-5` 恢复导出，总耗时 346.85 秒。
识别结果含 122 个小节元素；默认不自动修复，共 63 条核对提示，
包括 42 条时值、9 条符杠、6 条八度谱号、4 条音程、1 条延音线和
1 条文档级重复谱号候选。这些是规则疑点，不代表 63 个确定错误。

确认标记错误模式修复了 6 处谱号，未改变 XML pitch。
MuseScore 4 命令行成功导入修复文件并保存 MSCZ；修复前后 MuseScore
读入的 342 个音符音高序列一致。尚未人工核验所有音符、视觉位置与播放。
Audiveris 日志仍显示缺少 OCR 语言；文字、标题及乐器名识别受影响。
14 项自动测试通过，PyQt 界面构造、PDF 加载和报告按钮状态检查通过。
真实 PDF 与输出仅保留本地，未提交到仓库。
