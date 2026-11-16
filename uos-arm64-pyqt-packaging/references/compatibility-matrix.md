# 兼容性矩阵与技术选型依据

> 本文档是「为什么不走别的路线」的证据页。数据来自 2026-10 ~ 2026-11 在统信 UOS 20 arm64 实机 + 阿里云 Debian 10.13 arm64 构建机上的实测，以及 PyPI 官方元数据核对。版本会变化，遇到新 wheel 时按本文方法重新验证，不要凭经验外推。

## 1. 目标机硬约束

| 项 | UOS 20 (arm64) 实测值 | 带来的约束 |
|---|---|---|
| 内核 | 4.19.0-arm64-desktop | 构建机可用更新内核，产物不绑定内核 |
| CPU 架构 | aarch64 | x86_64 的 wheel / ELF 一律不可用 |
| glibc | **2.28** | 任何依赖 `GLIBC_2.29` 及以上符号的 `.so` 都无法加载 |
| 系统 Python | **3.7.x** | 源码不得使用 3.8+ 语法与 3.8+ 标准库 API |
| 包管理 | apt / dpkg（Debian 10 系） | 优先交付 `.deb`，依赖关系可声明、可 `apt install -f` 补齐 |
| Qt 可用来源 | 发行版仓库 `python3-pyqt5` | 由发行版针对本机 glibc 自编译，零兼容风险 |

glibc 是**双向约束**：构建/运行环境要 ≥2.28 才装得上部分新 wheel，又要 ≤2.28 才能在 UOS 上跑。这个「夹缝」决定了不能靠升级构建环境绕过。

## 2. 四条被验证走不通的路线

| 路线 | 失败现象 | 根因 |
|---|---|---|
| PyQt6 pip wheel（aarch64） | `libm.so.6: version 'GLIBC_2.29' not found` | wheel 标签写 `manylinux_2_28`，但内部 Qt 库实际链接 2.29 符号，标签失准 |
| PySide6 6.7.3 aarch64 | 导入失败 / 要求更高 glibc | wheel 为 `manylinux_2_31`，需 glibc 2.31 |
| PyQt6 ≤6.6 / PyQt5-Qt5 pip wheel | `No matching distribution found` | 官方未提供 aarch64 Linux wheel（截至实测时间） |
| 把 Windows / x86_64 的 Qt `.so` 拷过去 | `wrong ELF class` / `cannot open shared object` | 架构不符 |

**结论**：在 UOS 20 arm64 上，「pip 装 Qt 绑定 + 捆绑 Qt 运行库」整体不可行。唯一可靠来源是**发行版自己的 `python3-pyqt5`**。

> ⚠️ 上述为实测记录，不是对所有版本的永久断言。Qt / Riverbank 后续可能发布真正兼容 glibc 2.28 的 aarch64 wheel。若目标环境 glibc ≥2.29，或出现新 wheel，用第 4 节的方法重新核验后再切换路线。

## 3. 推荐路线及代价

| 维度 | 推荐方案 | 代价 |
|---|---|---|
| GUI 绑定 | 源码降级到 PyQt5，运行时用系统 `python3-pyqt5` | 需要改源码（枚举展平、`exec_()`）；放弃 Qt6 新 API |
| 纯 Python 依赖 | `pip install --target=third_party` 内置 + `sys.path` 引导 | 包体积增大；升级依赖要重新打包 |
| 分发格式 | `Architecture: all` 的 `.deb` | 目标机必须能装 `python3-pyqt5`（外部前提） |
| 构建机 | 任意 Linux（Debian 10.13 arm64 已验证）；Windows 上只生成 staging | 需要 `dpkg-deb`（Debian/Ubuntu 自带） |

**为什么 `arch:all` 是关键**：包里全是 `.py` 与文本，没有任何 ELF，因此构建机架构无关，也不受构建机 glibc 影响。这从根上消除了交叉编译、sysroot、Qt 插件路径等一整类问题。

## 4. 自行复核 wheel 是否可用（换版本时照做）

在**目标机或同 glibc 环境**上：

```bash
python3 -m pip download --only-binary=:all: --platform manylinux_2_28_aarch64 PyQt6 -d /tmp/whl
cd /tmp/whl && unzip -o *.whl -d unpacked
# 检查所有 .so 需要的最高 glibc 符号版本
find unpacked -name '*.so*' -print0 \
  | xargs -0 -I{} sh -c 'objdump -T "{}" 2>/dev/null | grep -o "GLIBC_[0-9.]*"' \
  | sort -Vu | tail -5
# 出现 GLIBC_2.29 或更高 → 在 UOS 20 上必崩
```

同时确认 wheel 标签与内部实现一致（本技能记录的事故正是「标签 manylinux_2_28、内部要 2.29」）。

## 5. 依赖版本核对表

| 依赖 | 锁定版本 | 依据 |
|---|---|---|
| openpyxl | **3.1.2** | PyPI 元数据 `requires_python: >=3.6`，分类器含 `Python :: 3.7`；3.1.x 后续版本可能抬高下限，故锁定 |
| et-xmlfile | 随 openpyxl 自动解析 | openpyxl 3.1.2 的 `requires_dist` 含 `et-xmlfile`，手工拷贝 `third_party/` 时**必须一并带上** |
| PyQt5 | 由目标机 apt 决定 | 不写入 `third_party/`，不声明 pip 版本 |
| Python | 3.7（目标机） | 构建机可用 3.8+ 跑脚本，但产物源码必须兼容 3.7 |

## 6. 与其他发行版的适配边界

| 环境 | 是否适用 | 说明 |
|---|---|---|
| 统信 UOS 20 arm64 | ✅ 完整适用 | 本技能主目标 |
| Deepin 20 / 麒麟 V10 arm64（glibc 2.28） | ✅ 基本适用 | 先跑 `preflight_uos.sh`，确认包名 `python3-pyqt5` 存在 |
| glibc ≥ 2.31 的 arm64 发行版 | ⚠️ 方案仍可用但非最优 | 可直接考虑 PySide6/PyQt6 wheel 路线 |
| x86_64 UOS | ❌ 不适用 | 无 glibc 夹缝，常规 PyInstaller / pip 方案更简单 |
| 需要 Qt6 专属 API 的项目 | ❌ 不适用 | 源码必须能降级到 PyQt5，否则需自行交叉编译 Qt5/Qt6 |
