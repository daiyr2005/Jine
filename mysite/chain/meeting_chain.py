from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_ollama import ChatOllama
from mysite.config import OLLAMA_URL, OLLAMA_MODEL
from mysite.db.schema import MeetingTaskListSchema

llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0,
)

structured_llm = llm.with_structured_output(MeetingTaskListSchema)

meeting_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Ты — ассистент, который анализирует текст встречи и извлекает из него конкретные задачи "
            "и договорённости.\n\n"
            "ПРАВИЛА ЗАПОЛНЕНИЯ:\n"
            "1. title: краткая формулировка того, что нужно сделать (глагол + суть), без имени и срока.\n"
            "2. assignee: имя ответственного, если оно явно названо в тексте. Если не названо — null.\n"
            "3. deadline_text: срок ровно в той формулировке, как он упомянут в тексте (например, 'до пятницы'). "
            "Если срок не упомянут — null.\n"
            "4. Включай в список только задачи, по которым явно принято решение — то, что просто обсуждали "
            "без принятого решения, в список НЕ включай."
        ),
        (
            "human",
            "Текст встречи: {text}"
        ),
    ]
)


def clean_meeting_tasks(data: MeetingTaskListSchema) -> MeetingTaskListSchema:
    for task in data.tasks:
        if task.assignee is not None and not str(task.assignee).strip():
            task.assignee = None
        if task.deadline_text is not None and not str(task.deadline_text).strip():
            task.deadline_text = None
    return data


meeting_chain = meeting_prompt | structured_llm | RunnableLambda(clean_meeting_tasks)