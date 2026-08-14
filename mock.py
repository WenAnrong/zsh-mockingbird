#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zsh-mockingbird / mock.py
"""

import argparse
import json
import os
import random
import sys
import threading
import urllib.request

# --------------------------------------------------------------------------
# ANSI 颜色
# --------------------------------------------------------------------------
RESET = "\033[0m"
BOLD_RED = "\033[1;31m"  # 标头：红色粗体
YELLOW = "\033[0;33m"    # AI 回复：黄色
CYAN = "\033[0;36m"      # 建议命令：青色

# 转圈动画（等待 AI 响应期间显示）
# --------------------------------------------------------------------------
SPINNER_FRAMES_UTF8 = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SPINNER_FRAMES_ASCII = ["|", "/", "-", "\\"]


def spinner_frames():
    """按 stdout 编码选择转圈字符：UTF-8 用 Braille 点阵，否则回退 ASCII。"""
    enc = (sys.stdout.encoding or "").lower()
    return SPINNER_FRAMES_UTF8 if "utf" in enc else SPINNER_FRAMES_ASCII


def _display_width(text):
    """估算终端显示宽度：ASCII 算 1 列，其余（中文/emoji）算 2 列。"""
    return sum(2 if ord(ch) > 127 else 1 for ch in text)


class Spinner:
    """等待期间在终端显示转圈动画，结束时清除该行。"""

    def __init__(self, message):
        self.message = message
        self._stop = threading.Event()
        self._thread = None

    def _run(self):
        frames = spinner_frames()
        i = 0
        while not self._stop.is_set():
            sys.stdout.write("\r{} {}".format(frames[i % len(frames)], self.message))
            sys.stdout.flush()
            self._stop.wait(0.08)
            i += 1
        # 清空整行，避免残留
        sys.stdout.write("\r" + " " * (_display_width(self.message) + 4) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        if sys.stdout.isatty():  # 只在真实终端转圈，管道输出时静默
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc):
        if self._thread is not None:
            self._stop.set()
            self._thread.join()
        return False

# --------------------------------------------------------------------------
# 配置读取（直接读取 config.env 文件，不再依赖 shell export）
# --------------------------------------------------------------------------
def load_config(path):
    """解析 config.env（KEY=VALUE 格式）为 dict。

    自动忽略注释行、空行，并去掉值两侧可选的双引号/单引号。
    文件不存在时返回空 dict，不报错。
    """
    cfg = {}
    if not path or not os.path.isfile(path):
        return cfg
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key:
                cfg[key] = value
    return cfg


def read_config(config_path):
    """合并配置：优先读 config.env 文件，环境变量仅作向后兼容兜底。"""
    file_cfg = load_config(config_path)

    def pick(key, default):
        val = file_cfg.get(key)
        if val is not None and val.strip():
            return val.strip()
        val = os.environ.get(key)  # 兼容旧方式，非必需
        if val is not None and val.strip():
            return val.strip()
        return default

    cfg = {}
    cfg["api_key"] = pick("MOCKINGBIRD_API_KEY", "")
    cfg["api_url"] = pick("MOCKINGBIRD_API_URL", "").rstrip("/")
    cfg["model"] = pick("MOCKINGBIRD_MODEL", "")
    cfg["tone"] = pick("MOCKINGBIRD_TONE", "sarcastic")
    cfg["spinner"] = pick("MOCKINGBIRD_SPINNER", "正在思考怎么嘲讽你...")
    try:
        cfg["timeout"] = float(pick("MOCKINGBIRD_TIMEOUT", "3.0"))
    except (TypeError, ValueError):
        cfg["timeout"] = 3.0
    return cfg

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


def call_api(messages, cfg):
    """发起 OpenAI 兼容的请求，返回回复文本。"""
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.9,
        "max_tokens": 400,
    }
    req = urllib.request.Request(
        cfg["api_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + cfg["api_key"],
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


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


def render(body, suggestion, source="AI"):
    """Aif cfg["spinner"]:
            with Spinner(cfg["spinner"]):
                text = call_api(messages, cfg)
        else:
            NSI 彩色终端渲染：红色标头 + 黄色正文 + 青色建议。

    source 为 "AI" 时表示来自大模型，否则显示"本地"（本地兜底语录）。
    """
    label = "AI" if source == "AI" else "本地"
    out = [f"{BOLD_RED}[Mockingbird {label} 警告]{RESET}"]
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
    parser = argparse.ArgumentParser(add_help=False, prog="mock.py")
    parser.add_argument("--config", default="", help="config.env 文件路径")
    parser.add_argument("--cwd", default="", help="命令执行时的工作目录")
    parser.add_argument("rest", nargs="*")
    ns = parser.parse_args(argv)

    rest = ns.rest
    if not rest:
        return 0
    cmd = rest[0]
    args = list(rest[1:])
    cwd = ns.cwd or os.environ.get("MOCKINGBIRD_CWD") or os.getcwd()

    cfg = read_config(ns.config)

    # 未配置 API Key 或完整地址：直接本地兜底，不打扰用户
    if not cfg["api_key"] or not cfg["api_url"]:
        body, suggestion = split_suggestion(fallback_quote(cmd))
        render(body, suggestion, source="local")
        return 0

    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS.get(cfg["tone"], SYSTEM_PROMPTS["sarcastic"])},
        {"role": "user", "content": build_user_prompt(cmd, args, cwd)},
    ]

    try:
        if cfg["spinner"]:
            with Spinner(cfg["spinner"]):
                text = call_api(messages, cfg)
        else:
            text = call_api(messages, cfg)
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
        render(body, suggestion, source="local")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
