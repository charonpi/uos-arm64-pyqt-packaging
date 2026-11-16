---
name: uos-arm64-pyqt-packaging
display_name: 统信 UOS arm64 PyQt 应用打包
display_name_en: UOS arm64 PyQt App Packaging
description: 把 PyQt 或纯 Python 桌面应用打包成可在统信 UOS 20（arm64, glibc 2.28）上运行的 deb 安装包。当用户需要为 UOS、Deepin、麒麟 arm64 打包 Python GUI 程序，或遇到 GLIBC_2.29 not found、PyQt6 轮子不兼容、x86 与 arm 架构不符、Python 3.7 语法报错、python3-pyqt5 缺失等问题时使用。
description_zh: 面向统信 UOS 20 arm64 的 PyQt 应用 deb 打包全流程：源码迁移、Python 3.7 兼容检查、构建、安装验证与排错。
description_en: End-to-end workflow to package PyQt or Python desktop apps as deb installers for UOS 20 arm64 (glibc 2.28), covering source migration, Python 3.7 checks, build, install and troubleshooting.
examples_zh:
  - "帮我把这个 PyQt6 程序打包成能在统信 UOS 20 arm64 上安装的 deb"
  - "UOS 上启动报 libm.so.6: version GLIBC_2.29 not found，怎么修"
  - "检查一下这份源码有没有 Python 3.7 跑不了的语法"
  - "帮我生成一个 arch:all 的 deb，依赖系统 python3-pyqt5"
examples_en:
  - "Package my PyQt6 app as a deb for UOS 20 arm64"
  - "Fix GLIBC_2.29 not found on UOS arm64"
  - "Check whether my source is Python 3.7 compatible"
  - "Build an arch:all deb that depends on system python3-pyqt5"
version: 1.0.0
author: "Wang Zizheng (charonpi)"
category: 开发工具
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
disable-model-invocation: false
user-invocable: true
license: MIT
agent_created: true
---

# 统信 UOS 20 arm64 — PyQt 应用打包

## 0. 一句话结论（决策门禁，先读）

在 UOS 20（内核 4.19 / **glibc 2.28** / **aarch64** / 系统 **Python 3.7**）上，**任何「pip 安装并捆绑 Qt 运行库」的路线都不可靠**：PyQt6 / PySide6 的 aarch64 wheel 要么不存在，要么内部 Qt 实际链接 `GLIBC_2.29`，装到 UOS 必崩。

唯一稳定路线固定为四段式：

```
A 源码降级 PyQt6 → PyQt5 + Python 3.7 兼容
      ↓
B 纯 Python 依赖内置 third_party/ + sys.path 引导
      ↓
C 构建 Architecture: all 的 deb（不捆 Qt，依赖系统 python3-pyqt5）
      ↓
D 目标机 apt 安装系统 PyQt5 + dpkg -i + 启动验证
```

判定依据与实测数据见 `references/compatibility-matrix.md`。**不要**在确认目标机环境前直接开始构建。

## 1. 环境预检（每次任务第一步）

把 `scripts/preflight_uos.sh` 复制到目标 UOS 机器执行，确认四项硬指标：

| 指标 | 期望 | 不达标时 |
|---|---|---|
| 架构 | `aarch64` | 本技能不适用，改用常规 x86_64 打包流程 |
| glibc | 2.28 | 若 ≥2.29，可评估 PyQt6 路线，见兼容矩阵 |
| Python | 3.7.x | 若 ≥3.8，仍需按 3.7 写源码（发行版自带解释器为准） |
| `python3-pyqt5` | apt 仓库可见 | 必须让目标机可安装；这是整个方案的外部前提 |

```sh
sh scripts/preflight_uos.sh
```

**外部前提无法远程验证**：目标机必须能 `sudo apt install -y python3-pyqt5`。若仓库里没有该包，先解决软件源/开发者模式，再继续。

## 2. 阶段 A — 源码迁移

在**源码副本**上执行（绝不直接改原工程）：

```bash
python3 scripts/migrate_pyqt6_to_pyqt5.py <源码目录> --dry-run   # 先看报告
python3 scripts/migrate_pyqt6_to_pyqt5.py <源码目录> --apply --backup
```

脚本自动完成：`PyQt6` → `PyQt5` 导入替换；PyQt6 作用域枚举展平（`Qt.ItemFlag.X` → `Qt.X` 等）；`.exec()` → `.exec_()`；每个 `.py` 在 docstring/future 之后插入 `from __future__ import annotations`。

随后人工复核三件事（脚本只做机械替换）：
1. 所有 `list[X]` / `dict[X,Y]` / `X | None` 是否**只出现在注解位置**；
2. `QAction`、`QShortcut` 等模块归属差异；
3. 自定义枚举/常量是否被误替换（报告会列出改动行）。

完整枚举映射表与 Python 3.7 语法红线见 `references/migration-guide.md`。

## 3. 阶段 B — 兼容性检查与依赖内置

```bash
python3 scripts/check_py37_compat.py <源码目录>            # 表格报告
python3 scripts/check_py37_compat.py <源码目录> --json     # 供 CI 消费
```

检查项：缺失 `from __future__ import annotations`、非注解位置的 PEP 585 / PEP 604 用法、3.8+ 语法（海象运算符、positional-only、match）、3.8+ 标准库 API。**有 ERROR 必须先修完再打包**，否则目标机 import 即崩。

纯 Python 依赖必须随包内置（不要指望目标机 pip）：

```bash
python3 -m pip install --target=<源码目录>/third_party openpyxl==3.1.2
# openpyxl 依赖 et-xmlfile，--target 会自动带上；手工拷贝时务必一并复制
```

在入口文件最顶部（任何业务 import 之前）插入 `templates/bootstrap.py.tpl` 的引导片段，或由构建脚本 `--inject-bootstrap` 自动注入。openpyxl 3.1.2 的 `requires_python >=3.6`，分类器明确含 3.7。

## 4. 阶段 C — 构建 deb

```bash
python3 scripts/build_deb.py \
  --src <源码目录> --pkg my-app --version 1.0.0 \
  --entry main.py --app-name "我的应用" \
  --third-party <源码目录>/third_party \
  --out ./dist
```

生成 `DEBIAN/control`、`/usr/bin/<pkg>` 启动器、`/usr/share/applications/<pkg>.desktop`、程序目录与 `third_party/`，产出 `<pkg>_<version>_all.deb`。

- 构建机**不要求 arm64**（产物 `Architecture: all`），Linux 即可；Windows 上自动降级为 `--staging-only`，把 staging 目录传到 Linux 后执行 `dpkg-deb --build`。
- Debian 10 已 EOL：先跑 `scripts/fix_debian10_sources.sh` 修源（含 `Check-Valid-Until=false`、`buster-updates` 注释），再 `apt install -y python3 python3-pip dpkg-dev fonts-noto-cjk`。
- **不需要**在构建机安装 Qt / libxcb / libgl1，那些是「捆绑 Qt」路线才需要的。
- 模板文件在 `templates/`，可直接按项目需要改写占位符后复用。

逐条命令、目录布局、control 字段含义与服务器构建实操见 `references/build-and-deploy.md`。

## 5. 阶段 D — 目标机安装与验收

```bash
sudo apt install -y python3-pyqt5 fonts-noto-cjk
sudo dpkg -i my-app_1.0.0_all.deb
sudo apt install -f                 # 补依赖
my-app                              # 或桌面双击图标
```

验收清单：终端可启动、桌面图标可启动、中文不方块、写出/读取 Excel 正常、`dpkg -l | grep my-app` 有记录。失败时按 `references/troubleshooting.md` 的症状表逐项定位。

## 6. 硬性禁止清单

- 禁止把 x86_64 的 wheel / 二进制拷进 arm64 包；`Architecture: all` 包内不得含任何 ELF 文件。
- 禁止用 `pip install PyQt6` / `PySide6` 后把 `.so` 打进包（glibc 2.28 上必崩）。
- 禁止在运行时位置写 `isinstance(x, list[str])`、`cast(list[str], x)`、`x = list[str]`（3.7 会抛 `TypeError`）。
- 禁止省略 `from __future__ import annotations`（含 dataclass 文件）。
- 禁止假设目标机能联网 pip；纯 Python 依赖一律内置。
- 禁止硬编码构建机绝对路径、用户名或凭据到交付物中。

## 7. 资源索引

| 资源 | 用途 | 何时加载 |
|---|---|---|
| `references/compatibility-matrix.md` | glibc / wheel / 解释器兼容矩阵、失败路线证据 | 判断能否走别的方案时 |
| `references/migration-guide.md` | PyQt6→PyQt5 枚举全表、3.7 语法红线 | 阶段 A、B |
| `references/build-and-deploy.md` | 端到端命令、Debian 10 改源、deb 目录规范 | 阶段 C、D |
| `references/troubleshooting.md` | 症状 → 根因 → 修复 | 报错时 |
| `scripts/migrate_pyqt6_to_pyqt5.py` | 源码机械迁移（幂等、可 dry-run、可备份） | 阶段 A |
| `scripts/check_py37_compat.py` | 静态兼容性门禁 | 阶段 B |
| `scripts/build_deb.py` | 参数化构建 arch:all deb | 阶段 C |
| `scripts/preflight_uos.sh` | 目标机环境自检 | 阶段 0 |
| `scripts/fix_debian10_sources.sh` | 修复 Debian 10 EOL 源 | 构建机准备 |
| `templates/*.tpl` | control / 启动器 / desktop / sys.path 引导模板 | 需要人工定制时 |
| `assets/icon-512.png` | 技能市场 512×512 展示图标 | 发布技能时 |

## 8. 交付话术

向用户交付时，始终明确三件事：产物 deb 的绝对路径与 `Architecture: all`；目标机必须自行 `apt install python3-pyqt5`；未通过 `preflight_uos.sh` 与 `check_py37_compat.py` 前不承诺「能跑」。
