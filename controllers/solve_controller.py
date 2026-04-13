from fastapi import APIRouter, HTTPException
from dto import SolveDto
from storage import db
from data_models import ScheduleData, Day, Die, Part, DiePart, PartDemand, Task
from core_model import PunchingScheduler
from datetime import timedelta, date
import logging

router = APIRouter(prefix="/solve", tags=["Solve"])


def get_schedule_data(line_id: int, begin_date: date) -> ScheduleData:
    num_days = 7
    days_range = [begin_date + timedelta(days=i) for i in range(num_days)]

    # 1. 获取该线体的模具
    line_dies = [v for v in db.dies.values() if v["lineId"] == line_id]
    if not line_dies:
        raise HTTPException(status_code=400, detail=f"No dies found for line {line_id}")

    die_map = {}
    die_db_id_to_code = {}
    for d in line_dies:
        min_batch = 100
        prod_time = int(60 / d["akz"]) if d["akz"] > 0 else 60
        die = Die(id=d["code"], min_batch=min_batch, production_time=prod_time)
        die_map[die.id] = die
        die_db_id_to_code[d["id"]] = d["code"]

    # 2. 获取这些模具生产的零件
    die_db_ids = set(die_db_id_to_code.keys())
    line_parts = [v for v in db.parts.values() if v["dieId"] in die_db_ids]

    part_map = {}
    part_db_id_to_code = {}
    for p in line_parts:
        inv_record = next(
            (v for v in db.part_inventory.values()
             if v["part"] == p["code"] and v["day"] == begin_date),
            None
        )
        initial_inv = inv_record["quantity"] if inv_record else 0
        part = Part(id=p["code"], initial_stock=initial_inv, max_stock=p["min"] * 5)
        part_map[part.id] = part
        part_db_id_to_code[p["id"]] = p["code"]

    # 3. 生产关系（die_part_map）
    die_part_map = {}
    for p in line_parts:
        die_code = die_db_id_to_code[p["dieId"]]
        part_code = p["code"]
        die_part_map[(die_code, part_code)] = DiePart(
            die_id=die_code, part_id=part_code, yield_rate=1  # 假设一个 hit 产出一个零件
        )

    # 4. 天配置（day_map）
    day_map = {}
    for d in days_range:
        day_id = str(d)
        day_cfg = db.days.get(d)
        if day_cfg:
            wt_text = day_cfg["workingTimeText"]
            minutes = db.working_times.get(wt_text, 480)
            working_time = minutes
            out_minutes = day_cfg["outMinutes"]
        else:
            working_time = 480
            out_minutes = 0
        day_map[day_id] = Day(id=day_id, working_time=working_time, out_minutes=out_minutes)

    # 5. 零件需求（part_demand_map）
    part_demand_map = {}
    for d in days_range:
        day_id = str(d)
        usages = [v for v in db.car_usages.values() if v["day"] == d]
        for part_code, part in part_map.items():
            total_demand = 0
            p_db_id = next((k for k, v in part_db_id_to_code.items() if v == part_code), None)
            if p_db_id is not None:
                relevant_car_parts = [v for v in db.car_parts.values() if v["partId"] == p_db_id]
                for cp in relevant_car_parts:
                    car_usage = next((u["num"] for u in usages if u["carId"] == cp["carId"]), 0)
                    total_demand += car_usage * cp["usage"]
            if total_demand > 0:
                part_demand_map[(day_id, part_code)] = PartDemand(
                    day_id=day_id, part_id=part_code, demand=total_demand
                )

    # 6. 初始任务列表（每个模具每天一个任务占位）
    tasks = []
    task_id = 0
    for day_id in sorted(day_map.keys(), key=lambda d: [int(x) for x in d.split('-')]):
        for die_id in die_map:
            tasks.append(Task(id=str(task_id), day_id=day_id, die_id=die_id))
            task_id += 1

    return ScheduleData(day_map, die_map, part_map, die_part_map, part_demand_map, tasks)


@router.post("/start")
async def start_solve(solve_dto: SolveDto):
    try:
        data = get_schedule_data(solve_dto.lineId, solve_dto.begin)
        scheduler = PunchingScheduler(data)
        try:
            # New behavior: scheduler.solve() returns active task list or raises on infeasible
            result_tasks = scheduler.solve(log_search=False)

            # persist results and status
            db.solve_results[solve_dto.lineId] = result_tasks
            db.solve_status[solve_dto.lineId] = {
                "status": "COMPLETED",
                "score": scheduler.last_score,
            }

            # Persist active tasks into relational task table via storage.pinned_tasks
            pinned = []
            for t in result_tasks:
                # find die db id by code if possible
                die_code = t.get("dieCode")
                die_db_id = None
                for k, v in db.dies.items():
                    if v.get("code") == die_code:
                        die_db_id = k
                        break

                task_id = db.get_next_id("task")
                pinned.append({
                    "taskId": task_id,
                    "day": t.get("day"),
                    "dieId": die_db_id,
                    "seqInDay": t.get("seqInDay"),
                    "quantity": t.get("hits"),
                    "pinnedType": None,
                    "memo": None,
                    "priority": None,
                })

            db.pinned_tasks = pinned

            with db.session_scope() as s:
                db.save(s)

            # return results to frontend
            return {"message": f"Solver finished for line {solve_dto.lineId}", "status": "COMPLETED", "results": result_tasks}
        except Exception as e:
            # If scheduler raised SolveInfeasibleError (or other), try to extract reasons
            reasons = getattr(e, 'reasons', None) or [str(e)]

            # 诊断不可行原因已在 exception.reasons 中，如果没有，再执行诊断
            # 尝试生成降级的回退排产（贪心分配，尽量满足需求）。
            result_tasks = []
            remaining = {k: v.demand for k, v in data.part_demand_map.items()}

            def sorted_days():
                return sorted(data.day_map.keys(), key=lambda d: [int(x) for x in d.split('-')])

            for day_id in sorted_days():
                day = data.day_map[day_id]
                work_sec = (day.working_time - day.out_minutes) * 60

                for die_id, die in data.die_map.items():
                    # 可生产的零件
                    capable_parts = [p for (d, p) in data.die_part_map.keys() if d == die_id]
                    if not capable_parts:
                        continue

                    max_hits = work_sec // die.production_time if die.production_time > 0 else 0
                    assigned_qty = 0
                    assigned_part = None

                    for part_id in capable_parts:
                        dem = remaining.get((day_id, part_id), 0)
                        if dem <= 0:
                            continue
                        take = min(dem, max_hits)
                        # 必须满足最小批次，否则跳过
                        if take >= die.min_batch:
                            assigned_qty = take
                            assigned_part = part_id
                            remaining[(day_id, part_id)] = dem - take
                            break

                    if assigned_qty > 0 and assigned_part is not None:
                        result_tasks.append({
                            "day": date.fromisoformat(day_id),
                            "dieCode": die_id,
                            "hits": assigned_qty,
                            "lineId": solve_dto.lineId,
                            "startTime": 0,
                        })

            if result_tasks:
                # 排序并设置顺序字段
                result_tasks.sort(key=lambda x: (x["day"], x["startTime"]))
                last_day = None
                seq = 1
                for t in result_tasks:
                    if t["day"] != last_day:
                        seq = 1
                        last_day = t["day"]
                    t["seqInDay"] = seq
                    seq += 1

                db.solve_results[solve_dto.lineId] = result_tasks
                db.solve_status[solve_dto.lineId] = {"status": "PARTIAL", "reasons": reasons}

                # Persist partial active tasks into relational task table via storage.pinned_tasks
                pinned = []
                for t in result_tasks:
                    die_code = t.get("dieCode")
                    die_db_id = None
                    for k, v in db.dies.items():
                        if v.get("code") == die_code:
                            die_db_id = k
                            break

                    task_id = db.get_next_id("task")
                    pinned.append({
                        "taskId": task_id,
                        "day": t.get("day"),
                        "dieId": die_db_id,
                        "seqInDay": t.get("seqInDay"),
                        "quantity": t.get("hits"),
                        "pinnedType": None,
                        "memo": None,
                        "priority": None,
                    })

                db.pinned_tasks = pinned

                with db.session_scope() as s:
                    db.save(s)
                return {
                    "message": f"Solver failed; generated partial fallback schedule for line {solve_dto.lineId}",
                    "status": "PARTIAL",
                    "reasons": reasons,
                    "results": result_tasks,
                }

            # 如果回退也没有任何结果，则按原有逻辑返回失败
            db.solve_status[solve_dto.lineId] = {"status": "FAILED", "reasons": reasons}
            with db.session_scope() as s:
                db.save(s)
            return {
                "message": "Solver failed to find a solution",
                "status": "FAILED",
                "reasons": reasons,
            }

    except Exception as e:
        logging.exception("Solve failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/is-running")
async def is_solve_running():
    """检查是否有排产任务正在运行"""
    # TODO: 实现实际的求解状态检查
    return {"running": False, "lineId": None}


@router.get("/result/all")
async def get_all_solve_results():
    """获取所有排产结果"""
    results = []
    for line_id, tasks in db.solve_results.items():
        results.extend(tasks)
    return {"data": results}


@router.get("/result/latest")
async def get_latest_solve_result():
    """获取最新的排产结果（预览）。返回最近有结果的线体的结果（非空）。"""
    if not db.solve_results:
        return {"data": []}

    # 返回最近一个非空结果的线体
    for line_id in reversed(list(db.solve_results.keys())):
        results = db.solve_results.get(line_id) or []
        if results:
            return {"data": results}

    # 若所有结果均为空，返回空列表
    return {"data": []}
