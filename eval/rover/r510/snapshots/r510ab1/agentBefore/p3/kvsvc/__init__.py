"""kvsvc —— 仅用 Python 3 标准库实现的带过期时间的键值存储服务。

入口: python3 -m kvsvc.server --port {int} --wal {path}
"""

__all__ = ["store", "server"]
