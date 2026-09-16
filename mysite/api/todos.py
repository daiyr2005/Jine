from fastapi import APIRouter, HTTPException
from mysite.db.schema import *
from mysite.chain.plan_chain import plan_chain
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter(prefix="/todos", tags=["todos"])



@router.post("/plan_create/", response_model=PlanCreateResponse)
async def plan_create(payload: PlanCreateRequest):
    try:
        result: PlanOutputSchema = await plan_chain.ainvoke(
            {
                "goal": payload.goal,
                "constraints": payload.constraints or "нет ограничений",
                "count_tasks": payload.count_tasks,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    return PlanCreateResponse(
        plan_status="draft",
        tasks=result.tasks,
        tasks_count=len(result.tasks),
    )