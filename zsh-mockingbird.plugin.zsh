# ---------------------------------------------------------------------------
# zsh-mockingbird.plugin.zsh
#
# 一个会"嘲讽你敲错命令"的 Zsh 插件。
# 依赖: python3（仅用标准库，无需 pip install 任何东西）
#
# 行为:
#   重写 Zsh 的 command_not_found_handler，把敲错的命令异步丢给 mock.py，
#   mock.py 调用 LLM API 生成阴阳怪气的嘲讽 + 正确命令建议。
#   （API 失败 / 超时 / 未配置 Key 时，自动回退到本地 5 条毒舌语录。）
#
# 适用加载方式:
#   - Oh My Zsh: 放到 ~/.oh-my-zsh/custom/plugins/zsh-mockingbird/ 并加入 plugins 数组
#   - 手动:      source /path/to/zsh-mockingbird.plugin.zsh
# ---------------------------------------------------------------------------

# 插件所在目录（自动解析，兼容 oh-my-zsh / 手动 source）
: "${MOCKINGBIRD_PLUGIN_DIR:=${${(%):-%x}:A:h}}"

# 加载本地配置（若存在 config.env，会把其中的变量 export 出来）
if [[ -f "${MOCKINGBIRD_PLUGIN_DIR}/config.env" ]]; then
    set -a
    source "${MOCKINGBIRD_PLUGIN_DIR}/config.env"
    set +a
fi

# 是否后台异步执行（不阻塞终端）：1 = 异步，0 = 同步等待
: "${MOCKINGBIRD_ASYNC:=1}"

# 重写 Zsh 的 command_not_found_handler
command_not_found_handler() {
    local cmd="$1"
    shift

    # python3 都没装就别折腾了，按原样报错
    if ! command -v python3 >/dev/null 2>&1; then
        return 127
    fi

    local mock_script="${MOCKINGBIRD_PLUGIN_DIR}/mock.py"
    if [[ ! -f "$mock_script" ]]; then
        return 127
    fi

    if (( MOCKINGBIRD_ASYNC )); then
        # &! = 后台运行 + disown，不阻塞终端，嘲讽稍后送达
        MOCKINGBIRD_CWD="$PWD" python3 "$mock_script" "$cmd" "$@" &!
    else
        # 同步等待结果（最多等 MOCKINGBIRD_TIMEOUT 秒）
        MOCKINGBIRD_CWD="$PWD" python3 "$mock_script" "$cmd" "$@"
    fi

    # 保持标准 Linux "command not found" 退出码
    return 127
}
