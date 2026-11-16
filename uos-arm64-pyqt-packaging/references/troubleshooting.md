# 排错速查：症状 → 根因 → 修复

按出现阶段分组。每条都给出**可复制的验证命令**，先确认再改，避免盲目重装。

## A. 目标机启动阶段

| 症状 | 根因 | 修复 / 验证 |
|---|---|---|
| `libm.so.6: version 'GLIBC_2.29' not found` | 包里混进了 PyQt6/PySide6 的 Qt `.so`，或目标机 `site-packages` 有残留 wheel | `dpkg-deb -c <deb> \| grep '\.so'` 应无输出；`find /usr/lib/python3/dist-packages -name 'PyQt6*'` 清理残留；严格走 PyQt5 系统库方案 |
| `ImportError: No module named 'PyQt5'` | 目标机未装系统 PyQt5 | `sudo apt install -y python3-pyqt5` 后 `sudo apt install -f`；`python3 -c 'import PyQt5.QtCore; print(PYQT_VERSION_STR)'` 验证 |
| `SyntaxError: invalid syntax` | 用了 3.8+ 语法（`:=`、`f"{x=}"`、`match`、仅位置参数） | `python3 scripts/check_py37_compat.py <src>` 定位文件行号；按 `migration-guide.md` 降级 |
| `TypeError: 'type' object is not subscriptable` | 运行时位置出现 `list[str]` / `dict[str, int]` | 全部移到注解位置；确认文件顶部有 `from __future__ import annotations` |
| `TypeError: unsupported operand type(s) for \|` | 运行时位置出现 `X \| None` | 同上；注解位置安全 |
| `AttributeError: type object 'Qt' has no attribute 'ItemFlag'` | 源码仍是 PyQt6 作用域枚举 | `python3 scripts/migrate_pyqt6_to_pyqt5.py <src> --apply --backup` |
| `AttributeError: 'QApplication' object has no attribute 'exec'` | 老 PyQt5 只有 `exec_()` | 全局替换 `.exec(` → `.exec_(` |
| `ModuleNotFoundError: No module named 'openpyxl'` | 未内置依赖或 sys.path 引导位置不对 | 确认 `/usr/share/<pkg>/third_party/openpyxl` 存在，且入口文件**任何业务 import 之前**插入 `templates/bootstrap.py.tpl` |
| `ModuleNotFoundError: No module named 'et_xmlfile'` | 手工拷 openpyxl 时漏了它的依赖 | 用 `pip install --target=third_party openpyxl==3.1.2` 重新生成，或补装 `et-xmlfile` |
| 中文显示成方块 | 缺中文字体 | `sudo apt install -y fonts-noto-cjk`；`fc-list :lang=zh \| head` 验证 |
| 双击图标无反应，终端能跑 | UOS 未开开发者模式 / 安全策略拦截 / desktop 文件 `Exec` 路径错 | 终端执行 `<pkg>` 看真实报错；`cat /usr/share/applications/<pkg>.desktop` 检查 `Exec=/usr/bin/<pkg>`、`Terminal=false`；在系统设置开启开发者模式 |
| 图标启动后立刻闪退 | 工作目录不是程序目录，代码用了相对路径读写 | 启动器 `cd` 到程序目录，或代码一律用 `__file__` 推导路径 |
| `QXcbConnection: Could not connect to display` | 通过 SSH/无桌面会话启动 | 在图形会话内执行；`echo $DISPLAY` 应非空 |

## B. 构建机阶段

| 症状 | 根因 | 修复 |
|---|---|---|
| `apt update` 满屏 404 | Debian 10 EOL，源仍指向 deb.debian.org / buster-updates | `sudo sh scripts/fix_debian10_sources.sh`；或按 `build-and-deploy.md` 第 2 节手工改源 |
| `Release file ... is not valid yet` / `expired` | archive.debian.org 的 Release 过期 | `apt-get -o Acquire::Check-Valid-Until=false update` |
| `dpkg-deb: command not found` | 未装 dpkg-dev | `sudo apt install -y dpkg-dev` |
| Windows 上构建脚本报「未找到 dpkg-deb」 | 正常降级行为 | 用 `--staging-only` 生成 staging，传 Linux 后 `dpkg-deb --build` |
| `dpkg-deb: control file has bad permissions` | `DEBIAN/` 或 control 权限不对 | `chmod 755 <staging>/DEBIAN; chmod 644 <staging>/DEBIAN/control` |
| `dpkg-deb` 警告文件属主非 root | 普通用户构建 | 加 `--root-owner-group` |
| 生成的 deb 体积异常大 | 误把 `.git/`、`__pycache__/`、`.venv/` 或 `.so` 打进包 | 构建脚本默认排除；检查 `dpkg-deb -c <deb>` 逐项确认 |
| `pip` 拉到不兼容 3.7 的新版依赖 | 未锁版本 | 全部显式锁版本，如 `openpyxl==3.1.2`；`pip install --target` 后核对各包 `requires_python` |

## C. 安装 / 依赖阶段

| 症状 | 根因 | 修复 |
|---|---|---|
| `dpkg: dependency problems prevent configuration` | 缺 `python3-pyqt5` | `sudo apt install -f`（会自动装 Depends）；仍失败则检查软件源 |
| `E: Unable to locate package python3-pyqt5` | 目标机软件源未配置/未联网/未开开发者模式 | 配置可用源后 `apt update`；**这是外部前提，无解时不要继续** |
| `dpkg: error processing archive ... trying to overwrite` | 同包名被其他来源安装过 | `sudo dpkg -r <pkg>` 后重装；或递增版本升级 |
| `Architecture: all` 却提示架构不符 | control 被模板改写 | `dpkg-deb -I <deb> \| grep Architecture` 应为 `all` |

## D. 迁移脚本相关

| 症状 | 根因 | 修复 |
|---|---|---|
| 自定义类的 `Foo.StandardButton.X` 被误改 | 作用域白名单机械匹配 | 用 `--dry-run` 复核，给该文件加 `--exclude`，手工改回 |
| `from __future__ import annotations` 被插到 docstring 之前 | 旧版手工插入 | 脚本用 AST 定位，自动版不会；手工修正为 docstring 之后 |
| `SyntaxError: from __future__ imports must occur at the beginning of the file` | 前面有业务 import | 移到所有业务 import 之前（shebang / 编码声明 / 注释 / docstring 之后） |
| 迁移后枚举仍报错 | 作用域白名单未覆盖自定义枚举 | 按 `migration-guide.md` 表格手工补一条，并考虑给技能提 PR 扩充白名单 |

## E. 一键诊断命令

```sh
# 目标机
python3 --version; uname -m; ldd --version | head -1
python3 -c 'import PyQt5.QtCore as c; print("PyQt5 OK", c.PYQT_VERSION_STR)'
dpkg-deb -I ./<pkg>.deb | grep -E 'Package|Version|Architecture|Depends'
dpkg-deb -c ./<pkg>.deb | grep -E '\.so|\.pyc|\.git/' || echo 'no binaries/pycache/git in package'
sh scripts/preflight_uos.sh
python3 scripts/check_py37_compat.py /usr/share/<pkg>
```

仍无法定位时，把 `preflight_uos.sh` 输出、完整 Traceback、`dpkg-deb -I/-c` 结果一起收集，向技能仓库提 Issue。
