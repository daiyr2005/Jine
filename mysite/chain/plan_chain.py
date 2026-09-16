from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_ollama import ChatOllama
from mysite.config import OLLAMA_URL, OLLAMA_MODEL
from mysite.db.schema import PlanOutputSchema

llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0,
)

structured_llm = llm.with_structured_output(PlanOutputSchema)

plan_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Ты — ассистент технического менеджера. Твоя задача — разбить цель на конкретный список задач.\n\n"
            "ПРАВИЛА ЗАПОЛНЕНИЯ:\n"
            "1. title: короткое название задачи (3-6 слов).\n"
            "2. details: конкретное описание, что нужно сделать, с учётом ограничений (constraints).\n"
            "3. priority: 3 — критично для цели, 2 — важно, 1 — второстепенно.\n"
            "4. status: всегда 'todo'.\n"
            "5. task_number: последовательная нумерация с 1.\n"
            "6. Строго учитывай ограничения из constraints (например, если сказано что автотесты не нужны — не создавай задачи на автотесты).\n"
            "7. Составь ровно {count_tasks} задач(и), не больше и не меньше."
        ),
        (
            "human",
            "Цель: {goal}\nОграничения: {constraints}"
        ),
    ]
)


def finalize_plan(data: PlanOutputSchema) -> PlanOutputSchema:
    # подстраховка нумерации на случай, если модель ошиблась
    for i, task in enumerate(data.tasks, start=1):
        task.task_number = i
        if task.priority < 1:
            task.priority = 1
        if task.priority > 3:
            task.priority = 3
        if not task.status:
            task.status = "todo"
    return data


plan_chain = plan_prompt | structured_llm | RunnableLambda(finalize_plan)