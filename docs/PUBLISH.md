# 技能市场上架保姆级教程

> 面向 `uos-arm64-pyqt-packaging` v1.0.0。目标：在 **WorkBuddy 开放平台**提交技能，审核通过后出现在客户端「专家·技能·连接器 → 技能市场」，别人点「+」即可安装。
>
> ⚠️ **实名认证、原创声明、提交审核必须由账号本人完成**。本文档把除此之外的所有材料都准备好了，按步骤大约 5 分钟。

---

## 0. 材料清单（本仓库已备齐）

| # | 材料 | 路径 | 状态 |
|---|---|---|---|
| 1 | 开放平台提交用 zip（根目录直铺 `SKILL.md`） | `dist/uos-arm64-pyqt-packaging-openplatform.zip` | ✅ 已生成 |
| 2 | 客户端上传用 zip（带顶层技能目录） | `dist/uos-arm64-pyqt-packaging.zip` | ✅ 已生成（备用） |
| 3 | 512×512 市场图标（约 7 KB，远低于 500 KB 上限） | `uos-arm64-pyqt-packaging/assets/icon-512.png` | ✅ 已生成 |
| 4 | 市场展示文案（中英、示例提示词、分类） | 本文第 3 节，可直接复制 | ✅ |
| 5 | 校验与哈希 | `dist/SHA256SUMS.txt` | ✅ |
| 6 | 开发者实名认证 | 本人：大陆二代身份证 + 实名手机号 + 邮箱 + 人脸核身 | ⬜ 需本人 |

生成/重建材料：

```bash
python3 tools/make_icon.py        # 需要时重新生成图标
python3 tools/make_release.py     # 校验 frontmatter、目录层级、资源引用并重建两种 zip
```

---

## 1. 为什么有两个 zip（务必先看）

| 用途 | 文件 | zip 内结构 |
|---|---|---|
| **开放平台提交审核** | `uos-arm64-pyqt-packaging-openplatform.zip` | `SKILL.md` 在 **zip 根目录**，`references/`、`scripts/`、`templates/`、`assets/` 为根下一级目录 |
| WorkBuddy 客户端「技能 → 添加技能 → 上传技能」 | `uos-arm64-pyqt-packaging.zip` | 顶层包一层 `uos-arm64-pyqt-packaging/` 目录 |

官方开放平台文档展示的是带 `{skill-name}/` 的结构，而部分实操资料要求根目录直铺 `SKILL.md`。两套说法并存，因此本仓库**两个都提供**：

- 提交开放平台时**优先用 `-openplatform.zip`**；
- 若提示「解析失败 / 找不到 SKILL.md」，换另一个 zip 重试（这是最常见、也是最容易自救的失败原因）；
- 两个包的内容完全一致，仅目录层级不同，`tools/make_release.py` 保证同步生成。

技能包内部严格**只有两级目录**（根 + 一级子目录），满足平台目录结构校验。

---

## 2. 提交步骤（照做即可）

### 2.1 开发者认证（只需做一次）

1. 浏览器打开 <https://open.workbuddy.cn>，用你的 WorkBuddy 账号登录。
2. 首次进入选择 **个人认证**（个人主体；企业/组织认证是另外两条路径）。
3. 按页面指引提交：大陆二代身份证、实名手机号、邮箱、人脸核身。
4. 认证通过后进入开放平台首页。

> 个人认证是平台要求，材料只提交给平台，本仓库与技能包内**不含任何个人信息或凭据**。

### 2.2 创建技能

1. 左侧导航 **发布管理 → 技能**。
2. 点击 **发布技能 / 创建技能** → **配置技能**。
3. **上传压缩包**：选 `dist/uos-arm64-pyqt-packaging-openplatform.zip`。
4. 平台自动开包解析并生成技能 ID。解析出的名称、描述等由 `SKILL.md` frontmatter 提供，核对无误后点「继续」。

若解析失败，先按第 5 节自查，再换另一个 zip。

### 2.3 确认信息（文案见第 3 节）

按表单逐项填写：

| 字段 | 填什么 |
|---|---|
| 市场展示名称 | `统信 UOS arm64 PyQt 打包助手` |
| 版本 | `v1.0.0`（与 `SKILL.md` frontmatter 一致） |
| 市场展示分类 | **开发工具**（可加 **效率工具**） |
| 服务类目 | 工具 / 办公、开发工具（以下拉实际选项为准，1~5 个） |
| 头像 | 上传 `uos-arm64-pyqt-packaging/assets/icon-512.png`（512×512，JPG/PNG，≤500 KB） |
| 简介 / 详细描述 | 复制第 3 节文案 |
| 推荐提示词 / 示例 | 复制第 3 节 3 条示例 |

技能市场的 9 个分类为：生活服务、开发工具、投资理财、内容创作、数据分析、效率工具、办公协同、商业运营、知识与学习。本技能最贴切的是 **开发工具**。

### 2.4 提交审核

1. 勾选原创声明（「承诺本内容是本人独立原创」）。
2. 阅读并同意开发者规则 → **提交审核**。
3. 页面提示约 **7 个工作日**出结果（实测常快于此时长），结果通过站内通知告知。
4. 审核通过后自动上架技能市场；之后在客户端搜索技能名即可安装。

> 提交前请确认已阅读第 4 节审核自查清单。提交后如需修改，**必须递增 `version`** 并重新打包上传（`python3 tools/make_release.py`）。

---

## 3. 可直接复制的展示文案

### 中文简介（一句话）

> 把 PyQt / 纯 Python 桌面应用打包成可在统信 UOS 20 arm64（glibc 2.28）上运行的 deb 安装包，自动完成 PyQt6→PyQt5 迁移、Python 3.7 兼容检查与 arch:all 构建。

### 详细描述（市场详情页）

```
面向国产 arm64 桌面系统的 Python GUI 打包流水线。

统信 UOS 20 的 glibc 停在 2.28，PyQt6 / PySide6 的 aarch64 官方 wheel 要么不存在，
要么内部 Qt 实际链接 GLIBC_2.29，装上去必然报 libm.so.6: version `GLIBC_2.29' not found。
本技能给出经过实机验证的稳定路线：源码降级到 PyQt5 并兼容系统 Python 3.7，
纯 Python 依赖内置 third_party，构建 Architecture: all 的 .deb，
运行时由发行版自编译的 python3-pyqt5 提供 Qt。

内置 5 个可直接运行的脚本（源码迁移、3.7 兼容门禁、deb 构建、目标机自检、Debian 10 改源）、
4 份参考文档（兼容矩阵、迁移指南、构建部署、排错速查）与可复制模板，
既是 WorkBuddy 技能，也能脱离 AI 当命令行工具用。
```

### 英文简介

> End-to-end workflow to package PyQt / Python desktop apps as `Architecture: all` .deb installers for UOS 20 arm64 (glibc 2.28, Python 3.7): PyQt6→PyQt5 migration, static compatibility gate, vendored pure-Python dependencies, build and troubleshooting.

### 3 条示例提示词（中英成对）

| # | 中文 | English |
|---|---|---|
| 1 | 帮我把这个 PyQt6 程序打包成能在统信 UOS 20 arm64 上安装的 deb | Package my PyQt6 app as a .deb for UOS 20 arm64 |
| 2 | UOS 上启动报 GLIBC_2.29 not found，怎么修 | Fix GLIBC_2.29 not found on UOS arm64 |
| 3 | 检查一下这份源码有没有 Python 3.7 跑不了的语法 | Check whether my source is Python 3.7 compatible |

### 标签建议

`UOS` `arm64` `aarch64` `glibc-2.28` `PyQt5` `deb` `国产操作系统` `信创` `Python3.7` `交叉打包`

---

## 4. 审核自查清单（提交前逐项打勾）

- [ ] zip 解压后 `SKILL.md` 在根目录，且 YAML frontmatter 以 `---` 开头
- [ ] frontmatter 含 `name` / `description` / `description_zh` / `description_en` / `examples_zh` / `examples_en` / `version` / `author` / `agent_created`
- [ ] `description` 中无 `<` `>` 尖括号（平台校验会拒）
- [ ] 中英文描述成对，示例提示词成对
- [ ] 版本号语义化 `1.0.0`，每次重新上传都递增
- [ ] 包内仅两级目录，无三级嵌套、无 `.pyc` / `.bak` / `.git` / `__pycache__`
- [ ] `SKILL.md` 引用的 `scripts/` `references/` `templates/` `assets/` 文件全部存在（`make_release.py` 已校验）
- [ ] 图标 512×512 PNG，≤500 KB
- [ ] 包内无硬编码 Token、密钥、内部地址、个人绝对路径
- [ ] 描述直说「用户能完成什么」，不夸大能力；外部前提（`python3-pyqt5`）已写清
- [ ] 原创声明由本人勾选

---

## 5. 解析失败 / 被驳回时怎么自救

| 现象 | 处理 |
|---|---|
| 「解析失败 / 找不到 SKILL.md」 | 换另一个 zip 重试（第 1 节） |
| 「目录层级不合规」 | 确认用的是 `-openplatform.zip`；`tools/make_release.py` 已强制两级目录检查 |
| 「描述含非法字符」 | 检查 `description` 是否有 `<` `>`；改用中文全角括号 |
| 「版本未变更」 | 修改 `SKILL.md` 的 `version` 并重跑 `make_release.py` |
| 「中英文字段缺失」 | 对照第 4 节 frontmatter 清单补齐 |
| 「图标不合规」 | 用 `assets/icon-512.png`（512×512，PNG，约 7 KB） |
| 仍无法定位 | 邮件 `openworkbuddy@tencent.com`，附 zip、`SHA256SUMS.txt` 与平台报错截图 |

---

## 6. 关于付费发布（可选，本次未启用）

平台支持一次性买断 / 按月订阅两种付费方式，但需要先满足三个条件：**已完成开发者认证、账号无违规记录、至少有 1 个审核通过的技能或专家**。满足后在「收入变现」开通收款账户、微信签约，重新发布时才能开启付费。

本次提交按**免费**发布。若后续想改付费，注意：**付费方式一经上架不可更改**，且需重新走一次版本递增与审核。

---

## 7. 时间线与后续维护

| 阶段 | 预期 |
|---|---|
| 准备材料 | 已完成（`dist/` 内） |
| 个人认证 + 表单提交 | 约 5~15 分钟，本人操作 |
| 平台审核 | 约 7 个工作日，站内通知 |
| 上架后 | 客户端技能市场可搜索安装 |
| 更新技能 | 改内容 → 递增 `version` → `python3 tools/make_release.py` → 重新上传 → 重新审核 |

维护提示：Qt / Riverbank 若后续发布真正兼容 glibc 2.28 的 aarch64 wheel，请先在目标机按 `references/compatibility-matrix.md` 第 4 节复核，再决定是否调整技能结论；不要凭旧经验外推。
