# uos-arm64-pyqt-packaging

> 把 PyQt（或纯 Python）桌面应用，打包成能在 **统信 UOS 20 arm64（glibc 2.28 / Python 3.7）** 上直接安装、双击运行的 `.deb`。
> 它既是一个 WorkBuddy / Claude-style **Skill**，也是一套可以脱离 AI 单独使用的命令行工具。

**版本** v1.0.0 · **许可证** MIT · **作者** 王梓铮 (charonpi) · **实测环境** UOS 20 arm64（内核 4.19）+ 阿里云 Debian 10.13 arm64

---

## 目录

- [这个技能解决什么问题](#这个技能解决什么问题)
- [该不该用它：30 秒判断](#该不该用它30-秒判断)
- [安装技能（3 种方式）](#安装技能3-种方式)
- [5 分钟从零到 .deb](#5-分钟从零到-deb)
- [目录结构](#目录结构)
- [脚本与模板速查](#脚本与模板速查)
- [可运行示例](#可运行示例)
- [常见问题](#常见问题)
- [上架技能市场](#上架技能市场)
- [项目边界](#项目边界)
- [反馈与贡献](#反馈与贡献)

---

## 这个技能解决什么问题

在 UOS 20 arm64 上打包 Python GUI 程序，最常见的结局是这三条死路：

| 尝试 | 结果 |
|---|---|
| `pip install PyQt6` 后把 Qt 运行库一起打进包 | `libm.so.6: version 'GLIBC_2.29' not found` —— aarch64 wheel 标签写 `manylinux_2_28`，内部 Qt 实际链接 2.29 |
| `pip install PySide6` | wheel 是 `manylinux_2_31`，要求 glibc 2.31 |
| 用 PyQt6 ≤6.6 / PyQt5-Qt5 的 pip wheel | 官方没有 aarch64 Linux 轮子，`No matching distribution found` |

UOS 20 的 glibc 恰好卡在 **2.28**：太低装不上新 wheel，太高又跑不了。本技能给出的唯一稳定解法是：

```
源码降级 PyQt6 → PyQt5（Python 3.7 兼容）
        ↓
纯 Python 依赖内置 third_party/ + sys.path 引导
        ↓
构建 Architecture: all 的 .deb（包内零二进制，不捆 Qt）
        ↓
目标机 apt 安装发行版自编译的 python3-pyqt5
```

因为包里全是文本与 `.py`，**构建机架构和 glibc 都无关**，交叉编译、sysroot、Qt 插件路径等一整类问题从根上消失。

完整证据与兼容性矩阵见 [`uos-arm64-pyqt-packaging/references/compatibility-matrix.md`](uos-arm64-pyqt-packaging/references/compatibility-matrix.md)。

---

## 该不该用它：30 秒判断

| 你的情况 | 建议 |
|---|---|
| UOS 20 / Deepin 20 / 麒麟 V10，**arm64，glibc 2.28** | ✅ 直接用 |
| 目标机 x86_64 | ❌ 用 PyInstaller / 常规 pip 方案更简单 |
| 项目强依赖 Qt6 专属 API，无法降级到 PyQt5 | ❌ 需要自行交叉编译 Qt，超出本技能范围 |
| 目标机 glibc ≥ 2.31 | ⚠️ 本方案仍可用，但可重新评估 PySide6 wheel 路线 |
| 目标机 apt 仓库里**没有** `python3-pyqt5` | ⛔ 外部前提，先修软件源，否则不要开始 |
| 程序是纯 Python、不需要 Qt | ✅ 适用，把 `Depends` 改成 `python3 (>= 3.7)` 即可 |

一键自检：把 `scripts/preflight_uos.sh` 拷到目标机执行 `sh preflight_uos.sh`，看输出是不是 `READY`。

---

## 安装技能（3 种方式）

### 方式 1：WorkBuddy 客户端上传（推荐，最省事）

1. 下载 [`dist/uos-arm64-pyqt-packaging.zip`](dist/uos-arm64-pyqt-packaging.zip)（带顶层技能目录的标准包）。
2. WorkBuddy 客户端 → **技能 → 添加技能 → 上传技能** → 选择该 zip → 启用。
3. 新开一个任务说：「帮我把这个 PyQt6 程序打包成 UOS 20 arm64 的 deb」，技能会按描述自动触发。

### 方式 2：手动放到技能目录

```bash
git clone https://github.com/charonpi/uos-arm64-pyqt-packaging.git
cp -r uos-arm64-pyqt-packaging/uos-arm64-pyqt-packaging ~/.workbuddy/skills/
```

Windows 对应 `C:\Users\<用户名>\.workbuddy\skills\`。项目级共享可放到 `<项目>/.workbuddy/skills/`。

### 方式 3：只用命令行，不装技能

克隆仓库后直接跑 `uos-arm64-pyqt-packaging/scripts/` 下的脚本，完全不依赖 AI：

```bash
python3 uos-arm64-pyqt-packaging/scripts/check_py37_compat.py ./your-app
python3 uos-arm64-pyqt-packaging/scripts/build_deb.py --src ./your-app --pkg my-app --entry main.py --out ./dist
```

> **两个 zip 的区别**：`uos-arm64-pyqt-packaging.zip` 带顶层目录，给客户端「上传技能」用；`uos-arm64-pyqt-packaging-openplatform.zip` 是根目录直铺（`SKILL.md` 在 zip 根），给 WorkBuddy 开放平台提交审核用。详见 [`docs/PUBLISH.md`](docs/PUBLISH.md)。

---

## 5 分钟从零到 .deb

以下假设：你有一个 PyQt6 写的桌面程序，入口是 `myapp/main.py`，用到 openpyxl，目标是 UOS 20 arm64。

### 步骤 0 · 目标机自检（UOS 上执行）

```bash
sh uos-arm64-pyqt-packaging/scripts/preflight_uos.sh
sudo apt install -y python3-pyqt5 fonts-noto-cjk
```

### 步骤 1 · 源码副本 + 自动迁移（任意开发机）

```bash
cp -r myapp myapp-build                     # 永远在副本上操作
S=uos-arm64-pyqt-packaging/scripts

python3 $S/migrate_pyqt6_to_pyqt5.py myapp-build --dry-run     # 先看报告，逐行复核
python3 $S/migrate_pyqt6_to_pyqt5.py myapp-build --apply --backup
```

脚本完成：PyQt6→PyQt5 导入、作用域枚举展平（`Qt.ItemFlag.X` → `Qt.X`）、`.exec()` → `.exec_()`、每个 `.py` 插入 `from __future__ import annotations`。**注释和字符串里的文字不会被改**。

### 步骤 2 · Python 3.7 兼容门禁（必须零 ERROR）

```bash
python3 $S/check_py37_compat.py myapp-build
# Scanned N file(s): 0 ERROR, 0 WARN  →  GATE PASSED
```

会报出运行时位置的 `list[str]` / `X | None`、3.8+ 语法与 3.8+ 标准库 API。修完再继续。

### 步骤 3 · 内置纯 Python 依赖

```bash
python3 -m pip install --target=myapp-build/third_party openpyxl==3.1.2
ls myapp-build/third_party | grep -E 'openpyxl|et_xmlfile'    # 两个都要有
```

`openpyxl==3.1.2` 的 PyPI 元数据为 `requires_python >=3.6`，分类器明确含 3.7。**必须锁版本**，否则高版本 Python 的构建机可能拉到要求 3.8+ 的新版。`et-xmlfile` 是它的运行时依赖，手工拷贝时最容易漏。

### 步骤 4 · 构建 .deb（Linux 构建机）

Debian 10 已 EOL，先修源（脚本会备份 `sources.list`、改 archive 源、注释 `buster-updates`、关闭 Release 有效期校验）：

```bash
sudo sh $S/fix_debian10_sources.sh
python3 $S/build_deb.py \
  --src myapp-build --pkg myapp --version 1.0.0 \
  --entry main.py --app-name "我的应用" \
  --maintainer "Your Name <you@example.com>" \
  --description "My PyQt5 desktop application" \
  --third-party myapp-build/third_party \
  --out ./dist --inject-bootstrap
```

产出 `dist/myapp_1.0.0_all.deb` + `.sha256` + `build-report.json`。

Windows 上没有 `dpkg-deb`，脚本会自动降级为生成 `dist/_staging_myapp/`，把这个目录传到 Linux 后一行命令收尾：

```bash
dpkg-deb --build --root-owner-group _staging_myapp myapp_1.0.0_all.deb
```

### 步骤 5 · 目标机安装与验收

```bash
sudo dpkg -i myapp_1.0.0_all.deb
sudo apt install -f                 # 自动补齐 python3-pyqt5 依赖
myapp                              # 终端先跑，能看真实报错
```

| 检查 | 通过标准 |
|---|---|
| `dpkg-deb -I myapp_1.0.0_all.deb` | `Architecture: all`、Depends 含 `python3-pyqt5` |
| `dpkg-deb -c myapp_1.0.0_all.deb \| grep '\.so'` | **无输出**（包内零二进制） |
| `python3 -c 'import PyQt5.QtCore'` | 成功 |
| 终端 `myapp` / 桌面图标双击 | 窗口正常，中文不方块 |

排错速查见 [`references/troubleshooting.md`](uos-arm64-pyqt-packaging/references/troubleshooting.md)。

---

## 目录结构

```
uos-arm64-pyqt-packaging/            ← GitHub 仓库根
├── README.md                       ← 本文（完整中文说明）
├── README.en.md                    ← 英文简介
├── LICENSE                         ← MIT
├── CHANGELOG.md
├── docs/
│   ├── PUBLISH.md                  ← 技能市场上架保姆级教程 + 展示文案
│   └── guide.html                  ← 本文的自包含 HTML 离线阅读版
├── uos-arm64-pyqt-packaging/       ← ★ 技能包本体（zip 的内容）
│   ├── SKILL.md                    ← 技能定义（YAML frontmatter + 四阶段工作流）
│   ├── README.md
│   ├── references/                 ← 4 份按需加载的参考文档
│   │   ├── compatibility-matrix.md
│   │   ├── migration-guide.md
│   │   ├── build-and-deploy.md
│   │   └── troubleshooting.md
│   ├── scripts/                    ← 5 个可直接运行的脚本
│   │   ├── migrate_pyqt6_to_pyqt5.py
│   │   ├── check_py37_compat.py
│   │   ├── build_deb.py
│   │   ├── preflight_uos.sh
│   │   └── fix_debian10_sources.sh
│   ├── templates/                  ← control / launcher / desktop / bootstrap 模板
│   └── assets/icon-512.png         ← 512×512 市场图标（约 7 KB）
├── examples/hello-pyqt5/           ← 迁移前 / 迁移后可运行示例
├── tools/
│   ├── make_icon.py                ← 重新生成图标
│   └── make_release.py             ← 校验 + 生成两种 zip + SHA256
└── dist/                           ← 构建产物（zip / sha256）
```

技能包严格保持**两级目录**（根 + 一级子目录），符合 WorkBuddy 开放平台对技能包结构的校验要求。

---

## 脚本与模板速查

| 脚本 | 关键参数 | 作用 | 运行位置 |
|---|---|---|---|
| `preflight_uos.sh` | 无 | 检查架构 / glibc / Python / `python3-pyqt5` / 中文字体 / 图形会话 | **目标 UOS 机** |
| `migrate_pyqt6_to_pyqt5.py` | `<src>` `--dry-run` / `--apply --backup` `--exclude` `--report` | PyQt6→PyQt5 机械迁移，幂等，只改代码不改字符串注释 | 任意开发机 |
| `check_py37_compat.py` | `<src>` `--json` `--strict` | Python 3.7 静态门禁，ERROR 时退出码 1 | 任意开发机 |
| `build_deb.py` | `--src --pkg --version --entry --app-name --third-party --out --inject-bootstrap --staging-only` | 参数化生成 `arch:all` deb / staging | Linux 构建机（Windows 自动降级） |
| `fix_debian10_sources.sh` | 无（需 root） | 修复 Debian 10 EOL 源、装构建依赖 | **构建机**，不要跑在 UOS 上 |

| 模板 | 占位符 | 生成物 |
|---|---|---|
| `control.tpl` | `PKG` `VERSION` `DEPENDS` `MAINTAINER` `DESCRIPTION` | `DEBIAN/control` |
| `launcher.tpl` | `ENTRY_PATH` | `/usr/bin/<pkg>` |
| `desktop.tpl` | `APP_NAME` `DESCRIPTION` `PKG` | `/usr/share/applications/<pkg>.desktop` |
| `bootstrap.py.tpl` | 无 | 入口文件顶部的 sys.path 引导 |
| `build-config.example.json` | — | 参数示例（文档性质，不自动加载） |

`build_deb.py` 会优先读取同级 `templates/` 下的模板，改模板即可定制，不用改 Python。

---

## 可运行示例

[`examples/hello-pyqt5/`](examples/hello-pyqt5/) 里有迁移前 / 迁移后两个最小 GUI 程序，以及一条完整的复现命令链。Windows / macOS / Linux 上都能跑通迁移 + 检查 + 生成 staging，无需 UOS 实机：

```bash
mkdir -p /tmp/demo && cp examples/hello-pyqt5/main_pyqt6.py /tmp/demo/main.py
python3 uos-arm64-pyqt-packaging/scripts/migrate_pyqt6_to_pyqt5.py /tmp/demo --apply
python3 uos-arm64-pyqt-packaging/scripts/check_py37_compat.py /tmp/demo
python3 uos-arm64-pyqt-packaging/scripts/build_deb.py --src /tmp/demo \
  --pkg hello-pyqt5 --entry main.py --out /tmp/demo-dist --inject-bootstrap
```

---

## 常见问题

**Q：为什么要降级到 PyQt5，不能用 PyQt6？**
UOS 20 的 glibc 2.28 与官方 aarch64 wheel 不兼容，Qt 二进制加载不了。PyQt5 由发行版自己编译，天然匹配本机 glibc。详见兼容矩阵。

**Q：构建机必须是 arm64 吗？**
不需要。产物是 `Architecture: all`，包内全是文本，任意 Linux（甚至 Windows 只生成 staging）都行。这是本方案最大的便利点。

**Q：目标机一定要联网 / 能 apt 吗？**
必须能装 `python3-pyqt5`（一次即可）。这是唯一的外部前提，无法远程绕过；若 apt 仓库没有该包，先解决软件源或开发者模式。

**Q：纯 Python 程序（不用 Qt）能用吗？**
能，把 `--depends` 改成 `python3 (>= 3.7)`，其余流程不变。

**Q：为什么 openpyxl 要锁 3.1.2？**
构建机 Python 版本通常高于目标机，不锁版本 pip 可能装到要求 3.8+ 的新包。3.1.2 的 `requires_python >=3.6`，且分类器含 3.7，已核对 PyPI 元数据。

**Q：双击图标没反应？**
先终端跑 `<pkg>` 看真实报错，再检查 UOS 开发者模式/安全策略、desktop 的 `Exec` 路径和 `Terminal=false`。见排错文档 A 组。

**Q：怎么换成麒麟 / Deepin？**
只要 `preflight_uos.sh` 显示 aarch64 + glibc 2.28 且 apt 有 `python3-pyqt5`，流程一致。

**Q：zip 里到底要不要顶层目录？**
两种规范并存：客户端「上传技能」用带顶层目录的包；开放平台提交用根目录直铺包。仓库 `dist/` 里两个都给了，用错会报「解析失败」，换另一个重试即可。

---

## 上架技能市场

完整步骤（含个人实名认证、市场展示文案、分类、512×512 图标、审核自查、版本递增规则）见 [`docs/PUBLISH.md`](docs/PUBLISH.md)。

简版：登录 [open.workbuddy.cn](https://open.workbuddy.cn) → 完成个人认证 → **发布管理 → 技能** → 上传 `dist/uos-arm64-pyqt-packaging-openplatform.zip` → 补齐展示信息（文案已在 PUBLISH.md 里写好可直接复制）→ 上传 `assets/icon-512.png` → 提交审核（约 7 个工作日）。

> 实名认证、原创声明与提交审核必须由账号本人完成，任何自动化工具都不应代做这一步。

---

## 项目边界

本技能**不做**：Qt 交叉编译、Qt6 专属 API 兼容、签名/加固、付费发行配置、目标机软件源修复、非 Debian 系发行版（RPM / pacman）打包。

本技能**不承诺**：目标机无法安装 `python3-pyqt5` 时程序能运行；源码无法降级到 PyQt5 时能打包。这两条属于外部前提，`SKILL.md` 要求 AI 在交付时明确告知，不夸大能力。

---

## 反馈与贡献

欢迎提 Issue / PR，尤其欢迎补充：新的实测兼容数据、`migrate_pyqt6_to_pyqt5.py` 的枚举作用域白名单、其它国产 arm64 发行版的 `preflight_uos.sh` 结果、排错文档里没覆盖的报错。

提交前请跑：

```bash
python3 tools/make_release.py     # 校验 frontmatter / 目录层级 / 资源引用 / 图标，并重建两种 zip
```

许可证：MIT，见 [LICENSE](LICENSE)。
