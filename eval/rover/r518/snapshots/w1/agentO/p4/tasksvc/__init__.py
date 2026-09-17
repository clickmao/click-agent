"""tasksvc: 任务队列 CLI 服务 (纯标准库)。

模块划分:
  tasksvc.store  存储层: JSON 数据库加载/校验/原子保存
  tasksvc.model  模型/时间层 (由后序节点实现)
  tasksvc.cli    命令行/状态机/输出 (由后序节点实现)

本文件仅做包标记与版本声明, 不实现任何业务逻辑。
"""

__all__ = ["store"]
__version__ = "1.0.0"
