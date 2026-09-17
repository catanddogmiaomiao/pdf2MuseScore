# PDF2Muse — HOMR 实验版

Windows 本地 PDF 乐谱转换工具，使用 PyQt6 界面。

**PDF → 本地 HOMR → 原始 MusicXML → MuseScore Studio**

免费、不上传乐谱。HOMR 是唯一识别后端，不依赖 Audiveris 或 Java。
识别结果不自动纠错；打开 MuseScore 试听、编辑。

## 安装与运行

准备 Python 3.11 或 3.12、MuseScore Studio。

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\setup-homr.ps1
python main.py
```

首次安装需要网络下载 HOMR、依赖和模型。默认独立环境位于
`%LOCALAPPDATA%\PDF2Muse\homr-runtime`，程序自动查找。
开发环境也支持项目下 `.homr-runtime`；设置中可手动选择独立环境的 `python.exe`。
不要把 HOMR 安装到 GUI 的 Python 环境中。

导入 PDF 后显示分页预览，选择保存位置并开始识别。阶段状态来自实际处理日志，
不显示虚构百分比。可取消识别；完成后可打开输出目录或在 MuseScore 中打开。

在“设置 → 语言”中选择简体中文、English、日本語或한국어，点击保存后立即生效，
下次启动沿用该选择。切换时保留 PDF 页码、文件路径及当前任务。
按钮、状态与错误提示均支持这四种语言；HOMR 原始日志保留原文。

纯白页会被跳过，并显示页码；其他识别失败不会静默跳过。
没有完整合并结果时不会把部分页标记为成功。
输入先复制到 `.pdf2muse/<任务编号>`，所有中间图片和日志留在该任务目录。
原文件不被覆盖，重复转换输出自动编号。

## 曲谱库

顶部“曲谱库”可搜索、预览、重命名和打开已导入的乐谱。导入时将 PDF 复制到
`%LOCALAPPDATA%\PDF2Muse\library`，按文件内容去重；原文件移动或存储卡断开后仍可查看副本。
每次成功识别都在库中保存独立的 MusicXML 和日志版本，不覆盖旧结果。
“更多 → 关联 MuseScore 文件”可选择自己的 `.mscz` / `.mscx`，此后默认打开该修改版；
也可在版本列表选择原始识别结果。关联文件保留原位置，程序不监视或猜测 MuseScore 的保存行为。
双击列表或“查看原谱”恢复转换页的 PDF 和最近结果。“重新识别”使用库中的 PDF。
“从曲谱库移除”只移除索引，保留库中的 PDF 和结果文件。
不会自动导入升级前的历史输出；需要重新导入对应 PDF。

## 固定后端

采用官方源码提交 `5e51b434b3149286dae1448603527923b62ef9f2`，安装元数据标记
`0.7.0+5e51b434`。PyPI 0.7.0 与当前官方接口不同，不直接使用该发行包。
`requirements-homr.txt` 固定源码；间接依赖由安装器解析，并记录在运行环境
`installed-versions.txt`。模型由 HOMR 初始化下载，保存在独立环境中。

当前采用 CPU ONNX 推理，关闭标题 OCR 以减少耗时；不生成自己的内部音符格式，
不重新生成 MusicXML，也不添加审谱或八度修复。

HOMR 侧重点是高音/低音谱号的音高与节奏，复杂记号的识别仍有局限。
成功导出文件不代表准确识别全部音符。测试记录见 [HOMR 验证](docs/homr-validation.md)。

## 打包

```powershell
python -m pip install -r requirements-build.txt
.\build.ps1
```

分发整个 `dist\PDF2Muse` 目录。PyInstaller 仅打包 GUI 与调用桥接脚本，
不打包 HOMR、ONNX、模型或 MuseScore。首次使用运行 `_internal\setup-homr.ps1`。
该脚本默认创建上述用户级环境，打包后无需开发机器的绝对路径。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试完整合并输出、中文路径、失败页退出码为 0、部分结果拒绝导出及静默进程取消。

## 开源组件

[HOMR](https://github.com/liebharc/homr) 使用 AGPL-3.0；
[MuseScore Studio](https://github.com/musescore/MuseScore) 使用其自身许可证。
本仓库不提交模型、用户乐谱或识别输出。早期 `design` 文档仅作历史记录。
