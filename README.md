# PDF2Muse 0.3.0 for Windows

PDF 五线谱 → 本地 HOMR → MusicXML → 可选的 MuseScore Studio 编辑。

官网：https://pdf2muse.top 。本分支基于官网此前使用的 `feature/homr`。
Windows 10 1809+/11 x64。识别环境、CPU 模型、Python 与 Qt 随安装包提供。
MuseScore Studio 需另行安装，不是识别所必需。转换结果应逐项对照原谱检查。

## 安装与账号

运行 `PDF2Muse-0.3.0-Windows-x64-Setup.exe`，按当前 Windows 用户安装，无需管理员权限。
通过“账号 / Account”注册，试用从注册时起连续计算 30 天，不会自动扣款。
有效授权码可永久激活；在线购买价格为 US$9.90，一次性付款，无自动续费。
适用税费与最终金额以 Creem 托管收银台为准，付款方式由 Creem 实际提供。
账号使用用户名/密码登录；注册需要邮箱验证码，另可使用仅显示一次的恢复码找回。
注册与重置密码邮件采用 Resend，与 Book2AudioGo 的方式一致。发信域名与密钥尚需配置；客服邮箱按要求保留待填。
注册、登录、激活与授权刷新需要联网，签名离线授权最长 7 天；识别和乐谱保存在本机。
永久购买不按月或年收费，但仍须至少每7天联网刷新授权。

当前运营主体、地区和品牌客服邮箱尚待填写，Creem 付款入口保持关闭。
不能将本次技术部署或法律文件草案称为已通过 Creem 审核或正式收款就绪。
账号服务源码与部署配置位于独立网站仓库的 `service/`。

## 法律文件与开源

隐私声明、服务与销售条款、EULA、退款政策、联系信息和第三方声明：
https://pdf2muse.top/legal/ 。安装后也可通过“法律 / Legal”离线查看。
购买后14天内可申请全额退款，适用消费者法定权利不受影响。

PDF2Muse 代码采用 GPL-3.0-only，见 LICENSE；第三方组件保留各自许可证。
HOMR 代码与模型按上游 AGPLv3 提供，并通过独立进程调用。
GPL 权利不受官方账号或付费安排额外限制，用户可依法修改和再分发代码。
程序不内嵌整个源码目录；下载页并列提供对应版本的源码压缩包与版本化仓库链接。
完整对应源码获取无需付费。不要只提供会变化的默认分支。

HOMR 上游说明训练数据权利可能不同于代码/权重许可证，商业模型权利仍需核实：
https://github.com/liebharc/homr/blob/main/LICENSE_FAQ.md 。详见 THIRD-PARTY-NOTICES.md。

## 从源码构建

GUI 以 Python 3.12.2 构建，固定依赖见 requirements-gui-lock.txt。

```powershell
python -m pip install -r requirements-gui-lock.txt
.\setup-homr.ps1 -Runtime .\.homr-runtime
.\.homr-runtime\Scripts\python.exe -m pip install -r requirements-engine-build.txt
.\build-portable.ps1 -RuntimePython .\.homr-runtime\Scripts\python.exe
.\packaging\build-installer.ps1 -SkipGuiBuild -InnoCompiler C:\Tools\InnoSetup6\ISCC.exe
```

本次安装程序使用许可明确允许商业用途的 Inno Setup 6.2.2；7.x 的商业授权要求不能忽略。
`packaging/build-installer.ps1 -EngineDir <冻结HOMR目录>` 也可复用已经验证的固定引擎，
始终重新检查模型哈希与三个 ONNX CPU 会话。GUI 改动不会重新训练或修改模型。
PyInstaller 在 spec 中收集 Qt 和依赖许可证；发布还应保留 Python 和引擎依赖通知。

源码压缩包：

```powershell
python packaging/make_source.py --homr-source <固定HOMR完整源码ZIP> --output dist/PDF2Muse-0.3.0-corresponding-source.zip
```

这会收集工作树中未忽略的应用源码、构建脚本、测试、许可证和完整固定 HOMR 上游源码。
用户乐谱、运行凭据、密钥、构建产物和私有账号数据不得提交或打包。

## 验证

```powershell
python -m unittest discover -s tests -v
```

安装后应在隔离 PATH、无系统 Python/Java 依赖的条件下测试真实 PDF → MusicXML，
并测试登录、到期、授权码、退款回调及离线授权签名。
`--verify-portable 输入.pdf 输出目录` 使用实际冻结 GUI → 引擎转换，仍要求有效账号授权。
本地曲谱库位于 `%LOCALAPPDATA%/PDF2Muse/library`；账号凭据受当前 Windows 用户 DPAPI 保护。
卸载保留曲谱、输出及账号设置，不远程删除用户文件。
