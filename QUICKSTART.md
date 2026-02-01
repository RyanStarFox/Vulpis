# 🚀 Vulpis 快速上手指南 (Quick Start)

欢迎使用 Vulpis！本指南将帮助您快速运行和配置本软件。请根据您的需求选择运行方式。

## 目录

- [方式一：通过桌面客户端运行 (推荐用户)](#方式一通过桌面客户端运行-推荐用户)
- [方式二：通过源码运行 (推荐开发者)](#方式二通过源码运行-推荐开发者)
- [配置说明](#配置说明)

---

## 方式一：通过桌面客户端运行 (推荐用户)

这是最简单的使用方式，无需配置 Python 环境，下载解压即用。

### 1. 下载

前往本项目的 [Releases 页面](../../releases) 下载适配您系统的最新版本：

- **Windows**: 下载 `.exe` 安装包
- **macOS**: 下载 `.dmg` 镜像文件

### 2. 安装与启动

- **Windows**: 双击安装包，跟随指引完成安装。并在桌面或开始菜单中找到 **Vulpis** 启动。
- **macOS**: 打开 `.dmg` 文件，将 Vulpis 图标拖入 `Applications` 文件夹，在启动台打开即可。
  - _注意：首次打开如提示"无法验证开发者"，请前往 `系统设置 > 隐私与安全性`，在下方点击 `仍要打开`，或者在终端中运行代码 `sudo xattr -d com.apple.quarantine /Applications/Vulpis.app`并按照提示输入密码。_

### 3. 首次配置

软件启动后，您会看到欢迎界面。请点击界面左上角或侧边栏底部的 **"⚙️ 系统设置"** 按钮，参照下方的 [配置说明](#配置说明) 完成初始化。

---

## 方式二：通过源码运行 (推荐开发者)

如果您希望修改代码、调试功能，或者在 Linux 服务器上部署，建议直接运行 Python 源码。

### 1. 环境准备

确保您的系统已安装：

- **Python**: 3.10 或更高版本 (推荐 3.11)
- **Git**

### 2. 获取代码

打开终端或命令行，执行：

```bash
git clone https://github.com/RyanStarFox/CS4314_NLP_Proj2.git
cd CS4314_NLP_Proj2
```

### 3. 安装依赖

建议使用虚拟环境以避免污染全局环境：

```bash
# 创建虚拟环境
python -m venv .venv

# 激活环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 安装核心依赖
pip install -r requirements.txt
```

### 4. 启动应用

执行以下命令启动 Streamlit 服务：

```bash
streamlit run app.py
```

启动成功后，浏览器将自动打开 `http://localhost:8501`。

---

## 配置说明

无论使用哪种方式启动，首次使用都需要配置基础参数。

### 1. API 配置 (必须)

在 **"⚙️ 系统设置"** -> **"🤖 AI模型配置"** 中填入大模型参数。本项目完全兼容 OpenAI 接口格式，支持 GPT-4、通义千问 (Qwen)、智谱 GLM 等。

- **以阿里云百炼/Qwen为例**:
  - **模型名称**: `qwen-plus` 或 `qwen-max`
  - **API Key**: `sk-xxxxxxxx...`
  - **Base URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1`

各个平台请参见官方文档

- [DeepSeek开放平台](https://platform.deepseek.com/)
- [智谱清言开放平台](https://bigmodel.cn)
- [阿里云百炼平台](https://bailian.console.aliyun.com/)
- [MiniMax开放平台](https://platform.minimaxi.com/)
- [Kimi开放平台](https://platform.moonshot.cn)
- [火山引擎](https://www.volcengine.com/)

### 2. 工具配置 (Pandoc)

如果您需要使用 **导出大纲为 PDF 和 DOCX** 的功能，需要系统安装 [Pandoc](https://pandoc.org/installing.html)。

1. 安装 Pandoc 后，进入设置页面的 **"🛠️ 工具配置"** 标签。
2. 点击 **"🔍 自动检测"** 按钮。
3. 系统会自动扫描并填入 Pandoc 获取路径。

🎉 **点击底部的 "💾 保存并应用配置"，即可开始使用 Vulpis！**
