# 🐦 zsh-mockingbird

> 一个会**阴阳怪气地嘲讽你敲错命令**的 Zsh 插件。
> 当你手滑把 `ls` 敲成 `sl`、把 `git` 敲成 `got` 时，它会调用大模型 API，以极度毒舌但又充满技术幽默感的口吻怼你一句，并顺手把正确的命令甩给你。

![Zsh](https://img.shields.io/badge/shell-Zsh-blue) ![Python](https://img.shields.io/badge/python-3.6%2B-green) ![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## ✨ 特性

- 🧠 **AI 嘲讽**：兼容 OpenAI 格式的 LLM API（DeepSeek / 阿里云百炼 Qwen / Moonshot 等均可）
- 🗣️ **三种人设**：`sarcastic` 阴阳怪气（默认）/ `angry` 祖安暴躁 / `tsundere` 傲娇
- ⚡ **零阻塞**：默认后台异步执行，嘲讽稍后送达，绝不卡住你的终端
- 🚫 **零依赖**：`mock.py` 仅用 Python 3 标准库（`urllib.request`），**不需要** `pip install openai`
- 🔒 **永不报错**：请求超时（默认 3 秒）/ 断网 / 未配置 Key 时，静默回退到本地 5 条毒舌语录
- 🎨 **彩色渲染**：ANSI 转义码输出（红色标头 + 黄色正文 + 青色建议）
- 📦 **即插即用**：直接放进 Oh My Zsh `custom/plugins` 即可加载

---

## 🏗️ 工作原理

```
[你在 Zsh 敲错命令]
        │
        ▼
[触发 Zsh 钩子: command_not_found_handler]
        │
        ▼
[后台异步调用 mock.py（不阻塞终端）]
        │
        ├── 1. 传入：错误命令、参数、当前目录
        ├── 2. 发起 OpenAI 兼容 HTTP POST（3 秒超时 / 可选 SSE 流式）
        └── 3. System Prompt 约束"阴阳怪气"人设
        │
        ▼
[彩色渲染：红色标头 + 毒舌回复 + 青色命令建议]
```

---

## 📁 项目结构

```text
zsh-mockingbird/
├── zsh-mockingbird.plugin.zsh   # Zsh 插件主入口（重写 command_not_found_handler）
├── mock.py                      # 核心脚本：API 请求 + 终端渲染 + 本地兜底
├── config.env.example           # 配置文件模板（复制为 config.env 使用）
└── README.md                    # 本说明文档
```

---

## 🚀 安装

> 插件**不会**自动改动你的 `~/.zshrc`，装好之后由你自己手动加入 `plugins=()`，一切尽在掌握。

### 方式一：git clone 安装（推荐，Oh My Zsh）

直接克隆到自定义插件目录：

```bash
git clone https://github.com/WenAnrong/zsh-mockingbird.git \
  ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-mockingbird
```

然后编辑 `~/.zshrc`，在 `plugins=(...)` 数组中手动加入 `zsh-mockingbird`：

```zsh
plugins=(... zsh-mockingbird)
```

最后使配置生效：

```bash
source ~/.zshrc
```

### 方式二：手动拷贝文件（没有 git 环境）

```bash
mkdir -p ~/.oh-my-zsh/custom/plugins/zsh-mockingbird
cp zsh-mockingbird.plugin.zsh mock.py config.env.example ~/.oh-my-zsh/custom/plugins/zsh-mockingbird/
```

然后同上，在 `~/.zshrc` 的 `plugins=(...)` 中加入 `zsh-mockingbird`，再 `source ~/.zshrc`。

### 方式三：手动 source（不使用 Oh My Zsh）

把仓库放到任意位置，在 `~/.zshrc` 末尾追加：

```zsh
source /path/to/zsh-mockingbird/zsh-mockingbird.plugin.zsh
```

`/path/to` 请替换为你实际的路径。

---

## ⚙️ 配置

首次使用，先在插件目录里基于模板生成 `config.env` 并填写：

```bash
cd ~/.oh-my-zsh/custom/plugins/zsh-mockingbird
cp config.env.example config.env
vim config.env
```

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `MOCKINGBIRD_API_KEY` | ✅ | （空） | 大模型 API Key（OpenAI 兼容格式） |
| `MOCKINGBIRD_BASE_URL` | ❌ | `https://api.deepseek.com` | API 地址，会自动拼接 `/chat/completions` |
| `MOCKINGBIRD_MODEL` | ❌ | `deepseek-chat` | 模型名称 |
| `MOCKINGBIRD_TONE` | ❌ | `sarcastic` | 人设：`sarcastic` / `angry` / `tsundere` |
| `MOCKINGBIRD_STREAM` | ❌ | `0` | `1` 开启 SSE 流式输出 |
| `MOCKINGBIRD_TIMEOUT` | ❌ | `3.0` | 请求超时（秒），超过即本地兜底 |

### 各家模型示例

**DeepSeek**

```bash
MOCKINGBIRD_API_KEY="sk-xxxx"
MOCKINGBIRD_BASE_URL="https://api.deepseek.com"
MOCKINGBIRD_MODEL="deepseek-chat"
```

**阿里云百炼（Qwen）**

```bash
MOCKINGBIRD_API_KEY="sk-xxxx"
MOCKINGBIRD_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
MOCKINGBIRD_MODEL="qwen-plus"
```

**Moonshot（Kimi）**

```bash
MOCKINGBIRD_API_KEY="sk-xxxx"
MOCKINGBIRD_BASE_URL="https://api.moonshot.cn/v1"
MOCKINGBIRD_MODEL="moonshot-v1-8k"
```

配置完成后：

```bash
source ~/.zshrc
```

---

## 🎮 使用

装好之后什么都不用做，直接在终端里敲一个不存在的命令：

```bash
$ sl
zsh: command not found: sl
[Mockingbird AI 警告]                    # 红色粗体
`sl` 是什么新命令？你自己发明的吧，反正 Linux 不认识你。   # 黄色
💡 你是不是想输入: ls?                    # 青色
```

> 未配置 API Key / 断网 / 超时的时候，插件会自动输出本地 5 条毒舌语录兜底，所以**永远能跑、永远不会崩**。

### 进阶开关

在 `~/.zshrc` 中（插件加载前）可额外设置：

```zsh
export MOCKINGBIRD_ASYNC=0    # 0 = 同步等待 AI 回复（默认 1 = 后台异步，不阻塞终端）
```

---

## 🧪 常见问题（FAQ）

**Q：不填 API Key 会怎样？**
完全正常使用——`mock.py` 会静默走本地毒舌语录兜底，只是内容固定、没有"个性化嘲讽"。

**Q：`python3` 没装怎么办？**
插件会检测到缺少 `python3` 并直接按原样返回 `zsh: command not found`，不会报错。装上 Python 3 后即可体验。

**Q：终端输出乱码 / 颜色失效？**
请确认终端支持 ANSI 256 色（macOS 自带 Terminal / iTerm2 / VS Code 终端均支持）。

**Q：和别的 `command_not_found_handler` 冲突？**
本插件会覆盖已有处理器。如果同时装了其他同类插件，建议只保留一个。

**Q：不想让嘲讽延迟出现？**
把 `MOCKINGBIRD_ASYNC=0` 即可改为同步模式，AI 回复会先于提示符渲染完成。

---

## 📝 说明

- `mock.py` 仅依赖 Python 3 标准库，零第三方依赖，开箱即用。
- System Prompt 强制约束 AI：**2 句话以内、50 字以内、最后单独一行给出 `💡 你是不是想输入: ...?` 建议**，确保终端阅读体验。
- 请求失败或超时时自动回退本地语录，**绝不阻塞用户终端、绝不抛出异常栈**。

## 📄 License

MIT License
