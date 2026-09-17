# 完整便携版验证

## 构建组成

- GUI：PyInstaller 6.5.0 / Python 3.12.2 / PyQt6，独立窗口程序。
- 引擎：同一固定 HOMR 源码提交，PyInstaller 6.5.0，hooks-contrib 2026.7。
- 模型：CPU Segnet、Transformer encoder / decoder，随包附带 SHA-256 清单。
- 标题 OCR 关闭；固定 CPU，不自动下载模型。
- 曲谱库、模型识别逻辑和 MusicXML 内容不做自动纠错。

## 已验证

18 项单元/集成测试通过，覆盖转换、取消、内存异常、曲谱库、语言切换以及便携引擎优先级。
引擎 `--self-test` 验证模型哈希，并分别创建三个 CPU ONNX 会话，全部成功。

发现并修复两个打包问题：

1. NumPy 2.5 的 C 扩展动态引用 `numpy._core._exceptions`，需要明确收集 `_core` 模块。
2. Qt6Core 调用 Windows 自带 `icuuc.dll` 的无版本后缀符号，其他包引入的 ICU 78 同名 DLL
   只有带 `_78` 的符号，导致 QtCore 导入失败。GUI spec 检测导入符号，并排除冲突 ICU DLL；
   保留 Windows 自带实现。

ZIP 创建后检查全部成员的 CRC，校验成功才替换最终 ZIP；磁盘空间不足不会被误报为成功。

## 搬移及真实转换

在当前 Windows 10 x64 机器上将整个程序移到 `work/便携测试/PDF2Muse`，
PATH 仅保留 Windows 目录，同时设置无效 PYTHONHOME / PYTHONPATH。
调用实际窗口版 EXE 的 `--verify-portable 输入.pdf 输出目录`，由其启动包内 HOMR.exe。
测试原始 6 页小提琴样例，最后一页纯白。

实际冻结 GUI → 冻结引擎转换成功，退出码 0，耗时 195.34 秒；
正确跳过第 6 页，合并全部 5 页非空白页。输出 117 小节、338 个音符/休止符元素，
音符数据与此前源代码环境导出结果对比。当前真实转换不调用系统 Python，日志中的实际命令
指向搬移目录下 `engine/HOMR.exe`。测试后恢复原发布目录。

这属于当前机器的隔离环境及路径搬移验证，不能替代一台全新 Windows 电脑的实际验收。
没有对伴奏版内存消耗重新作保证；便携打包不降低模型的识别内存需求。
