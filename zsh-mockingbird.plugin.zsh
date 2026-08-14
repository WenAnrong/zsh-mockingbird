# 插件所在目录（自动解析，兼容 oh-my-zsh / 手动 source）
: "${MOCKINGBIRD_PLUGIN_DIR:=${${(%):-%x}:A:h}}"

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

    # 同步执行：先等 mock.py 渲染完嘲讽，再回到提示符
    # 把 config.env 路径作为参数交给 mock.py 读取
    python3 "$mock_script" \
        --config "${MOCKINGBIRD_PLUGIN_DIR}/config.env" \
        --cwd "$PWD" \
        "$cmd" "$@"

    # 保持标准 Linux "command not found" 退出码
    return 127
}
