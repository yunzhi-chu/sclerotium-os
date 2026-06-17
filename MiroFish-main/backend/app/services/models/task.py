from enum import Enum
class TaskStatus(str, Enum):
    PENDING = "pending"; RUNNING = "running"; COMPLETED = "completed"; FAILED = "failed"
class Task:
    def __init__(self, *a, **kw): self.status = TaskStatus.PENDING
class TaskManager: pass
