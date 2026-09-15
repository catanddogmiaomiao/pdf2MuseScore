# 首次本机验证

日期：2026-09-15。此记录区分运行环境验证与识别效果验证。

## 环境

| 项目 | 观测结果 |
| --- | --- |
| Windows | Windows 10，build 19045，x64 |
| Python | 3.12.2，可运行 |
| 系统 Java | PATH 存在 Oracle Java 启动项，但无法启动 |
| Audiveris | 最初未安装；官方 5.11.0 Windows Console 包已下载并校验 SHA-256 |
| 包内 Java | runtime/release 标明 25.0.3；在受限命令执行器中启动失败 |
| MuseScore | 最初只有 MuseHub；官方 Studio 4.7.5 解包后，命令行确认版本 4.7.5，build 3654226 |

Audiveris 安装包 SHA-256：
`5f1b4e96a12c53c7da426814b76e599363c4181e291855996e0a6878dda95f71`

MuseScore 安装包 SHA-256：
`07b0f3292612e2df4c7e0632deb790add51b218f0ee33f7fecaa6111dd279ec6`

## 输入

用户提供 `MERRY GO ROUND OF LIFE.pdf`，360225 字节，6 页。
可见乐谱为小提琴独奏，前 5 页有谱，第 6 页空白，末尾印刷小节号为 117。
前 5 页的乐谱内容是约 1050 像素宽的嵌入式位图，不是矢量音符 PDF。
输入保留原样，未做 PNG 中转、裁边或图像增强。

输入 SHA-256：`99d10d017ff3777559b98c20d55df294bf05f10c0d19536fd3a0ce4b6cbfb802`

## 环境问题与处理

1. Windows Installer 管理提取失败：退出码 1603，日志中包含 2502/2503。
2. 用 lessmsi 解包官方 MSI 后可以访问完整程序文件，不需要改动 OMR。
3. Audiveris 包内 Java 25.0.3 在受限执行器中失败：
   `InternalError: Error loading java.security file`，根因为 `Path.toRealPath()` 检查父目录时
   遇到 `AccessDeniedException`。直接读同一个文件成功，但逐级 `FindFirstFileW` 检查父目录失败。
4. 使用 Temurin JRE 26.0.2.1 做诊断后 Java 自身可继续启动，但 JavaCPP 的缓存路径检查
   又遇到同一类父目录访问限制。该替代运行时没有用于产出任何乐谱，不作为产品默认依赖。
5. 临时目录副本、申请目录读取权限和申请专用运行目录均未消除当前受限命令执行器的问题。

相关 Java 上游修复：[JDK-8352728](https://github.com/openjdk/jdk/pull/29121)。
这是本次运行环境的启动障碍，不能当作 Audiveris 的识别失败。

## 识别验证状态

尚未成功进入 OMR 阶段。已准备本机启动脚本，待在普通 Windows 会话中执行后读取结果。

| 检查 | 状态 |
| --- | --- |
| PDF → Audiveris → MXL | 待完成 |
| 转换耗时 | 尚无有效数据 |
| MuseScore 导入 | 待完成 |
| 可编辑音符 | 待完成 |
| 实际播放 | 待完成 |
| 音符与节奏识别准确度 | 尚不可评估 |

## 后续人工核对清单

普通音符、调号、拍号、临时升降号、休止符、附点、连音线、延音线、三连音分别核对。
当前样例没有钢琴伴奏，不能据此评价钢琴和弦、多声部或跨谱表；这些需要第二份总谱样例。
反复记号也应使用明确含反复的小样例补测。

完整本机日志和路径保存在用户电脑中，不随源代码提交。
成功标准仍是人工修正工作量明显少于从头输入，单纯产生 MXL 文件不代表达到该标准。
