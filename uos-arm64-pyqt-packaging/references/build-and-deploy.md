# 端到端构建与部署手册

配套脚本：`scripts/fix_debian10_sources.sh`、`scripts/build_deb.py`、`scripts/preflight_uos.sh`。模板：`templates/`。

## 0. 全流程鸟瞰

```
[开发机 Windows/macOS]            [Linux 构建机]                [UOS 20 arm64 目标机]
  源码副本                          dpkg-deb                      apt/dpkg
  ├ migrate_pyqt6_to_pyqt5.py  →   ├ fix_debian10_sources.sh  →   ├ preflight_uos.sh
  ├ check_py37_compat.py          ├ build_deb.py                 ├ apt install python3-pyqt5
  └ pip --target third_party      └ <pkg>_<ver>_all.deb          ├ dpkg -i + apt install -f
                                                                  └ 终端/桌面启动验证
```

`build_deb.py` 在没有 `dpkg-deb` 的机器（如 Windows）上会自动降级为只生成 staging 目录，把该目录整体传到 Linux 后执行一行 `dpkg-deb --build` 即可。

## 1. 准备源码副本（开发机）

```bash
cp -r /path/to/original-app /path/to/build-src        # 永远在副本上操作
python3 scripts/migrate_pyqt6_to_pyqt5.py /path/to/build-src --dry-run
python3 scripts/migrate_pyqt6_to_pyqt5.py /path/to/build-src --apply --backup
python3 scripts/check_py37_compat.py /path/to/build-src
```

内置纯 Python 依赖（openpyxl 只是示例，按项目实际依赖替换）：

```bash
python3 -m pip install --target=/path/to/build-src/third_party openpyxl==3.1.2
ls /path/to/build-src/third_party | grep -E 'openpyxl|et_xmlfile'   # 两个都要有
```

> 构建机若 Python 版本很高（3.11+），**务必锁定版本号**，否则 pip 可能拉到要求 3.8+ 的新版依赖。`openpyxl==3.1.2` 的 `requires_python` 为 `>=3.6`，分类器含 3.7，已验证。

入口文件加入 `templates/bootstrap.py.tpl` 的 sys.path 引导，或让构建脚本自动注入：

```bash
python3 scripts/build_deb.py ... --inject-bootstrap
```

## 2. 构建机准备（Debian 10.13 arm64 已验证）

Debian 10 已 EOL，默认源全部 404。修复脚本一次性处理三件事：改 archive 源、注释 `buster-updates`、关闭 Release 有效期校验。

```bash
sudo sh scripts/fix_debian10_sources.sh
```

等价手工命令（便于排查）：

```bash
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak
sudo sed -i 's|deb.debian.org|archive.debian.org|g; s|security.debian.org|archive.debian.org/debian-security|g' /etc/apt/sources.list
sudo sed -i 's|^deb \(.*\) buster-updates |# deb \1 buster-updates |' /etc/apt/sources.list
sudo apt-get -o Acquire::Check-Valid-Until=false update
sudo apt-get install -y python3 python3-pip dpkg-dev fonts-noto-cjk
```

**三个常见坑**：
| 现象 | 原因 | 修复 |
|---|---|---|
| `apt update` 满屏 404 | 仍指向 `deb.debian.org` / EOL 的 `buster-updates` | 上面两条 sed |
| `Release file ... is not valid yet / expired` | archive.debian.org 的 Release 已过期 | `-o Acquire::Check-Valid-Until=false` |
| 装 Qt 相关包浪费时间 | 误以为要捆绑 Qt | 不需要；`arch:all` 包内无任何 `.so` |

## 3. 生成 .deb

把 `源码副本/` 与技能包 `scripts/`、`templates/` 一并传到构建机（保持技能包目录完整，`build_deb.py` 会从同级 `templates/` 读模板）。

```bash
python3 scripts/build_deb.py \
  --src /path/to/build-src \
  --pkg file-organizer \
  --version 1.0.0 \
  --entry main.py \
  --app-name "文件整理工具" \
  --maintainer "Your Name <you@example.com>" \
  --description "Export folder trees to Excel with hyperlinks" \
  --third-party /path/to/build-src/third_party \
  --out ./dist
```

输出：
- `dist/file-organizer_1.0.0_all.deb`
- `dist/file-organizer_1.0.0_all.deb.sha256`

### 生成的 staging 布局

```
<staging>/
├── DEBIAN/control
├── usr/bin/file-organizer                     # 755，#!/bin/sh 启动器
├── usr/share/applications/file-organizer.desktop
├── usr/share/icons/hicolor/256x256/apps/file-organizer.png   # 传了 --icon 才有
└── usr/share/file-organizer/
    ├── main.py ...                            # 源码
    └── third_party/                          # 内置依赖
```

### control 关键字段

```
Package: file-organizer
Version: 1.0.0
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.7), python3-pyqt5
Maintainer: ...
Description: ...
```

- `Architecture: all` — 全文本包，构建机架构无关；
- `Depends: python3-pyqt5` — 让 `apt install -f` 自动补系统 Qt 绑定；
- **不要**写 `Depends: python3-pyqt6`、`libqt6*` 或任何 pip 包。

### Windows 上只生成 staging

```bash
python3 scripts/build_deb.py --src ... --pkg ... --out ./dist --staging-only
# 输出 dist/_staging_<pkg>/，scp 到 Linux 后：
# dpkg-deb --build --root-owner-group _staging_<pkg> file-organizer_1.0.0_all.deb
```

## 4. 目标机安装

```bash
sh scripts/preflight_uos.sh          # 先自检，重点看 python3-pyqt5 是否可安装
sudo apt install -y python3-pyqt5 fonts-noto-cjk
sudo dpkg -i file-organizer_1.0.0_all.deb
sudo apt install -f                  # 自动补齐 Depends
file-organizer                       # 终端启动，看真实报错
```

桌面图标位于 `/usr/share/applications/<pkg>.desktop`；若双击无反应，先开终端跑 `<pkg>` 看输出，再检查 UOS 开发者模式/安全策略（见 `troubleshooting.md`）。

## 5. 验收清单

| # | 检查 | 通过标准 |
|---|---|---|
| 1 | `dpkg -l \| grep <pkg>` | 状态 `ii` |
| 2 | `dpkg-deb -I <deb>` | `Architecture: all`，Depends 含 `python3-pyqt5` |
| 3 | `dpkg-deb -c <deb> \| grep -E '\.so\|ELF'` | 无输出（包内无二进制） |
| 4 | `python3 -c 'import PyQt5.QtCore'` | 成功 |
| 5 | 终端执行 `<pkg>` | 窗口正常出现，无 Traceback |
| 6 | 桌面图标双击 | 与终端一致；中文不方块 |
| 7 | 读写 Excel / 业务主流程 | 功能完整 |
| 8 | `python3 -m compileall /usr/share/<pkg>` | 无 SyntaxError |

第 3 项常被忽略：`find <staging> -type f -exec file {} \;` 若出现 ELF，说明误把 wheel 二进制打进包，必须清除。

## 6. 升级与回滚

```bash
# 升级：修改源码后必须递增 version（deb 与 SKILL.md 版本号语义独立）
python3 scripts/build_deb.py --src ... --pkg file-organizer --version 1.0.1 ...
sudo dpkg -i file-organizer_1.0.1_all.deb

# 回滚
sudo dpkg -r file-organizer
sudo dpkg -i file-organizer_1.0.0_all.deb
```

## 7. 常见目录陷阱（来自真实事故）

- 脚本若用相对路径 `Linux程序/../源码` 找源码，两个目录必须是**同级兄弟目录**；本项目已改为 `--src` 显式传参，不再有此约束。
- 不要把 `third_party/` 放进 `usr/bin/`；桌面项 `Exec` 必须指向 `/usr/bin/<pkg>` 启动器，而不是 `python3 /usr/share/.../main.py`。
- `desktop` 文件必须 `Terminal=false`，否则 UOS 会把终端窗口一起拉起。
- 启动器要传 `"$@"`，否则命令行参数丢失。
