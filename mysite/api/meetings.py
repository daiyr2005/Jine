from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

from mysite.db.schema import *
from mysite.chain.meeting_chain import meeting_chain

router = APIRouter(prefix="/meetings", tags=["meetings"])





@router.post("/analyze/", response_model=List[MeetingTaskItem])
async def analyze(payload: AnalyzeRequest):
    try:
        result: MeetingTaskListSchema = await meeting_chain.ainvoke({"text": payload.text})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    return result.tasks


@router.post("/check_tasks/", response_model=CheckTasksResponse)
def check_tasks(payload: List[MeetingTaskItem]):
    checks = []
    without_assignee = without_deadline = complete = 0

    for i, task in enumerate(payload, start=1):
        missing = []
        if not task.assignee:
            missing.append("assignee")
            without_assignee += 1
        if not task.deadline_text:
            missing.append("deadline_text")
            without_deadline += 1
        if not missing:
            complete += 1

        checks.append(TaskCheck(
            task_number=i,
            needs_clarification=bool(missing),
            missing_fields=missing,
        ))

    return CheckTasksResponse(
        stats=Stats(
            total_tasks=len(payload),
            complete_tasks=complete,
            without_assignee=without_assignee,
            without_deadline=without_deadline,
        ),
        checks=checks,
    )