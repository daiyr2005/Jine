from typing import Optional, List
from pydantic import BaseModel, Field

class MeetingTaskItem(BaseModel):
    title: str
    assignee: str | None = None
    deadline_text: str | None = None


class AnalyzeRequest(BaseModel):
    text: str


class Stats(BaseModel):
    total_tasks: int
    complete_tasks: int
    without_assignee: int
    without_deadline: int


class TaskCheck(BaseModel):
    task_number: int
    needs_clarification: bool
    missing_fields: List[str]


class CheckTasksResponse(BaseModel):
    stats: Stats
    checks: List[TaskCheck]


class PlanCreateRequest(BaseModel):
    goal: str
    constraints: Optional[str] = None
    count_tasks: int = Field(3, ge=1, le=20)


class TaskOut(BaseModel):
    task_number: int
    title: str
    details: Optional[str] = None
    priority: int
    status: str


class PlanCreateResponse(BaseModel):
    plan_status: str = "draft"
    tasks: List[TaskOut]
    tasks_count: int


class MeetingTaskSchema(BaseModel):
    title: str = Field(description="Краткая формулировка задачи/договорённости")
    assignee: Optional[str] = Field(default=None, description="Имя ответственного, если указан")
    deadline_text: Optional[str] = Field(default=None, description="Срок как он упомянут в тексте, если указан")


class MeetingTaskListSchema(BaseModel):
    """Строгая схема вывода для извлечения задач из текста встречи."""
    tasks: List[MeetingTaskSchema] = Field(description="Список извлечённых задач/договорённостей")

class TaskItemSchema(BaseModel):
    task_number: int = Field(description="Порядковый номер задачи, начиная с 1")
    title: str = Field(description="Короткое название задачи")
    details: str = Field(description="Развёрнутое описание, что именно нужно сделать")
    priority: int = Field(description="Приоритет задачи от 1 (низкий) до 3 (высокий)")
    status: str = Field(default="todo", description="Статус задачи, всегда 'todo' при создании")


class PlanOutputSchema(BaseModel):
    """Строгая схема вывода для генерации плана задач."""
    tasks: List[TaskItemSchema] = Field(description="Список задач плана")