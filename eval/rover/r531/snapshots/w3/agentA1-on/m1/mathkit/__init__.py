"""mathkit: 纯函数数学工具包（仅标准库）。

每个 op 一个函数，签名 `op(args: dict) -> str`，返回应当写出的 stdout 文本
（末尾不带换行）。CLI 入口见 `mathkit/__main__.py`。
"""

__all__ = ["modular", "linear", "graphs", "prob"]
