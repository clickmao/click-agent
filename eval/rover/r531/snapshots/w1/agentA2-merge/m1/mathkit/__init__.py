"""mathkit: 一个仅依赖标准库的多模块数学工具包。

用法:
    echo '{"a": 11, "m": 16}' | python3 -m mathkit qr_count

每个 op 对应一个模块函数, 签名统一为 ``op(args: dict) -> str``,
返回应写到 stdout 的文本 (末尾不带换行)。
"""
