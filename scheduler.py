import datetime
from typing import List, Dict, Any
from sqlalchemy import select, and_, func
from ortools.sat.python import cp_model
from sqlalchemy.orm import InstrumentedAttribute

from models import (
    db,
    CarPart,
    CarUsage,
    Part,
    PartInventory,
    Task,
    Dunnage,
    DunnageInventoryHistory,
    Day,
    WorkingTime,
    Die,
)
from utils import ensure_day


class ProductionScheduler:
    def __init__(self, line_id: int, start_date_str: str, days_count: int = 7):
        self.pinned_tasks: list[Any] = []
        self.dunnage_stock_capacity: dict[int, int] = {}
        self.empty_dunnages: dict[int, int] = {}
        self.dunnages: dict[int, Dunnage] = {}
        self.start_date_str = start_date_str
        self.day_capacity: list[int] = []
        self.start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        self.days_count = days_count
        self.dates = [
            (self.start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(days_count)
        ]
        self.initial_inventory: dict[int, int] = {}
        self.consumption: dict[int, list[int]] = {}
        self.die_to_parts: dict[int, list[int]] = {}
        self.parts: dict[int, Part] = {}
        self.dies: dict[int, Die] = {}
        self.line_id = line_id
        # Priority attributes for urgency-based scheduling
        self.urgency: dict[int, float] = {}  # {part_id: urgency_value}
        self.die_priority: dict[int, float] = {}  # {die_id: priority_weight}

    def fetch_data(self):
        # 1. 获取生产线上的模具
        die_ids = self._fetch_die()

        # 2. 获取相关零件
        part_ids = self._fetch_part(die_ids)

        # 2.1 移除没有对应零件的模具，不为这些模具创建任务
        active_die_ids = [d_id for d_id in die_ids if d_id in (self.die_to_parts or {})]
        # 仅保留有零件的模具
        self.dies = {
            d_id: die for d_id, die in self.dies.items() if d_id in active_die_ids
        }
        die_ids = active_die_ids

        # 3. 获取需求 (Consumption)
        self._compute_consumption(part_ids)

        # 4. 获取初始库存
        self._fetch_part_inventory()

        # 5. 获取并补齐每日可用时间
        self._fetch_day_capacity()

        # 6. 获取器具数据
        # 根据零件获取
        dunnage_ids = list(
            set(p.dunnage_id for p in self.parts.values() if p.dunnage_id)
        )
        self.dunnages = {}
        if dunnage_ids:
            dun_query = select(Dunnage).where(Dunnage.id.in_(dunnage_ids))
            dun_res = db.session.execute(dun_query).scalars().all()
            self.dunnages = {d.id: d for d in dun_res}

        # 关联零件和器具，计算初始可用总量
        for p_id, p in self.parts.items():
            if p.dunnage_id:
                # attach dunnage dict to Part object for later use
                setattr(p, "dunnage", self.dunnages.get(p.dunnage_id))

        self._fetch_empty_dunnage(dunnage_ids)

        self._compute_dunnage_capacity()

        # 8. 获取锁定任务
        self.pinned_tasks = []
        task_query = select(Task).where(
            and_(Task.die_id.in_(die_ids), Task.day_id.in_(self.dates))
        )
        task_res = db.session.execute(task_query).mappings().all()
        self.pinned_tasks = list(task_res)  # type: ignore[assignment]

        # 9. 计算零件紧急度（基于消耗/库存比）
        self._compute_urgency()

    def _fetch_empty_dunnage(self, dunnage_ids: list[Any]):
        """
        获取 start_date 当天器具库存，用于计算同器具零件库存上限
        """
        self.empty_dunnages = {d_id: 200 for d_id in dunnage_ids}
        if dunnage_ids:
            dun_inv_query = select(DunnageInventoryHistory).where(
                and_(
                    DunnageInventoryHistory.dunnage_id.in_(dunnage_ids),
                    DunnageInventoryHistory.day_id == self.start_date_str,
                )
            )
            dun_inv_res = db.session.execute(dun_inv_query).scalars().all()
            for row in dun_inv_res:
                self.empty_dunnages[row.dunnage_id] = row.empty_quantity or 0

    def _compute_dunnage_capacity(self):
        """
        计算器具类型对应的总容量。
        计算公式：器具1的总容量 = 器具1的空余数量 * 器具1的容量 + 器具1相关零件的库存总和
        """
        self.dunnage_stock_capacity = {}
        for d_id, dunnage in self.dunnages.items():
            related_parts = [
                p_id for p_id, p in self.parts.items() if p.dunnage_id == d_id
            ]
            initial_stock = sum(
                self.initial_inventory.get(p_id, 0) for p_id in related_parts
            )  # 相关零件的库存总和
            stock_capacity = (
                self.empty_dunnages[d_id] * (dunnage.capacity or 1) + initial_stock
            )
            self.dunnage_stock_capacity[d_id] = stock_capacity
            setattr(dunnage, "available_quantity", stock_capacity)

    def _fetch_day_capacity(self):
        days = db.session.query(Day).filter(Day.id.in_(self.dates)).all()
        day_map = {day.id: day for day in days}
        missing_day_ids = [date for date in self.dates if date not in day_map]
        if missing_day_ids:
            # use shared ensure_day util to create missing Day rows
            for date in missing_day_ids:
                ensure_day(date)
            db.session.flush()
            # reload days
            days = db.session.query(Day).filter(Day.id.in_(self.dates)).all()
            day_map.update({day.id: day for day in days})
            db.session.commit()

        working_times = db.session.query(WorkingTime).all()
        working_time_map = {
            working_time.text: working_time.minutes for working_time in working_times
        }

        self.day_capacity = [0] * self.days_count  # 每一天可用时间列表
        for i, d_str in enumerate(self.dates):
            day = day_map[d_str]
            working_minutes = working_time_map.get(day.woking_time or "") or 0
            out_minutes = day.out_minutes or 0
            self.day_capacity[i] = working_minutes + out_minutes

    def _fetch_part_inventory(self):
        part_ids = list(self.parts.keys())
        sd_str = self.start_date.isoformat()
        inv_map = {}
        try:
            inv_res = (
                db.session.query(PartInventory)
                .filter(
                    PartInventory.part_id.in_(part_ids), PartInventory.day_id == sd_str
                )
                .all()
            )
            inv_map = {row.part_id: row.quantity for row in inv_res}
        except Exception:
            inv_map = {}
        self.initial_inventory = {p_id: (inv_map.get(p_id) or 0) for p_id in self.parts}

    def _compute_consumption(self, part_ids: list[Any]):
        # Consumption(part, day) = Sum(car_usage(car, day) * car_part(car, part))
        self.consumption = {p_id: [0] * self.days_count for p_id in part_ids}
        usage_query = (
            select(
                CarUsage.day_id,
                CarPart.part_id,
                func.sum(CarUsage.usage * CarPart.usage).label("total_usage"),
            )
            .join(CarPart, CarUsage.car_id == CarPart.car_id)
            .where(and_(CarPart.part_id.in_(part_ids), CarUsage.day_id.in_(self.dates)))
            .group_by(CarUsage.day_id, CarPart.part_id)
        )
        usage_res = db.session.execute(usage_query).mappings().all()
        for row in usage_res:
            d_idx = self.dates.index(row["day_id"])
            self.consumption[row["part_id"]][d_idx] = int(row["total_usage"])

    def _fetch_part(self, die_ids: list[int]) -> list[int]:
        # Fetch Part ORM objects instead of mapping to dicts so scheduler can
        # access model attributes directly.
        parts_objs = db.session.query(Part).filter(Part.die_id.in_(die_ids)).all()
        self.parts = {p.id: p for p in parts_objs}
        part_ids = list(self.parts.keys())

        # 模具与零件的对应关系 (假设一个模具产出一个零件，或者一个模具产出多个零件)
        self.die_to_parts = {}
        for p_id, p in self.parts.items():
            d_id = p.die_id
            if d_id is None:
                continue
            if d_id not in self.die_to_parts:
                self.die_to_parts[d_id] = []
            self.die_to_parts[d_id].append(p_id)
        return part_ids

    def _fetch_die(self) -> list[int]:
        # 1. 获取生产线上的模具
        dies = db.session.query(Die).filter(Die.line_id == self.line_id).all()
        self.dies = {die.id: die for die in dies}
        die_ids = list(self.dies.keys())
        return die_ids

    def _compute_urgency(self):
        """
        计算每个零件的紧急度 = 次日消耗量 / 当前库存
        - 库存为0时设为极大值999（最高优先级）
        - 无需求时设为1.0（最低优先级）
        - 限制权重范围在 1x - 50x
        
        将零件紧急度映射到模具（取最大紧急度）
        """
        self.urgency = {}  # {part_id: urgency_value}
        
        for p_id, cons in self.consumption.items():
            if len(cons) < 2:
                self.urgency[p_id] = 1.0
                continue
                
            next_day_cons = cons[1]  # 第二天的消耗量
            initial_stock = self.initial_inventory.get(p_id, 0)
            
            if initial_stock == 0:
                self.urgency[p_id] = 999.0  # 最高优先级
            elif next_day_cons == 0:
                self.urgency[p_id] = 1.0  # 无需求，最低优先级
            else:
                self.urgency[p_id] = next_day_cons / initial_stock
        
        # 限制权重范围在 1x - 50x
        for p_id in self.urgency:
            self.urgency[p_id] = min(self.urgency[p_id], 50.0)
        
        # 将零件紧急度映射到模具（取最大紧急度）
        self.die_priority = {}
        for d_id, p_ids in self.die_to_parts.items():
            if p_ids:
                max_urgency = max(self.urgency.get(p_id, 1.0) for p_id in p_ids)
                self.die_priority[d_id] = max_urgency
            else:
                self.die_priority[d_id] = 1.0
        
        # 调试日志
        print("DEBUG: part urgency:", {k: f"{v:.2f}" for k, v in self.urgency.items()})
        print("DEBUG: die priority:", {k: f"{v:.2f}" for k, v in self.die_priority.items()})

    def _sanity_checks(self):
        """Prints diagnostics to help find infeasible constraints."""
        # Check day capacities
        for i, d_str in enumerate(self.dates):
            cap = (
                self.day_capacity[i]
                if self.day_capacity and i < len(self.day_capacity)
                else None
            )
            print(f"DEBUG: sanity day {d_str} capacity={cap}")
        # Check dunnage capacities vs initial inventory
        for d_id, cap in (self.dunnage_stock_capacity or {}).items():
            related = [
                p_id
                for p_id, p in self.parts.items()
                if getattr(p, "dunnage_id", None) == d_id
            ]
            init = sum(self.initial_inventory.get(p_id, 0) for p_id in related)
            if init > cap:
                print(
                    f"DEBUG: sanity dunnage {d_id} initial_stock {init} > capacity {cap}"
                )
        # Check consumption shapes
        for p_id, cons in (self.consumption or {}).items():
            if len(cons) != self.days_count:
                print(
                    f"DEBUG: sanity consumption length mismatch for part {p_id}: {len(cons)} vs {self.days_count}"
                )

        # Additional checks: any day capacity zero
        zeros = [d for d, c in zip(self.dates, self.day_capacity) if c == 0]
        if zeros:
            print(f"DEBUG: sanity zero capacity days: {zeros}")

    def solve(self):
        # Run pre-sanity diagnostics to detect obvious infeasible inputs
        try:
            self._sanity_checks()
        except Exception as e:
            print("DEBUG: sanity_checks error:", e)
        # quick checks
        for d_str, cap in zip(self.dates, self.day_capacity):
            if cap < 120:
                print(f"DEBUG: warning - day {d_str} capacity {cap} < 120")

        # 校验锁定任务与日容量的兼容性：如果某任务被锁定为必须在某日生产，但该日可用时间小于最小生产时长（120），则必然不可行
        if self.pinned_tasks:
            for task in self.pinned_tasks:
                try:
                    if task.get("is_day_pinned"):
                        d_str = task["day_id"]
                        if d_str in self.dates:
                            t_idx = self.dates.index(d_str)
                            if self.day_capacity[t_idx] < 120:
                                raise RuntimeError(
                                    f"Infeasible: day {d_str} capacity {self.day_capacity[t_idx]} < 120 but task pinned."
                                )
                except (KeyError, TypeError):
                    # 忽略格式异常的任务记录，保守跳过
                    continue

        # 诊断：如果没有可调度的模具，直接返回每日空任务
        if not self.dies:
            print("DEBUG: no dies available after filtering — returning empty schedule")
            return [{"date": d, "tasks": []} for d in self.dates]

        # 诊断：统计每日产能被 day-pinned 任务占用的最小分钟数（每个被锁定的模具至少 120 分钟）
        pinned_minutes_per_day = {d: 0 for d in self.dates}
        for task in self.pinned_tasks or []:
            try:
                if task.get("is_day_pinned"):
                    d_str = task["day_id"]
                    d_id = task["die_id"]
                    if d_str in self.dates and d_id in self.dies:
                        pinned_minutes_per_day[d_str] += 120
            except Exception:
                continue
        for d_str, mins in pinned_minutes_per_day.items():
            cap = self.day_capacity[self.dates.index(d_str)]
            if mins > cap:
                print(
                    f"DEBUG: infeasible: pinned tasks require {mins}min on {d_str} but capacity is {cap}min"
                )
                print("DEBUG: aborting solve due to pinned-vs-capacity conflict")
                return None

        # Extra diagnostics to help find infeasible model construction
        print(f"DEBUG: dies count={len(self.dies)} ids={list(self.dies.keys())}")
        print(f"DEBUG: parts count={len(self.parts)}")
        print(f"DEBUG: die->parts mapping keys={list(self.die_to_parts.keys())}")
        print(f"DEBUG: pinned_tasks total={len(self.pinned_tasks or [])}")
        for task in self.pinned_tasks or []:
            d_id = task.get("die_id")
            d_str = task.get("day_id")
            present = d_id in self.dies
            print(
                f"DEBUG: pinned task die={d_id} day={d_str} present={present} is_day_pinned={task.get('is_day_pinned')} quantity={task.get('quantity')}"
            )
        print(
            "DEBUG: die akz values:",
            {d_id: getattr(die, "akz", None) for d_id, die in self.dies.items()},
        )

        model = cp_model.CpModel()

        # 变量定义
        # produce_vars[die_id, day_idx]: bool, 是否在该日生产该模具
        produce_vars = {}
        # qty_vars[die_id, day_idx]: int, 生产量
        qty_vars = {}
        # minutes_vars[die_id, day_idx]: int, 生产所用分钟数（用于填满每天工作）
        minutes_vars = {}
        # 记录每个 (die,day) 的上下界以便后续可行性判断
        minutes_upper_map = {}
        qty_upper_map = {}

        # 预估最大产量与分钟数上界 (按每天可用时间设置上界，避免域不兼容)
        for d_id, die in self.dies.items():
            akz = die.akz or 1
            for t in range(self.days_count):
                produce_vars[d_id, t] = model.new_bool_var(f"produce_{d_id}_{t}")
                # 使用当天的可用分钟数来计算当天最大产量，若 day_capacity 未设置则回退到 1440
                day_minutes = (
                    self.day_capacity[t]
                    if (self.day_capacity and t < len(self.day_capacity))
                    else 1440
                )
                # minutes 的上界应不超过当天可用分钟
                minutes_upper = max(day_minutes, 0)
                minutes_vars[d_id, t] = model.new_int_var(
                    0, minutes_upper, f"minutes_{d_id}_{t}"
                )
                max_qty_day = akz * max(day_minutes, 0)
                # 给上界留一点冗余因子，但不超过单次最大产量3000
                qty_upper = min(max_qty_day * 2, 3000)
                qty_vars[d_id, t] = model.new_int_var(0, qty_upper, f"qty_{d_id}_{t}")

                minutes_upper_map[(d_id, t)] = minutes_upper
                qty_upper_map[(d_id, t)] = qty_upper

        # 零件库存变量
        stock_vars = {}
        for p_id in self.parts.keys():
            for t in range(self.days_count):
                # 假设库存上限比较大
                # Allow negative stock to represent deficits so balance equations remain feasible
                stock_vars[p_id, t] = model.new_int_var(
                    -1000000, 1000000, f"stock_{p_id}_{t}"
                )

        # 约束实现
        for t in range(self.days_count):
            # 1. 每日最大生产时间限制
            time_expr = []
            for d_id, die in self.dies.items():
                akz = die.akz or 1
                # 使用预先创建的 minutes_vars 作为每天模具生产时间变量
                minutes_var = minutes_vars[d_id, t]
                # 模具产量 = 生产时间 * akz
                model.add(qty_vars[d_id, t] == minutes_var * akz).with_name(
                    f"qty_eq_minutes_{d_id}_{t}"
                )
                # 如果生产，则至少 120 分钟
                model.add(minutes_var >= 120 * produce_vars[d_id, t]).with_name(
                    f"min_prod_time_{d_id}_{t}"
                )
                time_expr.append(minutes_var)
            # 每天总生产时间 <= 每天可用时间
            model.add(sum(time_expr) <= self.day_capacity[t]).with_name(
                f"daily_time_{t}"
            )

            # 每天至少有一个任务（可选约束，仅当日可用时间大于120分钟时启用）
            if self.day_capacity[t] > 120:
                # 仅把在当日有足够分钟上界满足最小生产时长（120）的模具视为可选候选
                available_produces = []
                for d_id in self.dies.keys():
                    key = (d_id, t)
                    if key not in produce_vars:
                        continue
                    # 需要当天分钟上界 >= 120 且 qty 上界足以容纳最小产量
                    akz = getattr(self.dies[d_id], "akz", 1) or 1
                    if (
                        minutes_upper_map.get(key, 0) >= 120
                        and qty_upper_map.get(key, 0) >= akz * 120
                    ):
                        available_produces.append(produce_vars[key])
                if available_produces:
                    model.add(sum(available_produces) >= 1).with_name(
                        f"require_daily_prod_{t}"
                    )
                else:
                    # no available dies to schedule this day (all dies filtered/or cannot meet min duration), skip requirement
                    print(
                        f"DEBUG: no viable dies for daily requirement on {self.dates[t]} (capacity {self.day_capacity[t]})"
                    )
                    pass

            # 2. 库存平衡
            for p_id in self.parts.keys():
                die_id = self.parts[p_id].die_id
                prev_stock = (
                    self.initial_inventory[p_id] if t == 0 else stock_vars[p_id, t - 1]
                )  # 上一天零件的库存
                # 零件库存 == 上一天库存 + 今天生产 - 今天消耗
                # 模具生产1次 == 该零件生产1次
                model.add(
                    stock_vars[p_id, t]
                    == prev_stock + qty_vars[die_id, t] - self.consumption[p_id][t]
                ).with_name(f"stock_balance_{p_id}_{t}")


            # 3. 器具容量限制：同一器具下所有相关零件的库存总和不能超过起始日容量上限
            for dun_id, dunnage in self.dunnages.items():
                related_parts = [
                    p_id for p_id, p in self.parts.items() if p.dunnage_id == dun_id
                ]
                if not related_parts:
                    continue

                model.add(
                    sum(stock_vars[p_id, t] for p_id in related_parts)
                    <= self.dunnage_stock_capacity[dun_id]
                ).with_name(f"dunnage_cap_{dun_id}_{t}")

            # 4. 零件最小库存约束（软约束）：通过惩罚项鼓励库存不低于 min（或 > 0）
            # 使用软约束避免无解：当库存不足时产生惩罚，求解器会尽量满足
            min_stock_penalty = {}  # {p_id: penalty_var}
            for p_id, part in self.parts.items():
                part_min = getattr(part, "min", None)
                # 无论 Part.min 是否为 0 或空，都添加惩罚项
                # 如果 min > 0，惩罚库存低于 min 的部分；否则惩罚库存 < 0 的部分
                if part_min and part_min > 0:
                    # 创建缺货惩罚变量：max(0, part_min - stock_vars[p_id, t])
                    # 当 stock >= min 时，penalty = 0；当 stock < min 时，penalty = min - stock
                    penalty_var = model.new_int_var(0, part_min, f"min_penalty_{p_id}_{t}")
                    min_stock_penalty[p_id] = penalty_var
                    # 约束：penalty >= part_min - stock_vars，即 penalty >= max(0, min - stock)
                    model.add(penalty_var >= part_min - stock_vars[p_id, t]).with_name(
                        f"min_penalty_constraint_{p_id}_{t}"
                    )
                else:
                    # min 为空或为 0：惩罚库存 < 0 的部分（不缺货即可）
                    # 创建缺货惩罚变量：max(0, 0 - stock_vars[p_id, t]) = max(0, -stock)
                    penalty_var = model.new_int_var(0, 1000000, f"min_penalty_{p_id}_{t}")
                    min_stock_penalty[p_id] = penalty_var
                    # 约束：penalty >= -stock_vars，即 penalty >= max(0, -stock)
                    model.add(penalty_var >= -stock_vars[p_id, t]).with_name(
                        f"min_penalty_constraint_{p_id}_{t}"
                    )

        # 5. 锁定任务
        for task in self.pinned_tasks:
            d_id = task["die_id"]
            d_str = task["day_id"]
            # 锁定任务不在排产时间范围内，跳过
            if d_str not in self.dates:
                continue
            t = self.dates.index(d_str)
            key = (d_id, t)  # key由die_id和day_id组成
            # 锁定任务不在该线体对应的模具中，跳过
            if key not in produce_vars:
                continue
            # 如果该 die/day 的分钟或产量上界无法支持最小生产时长，则也跳过并警告
            akz = getattr(self.dies.get(d_id), "akz", 1) or 1
            if (
                minutes_upper_map.get(key, 0) < 120
                or qty_upper_map.get(key, 0) < akz * 120
            ):
                print(
                    f"DEBUG: skipping pinned task for die {d_id} on {d_str} — insufficient per-day bounds minutes_upper={minutes_upper_map.get(key)} qty_upper={qty_upper_map.get(key)}"
                )
                continue
            if task.get("is_day_pinned"):
                model.add(produce_vars[key] == 1).with_name(f"pinned_day_{d_id}_{t}")
            if task.get("is_quantity_pinned") and task.get("quantity") is not None:
                qty_val = task["quantity"]
                if qty_val > 3000:
                    print(
                        f"DEBUG: skipping pinned quantity for die {d_id} on {d_str} — quantity {qty_val} exceeds per-run limit 3000"
                    )
                else:
                    model.add(qty_vars[key] == qty_val).with_name(
                        f"pinned_qty_{d_id}_{t}"
                    )

        # 6. 如果 produce_vars 为 0，则 qty_vars 为 0
        for (d_id, t), v in produce_vars.items():
            model.add(qty_vars[d_id, t] == 0).with_name(
                f"qty_zero_if_not_prod_{d_id}_{t}"
            ).only_enforce_if(v.Not())
            # 如果生产，qty 必须大于 0 (已经在 120min 约束中体现)

        # 7. 目标函数：加权最大化生产时间，高优先级模具获得更高权重
        # 紧急度越高（消耗/库存比越大），越优先安排生产
        fill_expr = []
        for d_id in self.dies.keys():
            weight = self.die_priority.get(d_id, 1.0)
            for t in range(self.days_count):
                fill_expr.append(weight * minutes_vars[d_id, t])
        
        # 7.1 最小库存惩罚项：最小化库存低于 min 的缺货量
        # 惩罚权重设为生产权重的 10 倍，确保优先满足最小库存
        penalty_expr = []
        for p_id, penalty_var in min_stock_penalty.items():
            # 累加所有天的缺货惩罚
            penalty_expr.append(penalty_var)
        # 使用 minimize 将惩罚加到目标函数中（OR-Tools 支持多目标：先最大化，再最小化）
        # 这里通过加权方式：最大化生产时间 - 惩罚项 * 大系数
        total_penalty = sum(penalty_expr)
        
        # 使用 CP-SAT 的 AddLinearExpressionInObjective 实现复合目标
        # 先最大化生产时间，再最小化库存惩罚（通过负权重）
        model.maximize(sum(fill_expr) - 1000 * total_penalty)

        # 求解
        solver = cp_model.CpSolver()
        status = solver.solve(model)
        print("DEBUG: solver status=", status)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            results = []
            for t, d_str in enumerate(self.dates):
                day_tasks = []
                for d_id, die in self.dies.items():
                    if solver.Value(produce_vars[d_id, t]):
                        q = solver.Value(qty_vars[d_id, t])

                        # 获取模具关联的器具信息
                        dunnage_info = None
                        related_p_ids = self.die_to_parts.get(d_id, [])
                        part = None
                        if related_p_ids:
                            part = self.parts[related_p_ids[0]]
                        d = getattr(part, "dunnage", None)
                        if d:
                            dunnage_info = {
                                "id": d.id,
                                "name": d.name,
                                "available_quantity": getattr(
                                    d, "available_quantity", None
                                ),
                            }

                        day_tasks.append(
                            {
                                "die_id": d_id,
                                "die_name": die.name,
                                "die_code": die.code,
                                "quantity": q,
                                "duration_minutes": q / (die.akz or 1),
                                "dunnage": dunnage_info,
                            }
                        )
                results.append({"date": d_str, "tasks": day_tasks})
            return results
        else:
            print("DEBUG: no feasible solution")
            return None
