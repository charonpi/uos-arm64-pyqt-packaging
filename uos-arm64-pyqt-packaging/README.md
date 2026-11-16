# uos-arm64-pyqt-packaging

WorkBuddy / Claude-style Skill：把 PyQt（或纯 Python）桌面应用打包成可在 **统信 UOS 20 arm64（glibc 2.28 / Python 3.7）** 上运行的 `Architecture: all` `.deb`。

## 目录导航

| 文件 | 内容 |
|---|---|
| `SKILL.md` | 技能入口：四阶段工作流与决策门禁 |
| `references/compatibility-matrix.md` | 为什么 pip 装 Qt 的路线全部走不通（实测数据） |
| `references/migration-guide.md` | PyQt6→PyQt5 枚举全表、Python 3.7 语法红线 |
| `references/build-and-deploy.md` | 端到端构建命令、Debian 10 EOL 改源、deb 规范 |
| `references/troubleshooting.md` | 症状 → 根因 → 修复 |
| `scripts/` | 5 个可直接运行的脚本（迁移 / 检查 / 构建 / 自检 / 改源） |
| `templates/` | control、启动器、desktop、sys.path 引导、配置示例 |
| `assets/icon-512.png` | 技能市场 512×512 展示图标 |

仓库根目录另有 `README.md`（完整中文说明）、`docs/PUBLISH.md`（技能市场上架教程）、`examples/hello-pyqt5/`（可运行示例）。

## 最短使用路径

1. 目标机跑 `sh scripts/preflight_uos.sh`，确认 aarch64 / glibc 2.28 / Python 3.7 / `python3-pyqt5` 可用。
2. 源码副本上跑 `python3 scripts/migrate_pyqt6_to_pyqt5.py <src> --dry-run`，复核后 `--apply --backup`。
3. `python3 scripts/check_py37_compat.py <src>` 必须零 ERROR。
4. `python3 -m pip install --target=<src>/third_party openpyxl==3.1.2`（按项目依赖调整）。
5. `python3 scripts/build_deb.py --src <src> --pkg my-app --entry main.py --out ./dist --inject-bootstrap`。
6. 目标机 `sudo apt install -y python3-pyqt5` → `sudo dpkg -i my-app_1.0.0_all.deb` → `sudo apt install -f`。

## 一句话原理

不捆绑任何 Qt 二进制，运行时依赖发行版自己编译的 `python3-pyqt5`；包内全是文本与 `.py`，因此架构无关、不受构建机 glibc 影响。

版本、许可证与反馈方式见仓库根 `README.md` / `LICENSE`。
