#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zsh-mockingbird / mock.py
=========================

当用户在 Zsh 中敲错命令时，由 zsh-mockingbird.plugin.zsh 调用本脚本：

    1. 读取环境变量配置（兼容 OpenAI 格式的 LLM API）。
    2. 带上"阴阳怪气" System Prompt，用 urllib.request 发起 HTTP POST。
    3. 请求超时（默认 3 秒）/ 断网 / 未配置 Key 时，静默回退到本地 5 条毒舌语录。
    4. 用 ANSI 转义码渲染彩色终端输出。

零第三方依赖：仅使用 Python 3 标准库。

用法：
    python3 mock.py <错误的命令> [参数...]
"""

import json
import os
import random
import sys
import urllib.error
import urllib.request

# --------------------------------------------------------------------------
# ANSI 颜色
# --------------------------------------------------------------------------
RESET = "\033[0m"
BOLD_RED = "\033[1;31m"  # 标头：红色粗体
YELLOW = "\033[0;33m"    # AI 回复：黄色
CYAN = "\033[0;36m"      # 建议命令：青色

# --------------------------------------------------------------------------
# 配置读取（环境变量）
# --------------------------------------------------------------------------
def get_env(name, default=None):
    """读取环境变量，空白值视为未设置。"""
    val = os.environ.get(name)
    if val is None:
        return default
    val = val.strip()
    return val if val else default


API_KEY = get_env("MOCKINGBIRD_API_KEY", "")
BASE_URL = get_env("MOCKINGBIRD_BASE_URL", "https://api.deepseek.com").rstrip("/")
MODEL = get_env("MOCKINGBIRD_MODEL", "deepseek-chat")
TONE = get_env("MOCKINGBIRD_TONE", "sarcastic")
STREAM = get_env("MOCKINGBIRD_STREAM", "0") == "1"
try:
    TIMEOUT = float(get_env("MOCKINGBIRD_TIMEOUT", "3.0"))
except (TypeError, ValueError):
    TIMEOUT = 3.0

# --------------------------------------------------------------------------
# System Prompt（按语气风格）
# --------------------------------------------------------------------------
SYSTEM_PROMPTS = {
    "sarcastic": (
        "你是一个运行在 Linux 终端里的 AI 监督者。你的唯一任务是针对用户刚刚敲错的 "
        "Linux 命令进行极度阴阳怪气、刻薄、嘲讽的评价。\n"
        "规则：\n"
        "1. 严禁给予温和的帮助，不要像个客服！要像一个看着实习生敲错代码的资深技术大佬。\n"
        "2. 结合他输入的错误命令（例如把 ls 敲成 sl，把 git 敲成 got），用极具技术幽默感的话嘲讽他。\n"
        "3. 控制在 2 句话以内，字数控制在 50 字以内，适合终端快速阅读。\n"
        "4. 在最后单独换一行，用 `💡 你是不是想输入: <正确命令>?` 的格式给出修正建议。"
    ),
    "angry": (
        "你是一个脾气暴躁、祖安风格的 Linux 终端 AI 监督者。看到用户敲错命令你会血压飙升、直接开喷。\n"
        "规则：\n"
        "1. 用最暴躁、最祖安的话嘲讽，但必须带技术梗，不许只会骂街。\n"
        "2. 结合他输入的错误命令具体嘲讽，别当复读机。\n"
        "3. 控制在 2 句话以内，字数控制在 50 字以内。\n"
        "4. 骂归骂，命令还是得给——最后单独换一行，用 `💡 你是不是想输入: <正确命令>?` 给出正确命令。"
    ),
    "tsundere": (
        "你是一个傲娇的 Linux 终端 AI 监督者。嘴上各种嫌弃用户敲错命令，其实心里想帮他，"
        "最后会口嫌体正直地给出正确命令。\n"
        "规则：\n"
        "1. 用傲娇的语气（比如\"哼\"\"才不是\"\"真拿你没办法\"）嫌弃但关心地吐槽。\n"
        "2. 结合他输入的错误命令具体吐槽。\n"
        "3. 控制在 2 句话以内，字数控制在 50 字以内。\n"
        "4. 最后单独换一行，用 `💡 你是不是想输入: <正确命令>?` 给出正确命令——才不是为了帮你呢！"
    ),
}

# --------------------------------------------------------------------------
# 本地兜底：5 条毒舌语录 + 常见手滑纠错表
# --------------------------------------------------------------------------
COMMON_TYPOS = {
    "sl": "ls",
    "got": "git",
    "gti": "git",
    "dcoker": "docker",
    "dockercompose": "docker-compose",
    "kubectrl": "kubectl",
    "kubelctl": "kubectl",
    "pythno": "python3",
    "pytnon": "python3",
    "pyton": "python3",
    "sduo": "sudo",
    "suod": "sudo",
    "mkidr": "mkdir",
    "mikdir": "mkdir",
    "cd..": "cd ..",
    "gitclnoe": "git clone",
    "gitpul": "git pull",
    "gitpuh": "git push",
}

FALLBACK_QUOTES = [
    "佩服，能把 `{cmd}` 敲成这样也是一种天赋，建议去隔壁学学打字。",
    "`{cmd}` 是什么新命令？你自己发明的吧，反正 Linux 不认识你。",
    "手滑程度堪比在婚礼上喊出前任的名字，冷静点，重来。",
    "这台终端从未出现过 `{cmd}`，以后也不会有。建议先 man 一下自己的脑子。",
    "`{cmd}` —— 系统查无此令。你确定不是来砸场子的？",
]


def build_user_prompt(cmd, args, cwd):
    """构造给模型看的用户消息。"""
    lines = ["用户刚才敲错了一条命令，请按 System Prompt 的要求嘲讽并给出建议。"]
    lines.append("错误命令: " + cmd)
    if args:
        lines.append("完整命令: " + " ".join([cmd] + args))
    if cwd:
        lines.append("当前目录: " + cwd)
    return "\n".join(lines)


def call_api(messages):
    """发起 OpenAI 兼容的 /chat/completions 请求，返回回复文本。"""
    url = BASE_URL + "/chat/completions"
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": STREAM,
        "temperature": 0.9,
        "max_tokens": 200,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        if STREAM:
            return _parse_stream(resp)
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def _parse_stream(resp):
    """解析 SSE 流式响应（data: ... 行），合并为完整文本。"""
    parts = []
    for raw in resp:
        line = raw.decode("utf-8", errors="ignore").strip()
        if not line.startswith("data:"):
            continue
        chunk = line[len("data:"):].strip()
        if chunk == "[DONE]":
            break
        try:
            delta = json.loads(chunk)["choices"][0].get("delta", {}).get("content", "")
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
        if delta:
            parts.append(delta)
    return "".join(parts).strip()


def split_suggestion(text):
    """把 AI 回复拆成 正文 + 建议 两段，方便分别着色。"""
    body_lines, suggestion = [], ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("💡"):
            suggestion = line
        else:
            body_lines.append(line)
    return "\n".join(body_lines).strip(), suggestion


def render(body, suggestion):
    """ANSI 彩色终端渲染：红色标头 + 黄色正文 + 青色建议。"""
    out = [f"{BOLD_RED}[Mockingbird AI 警告]{RESET}"]
    if body:
        out.append(f"{YELLOW}{body}{RESET}")
    if suggestion:
        out.append(f"{CYAN}{suggestion}{RESET}")
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()


def fallback_quote(cmd):
    """本地兜底：随机一条毒舌语录，若能识别手滑则附带建议。"""
    suggestion = COMMON_TYPOS.get(cmd)
    quote = random.choice(FALLBACK_QUOTES).format(cmd=cmd)
    if suggestion:
        quote += f"\n💡 你是不是想输入: {suggestion}?"
    return quote


def main(argv):
    if not argv:
        return 0
    cmd = argv[0]
    args = list(argv[1:])
    cwd = os.environ.get("MOCKINGBIRD_CWD") or os.getcwd()

    # 未配置 API Key：直接本地兜底，不打扰用户
    if not API_KEY:
        body, suggestion = split_suggestion(fallback_quote(cmd))
        render(body, suggestion)
        return 0

    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS.get(TONE, SYSTEM_PROMPTS["sarcastic"])},
        {"role": "user", "content": build_user_prompt(cmd, args, cwd)},
    ]

    try:
        text = call_api(messages)
        if not text:
            raise RuntimeError("empty response")
        body, suggestion = split_suggestion(text)
        if not suggestion:
            # 模型没按格式给建议时，用本地纠错表兜底
            local = COMMON_TYPOS.get(cmd)
            if local:
                suggestion = f"💡 你是不是想输入: {local}?"
        render(body, suggestion)
    except Exception:
        # 超时 / 断网 / HTTP 错误 / 解析失败：静默回退本地语录
        body, suggestion = split_suggestion(fallback_quote(cmd))
        render(body, suggestion)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
