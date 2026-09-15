# PDF2Muse

Windows 本地 PDF 五线谱导入工具。目标流程：

**PDF → Audiveris → MusicXML / MXL → MuseScore Studio**

免费、本地识别，不调用付费 API，不上传乐谱，不限制转换次数。
识别结果保留原样，人工在 MuseScore 中检查、修改和播放。

## 当前阶段

第一阶段：验证 Audiveris 的真实 PDF 转换能力。尚未开发产品 GUI、播放器或自动纠错。
先证明识别结果有用，再编写 Python CLI、基础检查模块，最后决定是否开发 GUI。

本机验证记录见 [首次验证](docs/first-validation.md)。

## 依赖

- Windows 10/11 x64。
- [Audiveris 5.11.0 稳定版](https://github.com/Audiveris/audiveris/releases/tag/5.11.0)：
  推荐 `Audiveris-5.11.0-windowsConsole-x86_64.msi`，便于保存命令行日志。
  官方 Windows 包包含 Java 运行时，无须依赖系统 PATH 中的 Java。
- [MuseScore Studio](https://github.com/musescore/MuseScore/releases)：用于打开 MXL、编辑和播放。
- 后续 Python 封装将以 Python 3.12 为验证基线。

下载软件需要网络；乐谱转换在本机执行。第三方程序使用各自的开源许可证，
本仓库不包含第三方安装包、运行库、用户乐谱或识别输出。

## 直接运行 Audiveris

在 PowerShell 中运行，按实际安装位置修改路径：

```powershell
& "C:\Program Files\Audiveris\Audiveris.exe" -version
& "C:\Program Files\Audiveris\Audiveris.exe" -batch -transcribe -export -save -output "C:\Scores\result" -- "C:\Scores\score.pdf"
```

`-batch` 禁用 Audiveris GUI，`-transcribe` 识别整份谱，`-export` 导出 MusicXML，
`-save` 保留 OMR 工程，`-output` 设置输出目录。输入路径始终放在 `--` 后。
输出可能位于子目录，也可能因分段产生多个 MXL，不应只猜测一个同名输出文件。

使用本仓库的验证脚本记录版本、命令、耗时和结果：

```powershell
.\scripts\verify-audiveris.ps1 -Pdf "C:\Scores\score.pdf" -Audiveris "C:\Program Files\Audiveris\Audiveris.exe"
```

脚本每次创建独立目录，防止把上次的 MXL 误报成本次成功；完整日志和本机路径只保存在本地。
成功导出不等于音符识别准确。请对照原 PDF 检查音高、节奏、声部、连线和反复记号。

## 开发顺序

1. 真实 PDF → 官方 Audiveris → MXL，记录识别问题。
2. MuseScore 导入、编辑、播放验证，评估比手工录入省多少工作。
3. 最小 Python 命令行入口和 `--open`；增加可配置的程序发现。
4. 仅报告可疑小节，不自动修改识别结果。
5. 识别效果验证可用后，再开发极简 Windows GUI。

第一阶段直接处理 PDF；图像预处理、声部筛选和批量转换留待后续实测决定。

## 参考

- [Audiveris CLI](https://audiveris.github.io/audiveris/_pages/guides/advanced/cli/)
- [Audiveris 安装说明](https://audiveris.github.io/audiveris/_pages/tutorials/install/binaries/)
- [MuseScore 命令行](https://handbook.musescore.org/appendix/command-line-usage)

