# hello-pyqt5 示例

两个文件演示同一程序在迁移前 / 迁移后的形态：

| 文件 | 用途 |
|---|---|
| `main_pyqt6.py` | 迁移**前**：PyQt6 导入、`Qt.AlignmentFlag.AlignCenter`、`QMessageBox.StandardButton.Ok`、`app.exec()` |
| `main_pyqt5.py` | 迁移**后**：PyQt5 导入 + 扁平枚举 + `exec_()` + `from __future__ import annotations` + sys.path 引导 |

## 亲手跑一遍（Windows / macOS / Linux 均可）

```bash
mkdir -p /tmp/demo && cp main_pyqt6.py /tmp/demo/main.py
python3 ../../uos-arm64-pyqt-packaging/scripts/migrate_pyqt6_to_pyqt5.py /tmp/demo --dry-run
python3 ../../uos-arm64-pyqt-packaging/scripts/migrate_pyqt6_to_pyqt5.py /tmp/demo --apply --backup
python3 ../../uos-arm64-pyqt-packaging/scripts/check_py37_compat.py /tmp/demo
# 对比 /tmp/demo/main.py 与 main_pyqt5.py，应只有引导片段与注解的差别
python3 ../../uos-arm64-pyqt-packaging/scripts/build_deb.py \
  --src /tmp/demo --pkg hello-pyqt5 --version 1.0.0 \
  --entry main.py --app-name "Hello PyQt5" --out /tmp/demo-dist \
  --inject-bootstrap
```

在有 `dpkg-deb` 的 Linux 上会直接产出 `hello-pyqt5_1.0.0_all.deb`；其他平台会在 `/tmp/demo-dist/_staging_hello-pyqt5/` 生成 staging，传到 Linux 后一行命令完成打包。

## 在 UOS 20 arm64 上运行

```bash
sudo apt install -y python3-pyqt5 fonts-noto-cjk
sudo dpkg -i hello-pyqt5_1.0.0_all.deb
sudo apt install -f
hello-pyqt5
```
