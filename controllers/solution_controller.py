from fastapi import APIRouter, HTTPException, Query
from dto import PinnedTaskDto, UpdateTaskDto, MemoDto
from typing import List, Optional
from datetime import date
from storage import db

router = APIRouter(prefix="/solution", tags=["Solution"])


@router.post("/task")
async def add_pinned_task(task_dto: PinnedTaskDto):
    """为指定模具在特定日期和顺序位置添加固定任务。"""
    task_id = db.get_next_id("task")
    task = task_dto.model_dump()
    task["taskId"] = task_id
    db.pinned_tasks.append(task)
    with db.session_scope() as s:
        db.save(s)
    return {"message": "Task added successfully", "taskId": task_id}


@router.put("/task")
async def update_task(task_dto: UpdateTaskDto):
    """修改指定 ID 的任务信息（如数量、固定类型等）。如果标记为已完成，会触发备忘录处理。"""
    for task in db.pinned_tasks:
        if task["taskId"] == task_dto.taskId:
            if task_dto.pinnedType is not None:
                task["pinnedType"] = task_dto.pinnedType
            if task_dto.quantity is not None:
                task["quantity"] = task_dto.quantity
            with db.session_scope() as s:
                db.save(s)
            return {"message": f"Task {task_dto.taskId} updated"}
    raise HTTPException(status_code=404, detail="Task not found")


@router.delete("/task")
async def delete_task(id: int):
    """根据 ID 删除指定的任务。"""
    db.pinned_tasks = [t for t in db.pinned_tasks if t["taskId"] != id]
    with db.session_scope() as s:
        db.save(s)
    return {"message": f"Task {id} deleted"}


@router.get("/task/swap")
async def swap_tasks(task1Id: int, task2Id: int):
    """交换两个任务的日期和顺序。两个任务必须属于同一线体且未完成。"""
    t1 = next((t for t in db.pinned_tasks if t["taskId"] == task1Id), None)
    t2 = next((t for t in db.pinned_tasks if t["taskId"] == task2Id), None)
    if t1 and t2:
        t1["day"], t2["day"] = t2["day"], t1["day"]
        t1["seqInDay"], t2["seqInDay"] = t2["seqInDay"], t1["seqInDay"]
        with db.session_scope() as s:
            db.save(s)
        return {"message": f"Tasks {task1Id} and {task2Id} swapped"}
    raise HTTPException(status_code=404, detail="One or both tasks not found")


@router.get("/solve-result")
async def get_solve_result(lineId: int, begin: date, end: date):
    """根据线体 ID 和时间范围获取排产结果。"""
    all_tasks = db.solve_results.get(lineId, [])
    # 过滤时间范围
    filtered = [t for t in all_tasks if begin <= t["day"] <= end]
    return {"lineId": lineId, "period": [begin, end], "tasks": filtered}


@router.post("/die-memo")
async def save_memo(memo_dto: MemoDto):
    """添加/修改记录"""
    memo_id = db.get_next_id("memo")
    db.memos[memo_id] = memo_dto.model_dump()
    db.memos[memo_id]["id"] = memo_id
    with db.session_scope() as s:
        db.save(s)
    return {"message": "Memo saved", "id": memo_id}


@router.delete("/die-memo")
async def delete_memo(memoId: int):
    """删除记录"""
    if memoId in db.memos:
        del db.memos[memoId]
        with db.session_scope() as s:
            db.save(s)
        return {"message": f"Memo {memoId} deleted"}
    raise HTTPException(status_code=404, detail="Memo not found")


@router.get("/die-memo")
async def get_all_memos():
    """获取所有记录"""
    return {"memos": list(db.memos.values())}


@router.get("/solve-result")
async def get_solve_result_by_week(lineId: int, begin: date, end: date):
    """根据线体 ID 和时间范围获取排产结果（按周查询）"""
    all_tasks = db.solve_results.get(lineId, [])
    # 过滤时间范围
    filtered = [t for t in all_tasks if begin <= t.get("day") <= end]
    return {"lineId": lineId, "period": [begin, end], "tasks": filtered}
