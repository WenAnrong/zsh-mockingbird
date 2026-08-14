# 🐦 zsh-mockingbird

> 一个会**阴阳怪气地嘲讽你敲错命令**的 Zsh 插件。
> 当你手滑把 `ls` 敲成 `sl`、把 `git` 敲成 `got` 时，它会调用大模型 API，以极度毒舌但又充满技术幽默感的口吻怼你一句，并顺手把正确的命令甩给你。

---

## ✨ 特性

- 🧠 **AI 嘲讽**：兼容 OpenAI 格式的 LLM API（DeepSeek / 阿里云百炼 等均可）
- 🗣️ **三种人设**：`sarcastic` 阴阳怪气（默认）/ `angry` 祖安暴躁 / `tsundere` 傲娇
- ⚡ **同步执行**：嘲讽直接出现在提示符之前
- ⏳ **等待转圈**：调用 AI 时显示转圈动画（文案可配置），非 UTF-8 终端自动回退 ASCII
- 🚫 **零依赖**：`mock.py` 仅用 Python 3 标准库（`urllib.request`）
- 🔒 **永不报错**：请求超时（默认 6 秒）/ 断网 / 未配置 Key 时，静默回退到本地 5 条毒舌语录
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
[同步调用 mock.py（嘲讽先于提示符渲染）]
        │
        ├── 1. 传入：错误命令、参数、当前目录
        ├── 2. 发起 OpenAI 兼容 HTTP POST（6 秒超时）
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

### 方式一：git clone 安装（推荐，Oh My Zsh）

确保你已经安装了 [Oh My Zsh](https://github.com/ohmyzsh/ohmyzsh)。

直接克隆到自定义插件目录：

```bash
git clone https://github.com/WenAnrong/zsh-mockingbird.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-mockingbird
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

确保你已经安装了 [Oh My Zsh](https://github.com/ohmyzsh/ohmyzsh)。

```bash
mkdir -p ~/.oh-my-zsh/custom/plugins/zsh-mockingbird

cp zsh-mockingbird.plugin.zsh mock.py config.env.example ~/.oh-my-zsh/custom/plugins/zsh-mockingbird/
```

然后同上，在 `~/.zshrc` 的 `plugins=(...)` 中加入 `zsh-mockingbird`，再 `source ~/.zshrc`。

### 方式三：手动 source（不使用 Oh My Zsh）

普通 Zsh 用户可以直接 source 插件文件。

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
| `MOCKINGBIRD_API_URL` | ✅ | （空） | API 完整地址（必填，脚本不拼接） |
| `MOCKINGBIRD_MODEL` | ✅ |（空） | 模型名称 |
| `MOCKINGBIRD_TONE` | ❌ | `sarcastic` | 人设：`sarcastic` / `angry` / `tsundere` |
| `MOCKINGBIRD_SPINNER` | ❌ | `正在思考怎么嘲讽你...` | 等待 AI 响应时的转圈文案，留空禁用 |
| `MOCKINGBIRD_PAYLOAD` | ❌ | `{"thinking": {"type": "disabled"}}` | 自定义请求体 JSON，合并进 API 请求（可覆盖/新增字段） |
| `MOCKINGBIRD_TIMEOUT` | ❌ | `6.0` | 请求超时（秒），超过即本地兜底 |

配置完成后：

```bash
source ~/.zshrc
```
或者退出终端重新打开。

---

## 🎮 使用

装好之后什么都不用做，直接在终端里敲一个不存在的命令：

```bash
$ sl
[Mockingbird 本地 警告]                  # 未配置 AI 时的红色粗体标头
`sl` 是什么新命令？你自己发明的吧，反正 Linux 不认识你。   # 黄色
💡 你是不是想输入: ls?                    # 青色
```

> 标头会随来源变化：调用大模型成功时显示 `[Mockingbird AI 警告]`，走本地兜底时显示 `[Mockingbird 本地 警告]`。

---

## 🔄 更新插件

### git clone 安装（推荐）

在插件目录里 `git pull` 即可：

```bash
cd ~/.oh-my-zsh/custom/plugins/zsh-mockingbird
git pull
source ~/.zshrc
```

> 本地生成的 `config.env` 已被 `.gitignore` 忽略，`git pull` 不会覆盖你的 API Key 配置。

### 手动拷贝安装

重新把仓库里的插件文件拷到插件目录覆盖旧文件，再 `source ~/.zshrc`：

```bash
cp zsh-mockingbird.plugin.zsh mock.py config.env.example \
  ~/.oh-my-zsh/custom/plugins/zsh-mockingbird/
source ~/.zshrc
```

---

## 🧪 常见问题（FAQ）

**Q：不填 API Key 会怎样？**
完全正常使用——`mock.py` 会静默走本地毒舌语录兜底，只是内容固定、没有"个性化嘲讽"。

**Q：`python3` 没装怎么办？**
插件会检测到缺少 `python3` 并静默返回退出码 `127`（不会打印任何信息）。装上 Python 3 后即可体验。

**Q：终端输出乱码 / 颜色失效？**
请确认终端支持 ANSI 256 色（macOS 自带 Terminal / iTerm2 / VS Code 终端均支持）。

**Q：和别的 `command_not_found_handler` 冲突？**
本插件会覆盖已有处理器。如果同时装了其他同类插件，建议只保留一个。

