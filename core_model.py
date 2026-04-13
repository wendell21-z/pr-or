from ortools.sat.python import cp_model
from data_models import ScheduleData

"""
约束概述：
1. 某一天某个零件的库存 = 上一天的库存 + 该天生产 - 该天消耗
2. 某一天的生产时间 < 某一天的可生产时间
3. 某一天的生产时间 = 该天所有模具的生产时间总和
4. 某一天某个零件的生产数量 = 该天模具工作次数 * 该模具对应零件的生产数量
5. 某一天的生产时间 > 该天可用生产时间 * 0.8
6. 某一天的生产时间 < 该天可用生产时间
"""


class SolveInfeasibleError(Exception):
    """Raised when the CP-SAT solver finds the model infeasible. Contains a list of diagnostic reasons."""
    def __init__(self, reasons=None):
        super().__init__("Solve infeasible")
        self.reasons = reasons or []


class PunchingScheduler:
    def __init__(self, data: ScheduleData):
        self.data = data
        self.model = cp_model.CpModel()

        self.part_stock = {}     # {(part_id, day_id): int_var} 每天每个零件的库存
        self.max_production_per_day = 500
        self.assumptions = {}    # {assumption_literal: description}
        self.last_score = None

        # 按日期排序的天列表（支持 "YYYY-M-D" 或 "YYYY-MM-DD" 格式）
        self._sorted_days = sorted(
            data.day_map.keys(),
            key=lambda d: [int(x) for x in d.split('-')]
        )
        # 按天分组的任务索引
        self._tasks_by_day = {}
        for task in data.tasks:
            self._tasks_by_day.setdefault(task.day_id, []).append(task)

    def _create_variables(self):
        """
        创建模型变量，并将 OR-Tools 变量直接赋值到 Task 对象。
        """
        for day_id, day in self.data.day_map.items():
            work_time_seconds = (day.working_time - day.out_minutes) * 60
            tasks = self._tasks_by_day.get(day_id, [])
            num_tasks = len(tasks)


            for task in tasks:
                # 核心任务变量（赋值到 Task 对象）
                task.quantity = self.model.new_int_var(
                    0, self.max_production_per_day, f"qty_{task.id}")
                task.active = self.model.new_bool_var(f"active_{task.id}")
                # order 表示任务在当天中的序号（0 = 未安排，1..num_tasks = 序号）
                task.order = self.model.new_int_var(0, num_tasks, f"order_{task.id}")
                task.start = self.model.new_int_var(0, work_time_seconds, f"start_{task.id}")
                task.duration = self.model.new_int_var(0, work_time_seconds, f"dur_{task.id}")
                task.end = self.model.new_int_var(0, work_time_seconds, f"end_{task.id}")
                task.interval = self.model.new_optional_interval_var(
                    task.start, task.duration, task.end, task.active, f"interval_{task.id}")
                
                # 如果task的pin属性有值，则设置为固定变量
                if task.pinned_quantity is not None:
                    self.model.add(task.quantity == task.pinned_quantity)
                if task.pinned_order is not None:
                    self.model.add(task.order == task.pinned_order)
                    self.model.add(task.active == 1)  # 锁定序号的任务必须激活

        # 零件库存变量
        for part_id, part in self.data.part_map.items():
            for day_id in self._sorted_days:
                self.part_stock[(part_id, day_id)] = self.model.new_int_var(
                    0, part.max_stock, f"stock_{part_id}_{day_id}")

    def _add_constraints(self):
        def add_assumed(expr, name, desc):
            """添加带假设的约束，用于不可行性诊断。"""
            a = self.model.new_bool_var(name)
            self.model.add(expr).OnlyEnforceIf(a)
            self.assumptions[a] = desc

        # 约束 1：最小批次、未激活时数量为零、时长 = 数量 × 生产时间
        for task in self.data.tasks:
            die = self.data.die_map[task.die_id]
            qty = task.quantity
            active = task.active
            dur = task.duration

            # 若激活，数量 ≥ 最小批次；若未激活，数量 = 0
            self.model.add(qty >= die.min_batch).OnlyEnforceIf(active)
            self.model.add(qty == 0).OnlyEnforceIf(active.Not())
            # 时长 = 数量 × 单次生产时间
            self.model.add(dur == qty * die.production_time)
            # 序号：未激活时为 0，激活时 ≥ 1
            self.model.add(task.order == 0).OnlyEnforceIf(active.Not())
            self.model.add(task.order >= 1).OnlyEnforceIf(active)

        # 约束 2：每天的任务不能重叠（单机约束）
        for day_id in self._sorted_days:
            tasks = self._tasks_by_day.get(day_id, [])
            self.model.add_no_overlap([task.interval for task in tasks])

        # 约束 3：零件库存平衡
        # for part_id, part in self.data.part_map.items():
        #     for d_idx, day_id in enumerate(self._sorted_days):
        #         # 计算当天该零件的总产量
        #         daily_production = []
        #         for task in self._tasks_by_day.get(day_id, []):
        #             key = (task.die_id, part_id)
        #             if key in self.data.die_part_map:
        #                 yield_rate = self.data.die_part_map[key].yield_rate
        #                 daily_production.append(task.quantity * yield_rate)
        #
        #         # 前一天库存（第一天使用初始库存）
        #         if d_idx == 0:
        #             prev_stock = part.initial_stock
        #         else:
        #             prev_day_id = self._sorted_days[d_idx - 1]
        #             prev_stock = self.part_stock[(part_id, prev_day_id)]
        #
        #         pd = self.data.part_demand_map.get((day_id, part_id))
        #         demand = pd.demand if pd else 0
        #
        #         # 库存平衡等式
        #         self.model.add(
        #             self.part_stock[(part_id, day_id)] == prev_stock + sum(daily_production) - demand
        #         ).WithName(f"StockBalance_{part_id}_{day_id}")
        #
        #         # 带假设的非负库存约束（用于不可行性诊断）
        #         add_assumed(
        #             prev_stock + sum(daily_production) >= demand,
        #             f"NonNegStock_{part_id}_{day_id}",
        #             f"第 {day_id} 天零件 {part_id} 的库存不足（需求 {demand}，可用 {prev_stock} + 生产）。"
        #         )

        # 约束 4：每日工作时间（80% - 100%）
        # for day_id, day in self.data.day_map.items():
        #     work_time_seconds = (day.working_time - day.out_minutes) * 60
        #     min_work = int(work_time_seconds * 0.8)
        #     total_time = [task.duration for task in self._tasks_by_day.get(day_id, [])]
        #
        #     add_assumed(sum(total_time) >= min_work,
        #                 f"MinWork_{day_id}",
        #                 f"第 {day_id} 天工作时间未达到 80% 最小负荷要求。")
        #     add_assumed(sum(total_time) <= work_time_seconds,
        #                 f"MaxWork_{day_id}",
        #                 f"第 {day_id} 天工作量超过最大可用时间 ({work_time_seconds}s)。")

        # 约束 5：用户锁定任务（pinned_quantity / pinned_order）
        # for task in self.data.tasks:
        #     if task.pinned_quantity is not None:
        #         add_assumed(
        #             task.quantity == task.pinned_quantity,
        #             f"PinQty_{task.id}",
        #             f"任务 {task.id}（模具 {task.die_id}，{task.day_id}）的数量必须为 {task.pinned_quantity}。"
        #         )
        #
        #     if task.pinned_order is not None:
        #         # 锁定序号的任务必须被激活
        #         add_assumed(
        #             task.active == 1,
        #             f"PinActive_{task.id}",
        #             f"任务 {task.id}（模具 {task.die_id}，{task.day_id}）必须被安排。"
        #         )
        #         # 将 order 变量锁定为指定序号
        #         self.model.add(task.order == task.pinned_order).OnlyEnforceIf(task.active)
        #
        #         # 通过开始时间强制与其他锁定任务的相对顺序
        #         for other in self._tasks_by_day.get(task.day_id, []):
        #             if other.id != task.id and other.pinned_order is not None:
        #                 if other.pinned_order < task.pinned_order:
        #                     # other 必须在 task 之前完成
        #                     self.model.add(
        #                         task.start >= other.end
        #                     ).OnlyEnforceIf([task.active, other.active])

    def _set_objective(self):
        total_objective = []

        for d_idx, day_id in enumerate(self._sorted_days):
            # 越早的库存权重越高
            day_weight = len(self._sorted_days) - d_idx

            for part_id in self.data.part_map:
                stock_var = self.part_stock[(part_id, day_id)]
                total_objective.append(stock_var * day_weight)

                pd = self.data.part_demand_map.get((day_id, part_id))
                demand = pd.demand if pd else 0
                priority_threshold = 3 * demand

                # 紧急优先级：库存低于阈值时加分
                is_urgent = self.model.new_bool_var(f"urgent_{part_id}_{day_id}")
                self.model.add(stock_var < priority_threshold).OnlyEnforceIf(is_urgent)
                self.model.add(stock_var >= priority_threshold).OnlyEnforceIf(is_urgent.Not())
                total_objective.append(is_urgent * 1000)

            # 减少模具更换惩罚
            for task in self._tasks_by_day.get(day_id, []):
                total_objective.append(task.active * -10)

        self.model.maximize(sum(total_objective))

    def solve(self, log_search=True):
        """Run the solver. If a feasible/optimal solution is found, return a list of active tasks
        (each as a dict with day, dieCode, hits, startTime, seqInDay). If infeasible, raise SolveInfeasibleError
        with diagnostic reasons."""
        self._create_variables()
        self._add_constraints()
        self._set_objective()

        solver = cp_model.CpSolver()
        if log_search:
            solver.parameters.log_search_progress = True

        for lit in self.assumptions.keys():
            self.model.add_assumption(lit)

        status = solver.Solve(self.model)

        # Collect infeasibility reasons if infeasible
        if status == cp_model.INFEASIBLE:
            reasons = self.diagnose_infeasibility(solver)
            raise SolveInfeasibleError(reasons=reasons)

        # If feasible or optimal, build active task list
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # extract tasks
            result_tasks = []
            for task in self.data.tasks:
                qty = solver.Value(task.quantity)
                if qty > 0:
                    start_time = solver.Value(task.start)
                    result_tasks.append({
                        "day": date.fromisoformat(task.day_id),
                        "dieCode": task.die_id,
                        "hits": qty,
                        "startTime": start_time,
                    })

            # sort and add seqInDay
            result_tasks.sort(key=lambda x: (x["day"], x["startTime"]))
            last_day = None
            seq = 1
            for t in result_tasks:
                if t["day"] != last_day:
                    seq = 1
                    last_day = t["day"]
                t["seqInDay"] = seq
                seq += 1

            # save last objective value
            try:
                self.last_score = solver.ObjectiveValue()
            except Exception:
                self.last_score = None

            return result_tasks

        # Any other status is treated as infeasible/failed
        reasons = [f"Solver returned status {status}"]
        raise SolveInfeasibleError(reasons=reasons)

    def diagnose_infeasibility(self, solver: cp_model.CpSolver) -> list[str]:
        """结合 Sufficient Assumed Unsat Core 和业务逻辑诊断不可行原因。"""
        reasons = []

        # 1. 检查 OR-Tools 的 Unsat Core
        core = solver.sufficient_assumptions_for_infeasibility()
        if core:
            idx_to_desc = {var.Index(): d for var, d in self.assumptions.items()}
            for lit_idx in core:
                desc = idx_to_desc.get(lit_idx)
                if desc:
                    reasons.append(f"冲突约束: {desc}")

        # 2. 若 Unsat Core 无结果，执行启发式产能检查
        if not reasons:
            for part_id, part in self.data.part_map.items():
                total_demand = sum(
                    (self.data.part_demand_map[(day_id, part_id)].demand
                     if (day_id, part_id) in self.data.part_demand_map else 0)
                    for day_id in self._sorted_days
                )

                total_max_yield = 0
                has_capable_die = False
                for day_id in self._sorted_days:
                    day = self.data.day_map[day_id]
                    work_sec = (day.working_time - day.out_minutes) * 60
                    day_max = 0
                    for task in self._tasks_by_day.get(day_id, []):
                        key = (task.die_id, part_id)
                        if key in self.data.die_part_map:
                            has_capable_die = True
                            die = self.data.die_map[task.die_id]
                            yield_rate = self.data.die_part_map[key].yield_rate
                            max_hits = work_sec // die.production_time
                            day_max = max(day_max, max_hits * yield_rate)
                    total_max_yield += day_max

                if not has_capable_die:
                    reasons.append(f"零件 {part_id} 没有关联的模具可以生产。")
                elif part.initial_stock + total_max_yield < total_demand:
                    reasons.append(
                        f"零件 {part_id} 的总需求 ({total_demand}) 超过了最大可能的总产能和初始库存之和 "
                        f"({part.initial_stock + total_max_yield})。"
                    )

        if not reasons:
            reasons.append("求解器未找到可行解，可能是由于复杂的库存平衡或多模具竞争时间导致。请检查库存和需求配置。")

        return reasons

    def print_solution(self, solver, status):
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print(f"Solution Status: {solver.StatusName(status)}")

            for day_id in self._sorted_days:
                print(f"\n--- Day {day_id} ---")
                print("Production Plan (Sequence):")

                active_tasks = []
                for task in self._tasks_by_day.get(day_id, []):
                    qty = solver.Value(task.quantity)
                    if qty > 0:
                        start = solver.Value(task.start)
                        active_tasks.append({"task": task, "quantity": qty, "start": start})

                active_tasks.sort(key=lambda x: x["start"])

                total_time = 0
                for i, entry in enumerate(active_tasks, start=1):
                    task = entry["task"]
                    die = self.data.die_map[task.die_id]
                    qty = entry["quantity"]
                    start = entry["start"]
                    is_pinned = task.pinned_order is not None or task.pinned_quantity is not None
                    tag = "(User Pinned)" if is_pinned else "(Auto Planned)"
                    prod_time = qty * die.production_time
                    total_time += prod_time
                    print(f"  Task {i} {tag}: Die {task.die_id}, Qty {qty}, Start {start}s, Time {prod_time}s")

                if not active_tasks:
                    print("  No production planned.")

                day = self.data.day_map[day_id]
                work_sec = (day.working_time - day.out_minutes) * 60
                print(f"Total Daily Production Time: {total_time} / {work_sec}s")

                print("Inventory Status (End of Day):")
                for part_id, part in self.data.part_map.items():
                    stock = solver.Value(self.part_stock[(part_id, day_id)])
                    print(f"  Part: {part_id}, Stock: {stock}/{part.max_stock}")
        else:
            print("No solution found.")
