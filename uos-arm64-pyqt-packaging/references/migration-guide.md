# 源码迁移指南：PyQt6 → PyQt5 + Python 3.7

配套脚本：`scripts/migrate_pyqt6_to_pyqt5.py`（机械替换）、`scripts/check_py37_compat.py`（静态门禁）。**脚本只负责能安全自动化的部分，人工复核清单在第 4 节。**

## 1. 导入替换

| PyQt6 | PyQt5 |
|---|---|
| `from PyQt6.QtWidgets import ...` | `from PyQt5.QtWidgets import ...` |
| `from PyQt6.QtCore import ...` | `from PyQt5.QtCore import ...` |
| `from PyQt6.QtGui import ...` | `from PyQt5.QtGui import ...` |
| `import PyQt6.xxx` | `import PyQt5.xxx` |

模块名基本一致（QtWidgets / QtCore / QtGui / QtSvg / QtNetwork / uic）。少数 Qt6 才有的模块（如 `QtOpenGLWidgets`）在 PyQt5 中不存在，需改用 `QtWidgets.QOpenGLWidget`。

## 2. 枚举展平（PyQt6 作用域枚举 → PyQt5 扁平枚举）

PyQt6 把枚举收进作用域类，PyQt5 是扁平的。完整映射规则：`<前缀>.<Scope>.<成员>` → `<前缀>.<成员>`。

| PyQt6 写法 | PyQt5 写法 |
|---|---|
| `Qt.ItemFlag.ItemIsEnabled` | `Qt.ItemIsEnabled` |
| `Qt.ItemDataRole.DisplayRole` | `Qt.DisplayRole` |
| `Qt.CheckState.Checked` | `Qt.Checked` |
| `Qt.AlignmentFlag.AlignCenter` | `Qt.AlignCenter` |
| `Qt.ContextMenuPolicy.CustomContextMenu` | `Qt.CustomContextMenu` |
| `Qt.GlobalColor.white` | `Qt.white` |
| `Qt.Orientation.Horizontal` | `Qt.Horizontal` |
| `Qt.WindowType.Window` | `Qt.Window` |
| `Qt.KeyboardModifier.ControlModifier` | `Qt.ControlModifier` |
| `Qt.MouseButton.LeftButton` | `Qt.LeftButton` |
| `Qt.DropAction.CopyAction` | `Qt.CopyAction` |
| `Qt.SortOrder.AscendingOrder` | `Qt.AscendingOrder` |
| `Qt.FocusPolicy.StrongFocus` | `Qt.StrongFocus` |
| `Qt.CursorShape.PointingHandCursor` | `Qt.PointingHandCursor` |
| `QDialogButtonBox.StandardButton.Ok` | `QDialogButtonBox.Ok` |
| `QMessageBox.StandardButton.Yes` | `QMessageBox.Yes` |
| `QMessageBox.Icon.Warning` | `QMessageBox.Warning` |
| `QAbstractItemView.SelectionBehavior.SelectRows` | `QAbstractItemView.SelectRows` |
| `QAbstractItemView.EditTrigger.NoEditTriggers` | `QAbstractItemView.NoEditTriggers` |
| `QDir.Filter.Files` | `QDir.Files` |
| `dialog.DialogCode.Accepted` | `dialog.Accepted` |

脚本内置的作用域白名单覆盖：`ItemFlag`、`ItemDataRole`、`CheckState`、`ContextMenuPolicy`、`AlignmentFlag`、`GlobalColor`、`Orientation`、`WindowType`、`KeyboardModifier`、`MouseButton`、`DropAction`、`ToolBarArea`、`CursorShape`、`TextInteractionFlag`、`FocusPolicy`、`AspectRatioMode`、`TransformationMode`、`ConnectionType`、`ApplicationAttribute`、`WidgetAttribute`、`StandardButton`、`DialogCode`、`SelectionBehavior`、`EditTrigger`、`Filter`、`ButtonRole`、`Icon`、`MoveMode`、`SortOrder`、`Axis`、`ItemType`、`State`、`Shadow`、`Shape`、`ColorRole`、`Key`、`ShortcutContext`、`ToolButtonStyle`、`ScrollBarPolicy`、`TabPosition`、`TabShape`。

> 自定义类若恰好有同名属性（如自己写的 `Foo.StandardButton.Ok`），可能被误替换。务必用 `--dry-run` 报告逐行复核，必要时用 `--exclude` 跳过该文件。

## 3. 其他 API 差异

| 项 | PyQt6 | PyQt5 / 3.7 写法 |
|---|---|---|
| 事件循环 | `app.exec()` | `app.exec_()` |
| 菜单/对话框弹出 | `menu.exec(pos)` | `menu.exec_(pos)` |
| 高 DPI | Qt6 默认开启 | 需要时手动 `QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)`（须在实例化前） |
| `QAction` | `QtGui.QAction`（Qt6） | `QtWidgets.QAction`（Qt5）；按实际导入调整 |
| `QDesktopWidget` | 移除 | Qt5 仍可用 `QDesktopWidget` / `QApplication.primaryScreen()` |
| 枚举比较 | 强类型 `QMessageBox.StandardButton.Ok` | 直接 `== QMessageBox.Ok` |
| 信号重载 | 需 `signal[type]` 选择 | 同样支持 `signal[type]`，但注意老版本写法差异 |

## 4. Python 3.7 语法红线

### 4.1 必须加 `from __future__ import annotations`

每个含类型注解的 `.py` 都要加，且必须在 **docstring 之后、其他 import 之前**：

```python
"""模块说明。"""
from __future__ import annotations

import os
from PyQt5.QtWidgets import QWidget
```

加上后，注解变成惰性字符串，3.7 永不在运行时求值，于是这些写法在**注解位置**是安全的：

```python
def f(items: list[str]) -> dict[str, int] | None: ...
self.data: list[str] = []
@dataclass
class Cfg:
    path: str | None = None
```

### 4.2 绝对禁止（运行时位置会立即崩）

```python
isinstance(x, list[str])        # TypeError: 'type' object is not subscriptable
cast(list[str], x)
Alias = list[str]
x: list[str] = []               # ✅ 注解，安全
def g() -> tuple[int, ...]: ...  # ✅ 注解，安全
```

`check_py37_compat.py` 会用 AST 判断每个 `Subscript` / `BinOp(BitOr)` 是否位于注解子树内，只在运行时位置报错。

### 4.3 3.8+ 语法 / API（3.7 直接不支持）

| 类别 | 例子 | 3.7 替代 |
|---|---|---|
| 海象运算符 | `if (n := len(x)) > 3:` | 拆成两行 |
| f-string 调试 | `f"{x=}"` | `f"x={x}"` |
| 仅位置参数 | `def f(a, /, b):` | 去掉 `/` |
| 结构模式匹配 | `match x:` | `if/elif` |
| `functools.cached_property` | 3.8+ | 手写缓存或 `@property` |
| `math.prod` / `math.isqrt` | 3.8+ | `reduce(operator.mul, ...)` |
| `typing.Protocol` / `Literal` / `Final` | 3.8+ | `typing_extensions`（需一并内置） |
| `importlib.metadata` | 3.8+ | `pkg_resources` / 手工读文件 |
| `asyncio.to_thread` / `zoneinfo` | 3.9+ / 3.9+ | `run_in_executor` / `pytz` |

### 4.4 dataclass 特别提示

`@dataclass`（3.7 起可用）会读取 `__annotations__`；有了 `from __future__ import annotations` 后拿到的是字符串，dataclass 只关心键名，不解析类型，因此安全。**但 `from __future__` 必须写在 `@dataclass` 定义之前**（脚本会插到正确位置）。

## 5. sys.path 引导（内置依赖）

入口文件最顶部插入（模板 `templates/bootstrap.py.tpl`）：

```python
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _HERE)
_sys.path.insert(0, _os.path.join(_HERE, "third_party"))
```

要点：
- 必须在**任何业务 import 之前**，尤其是 `import openpyxl` / `from PyQt5...` 之前；
- `third_party` 优先级最高，避免目标机上同名旧包抢先被导入；
- 用 `__file__` 计算路径，不要写绝对路径（安装后是 `/usr/share/<pkg>/`）。

## 6. 人工复核清单（脚本跑完后逐项打勾）

- [ ] `--dry-run` 报告中的每一处枚举替换都符合预期，无自定义类被误伤
- [ ] 所有 `list[X]` / `X | None` 只在注解位置
- [ ] 每个含注解的 `.py`（含 dataclass 文件）都有 `from __future__ import annotations`
- [ ] 无 `:=` / `f"{x=}"` / `/` 位置参数 / `match`
- [ ] 无 3.8+ 标准库 API
- [ ] `QAction` 等跨模块类导入正确
- [ ] 入口文件有 sys.path 引导，且 `third_party/` 内含 `openpyxl` **与 `et_xmlfile`**
- [ ] `check_py37_compat.py` 退出码为 0
- [ ] 在 3.7 环境（或 `python3.7 -m compileall`）实际编译通过
