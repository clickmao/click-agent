"""tasksvc: 任务队列 CLI 服务 (仅标准库)。

子模块:
  - tasksvc.store: 存储层 (JSON 文件 + 原子写入 + 严格 schema 校验)
  - tasksvc.model: 模型/时间视图层
  - tasksvc.cli:   命令行入口

本包文件一律 UTF-8 无 BOM。
"""

__all__ = ["store"]
__version__ = "0.1.0"
