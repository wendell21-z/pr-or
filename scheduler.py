import datetime
from typing import List, Dict, Any
from sqlalchemy import select, and_, func
from ortools.sat.python import cp_model
from sqlalchemy.orm import InstrumentedAttribute

from models import (
    db, CarPart, CarUsage, Part, PartInventory,
    Task, Dunnage, DunnageInventoryHistory, Day, WorkingTime, Die,
)
from utils import ensure_day

class ProductionScheduler:
    def __init__(self, line_id: int, start_date_str: str, days_count: int = 7):
        self.constraints = {
            'daily_time':True,
            'dunnage_capacity':True,
            'deficit_objective':False,
            'pinned_tasks':False,
            'ensure_next_day_usage':False,
            'require_daily_production':False,
        }
        self.pinned_tasks = None
        self.dunnage_stock_capacity = None
        self.empty_dunnages = None
        self.dunnages = None
        self.start_date_str = start_date_str
        self.day_capacity = None
        self.start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        self.days_count = days_count
        self.dates = [(self.start_date + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days_count)]
        self.initial_inventory = None   # 零件初始库存
        self.consumption = None # 零件日需求量
        self.die_to_parts = None
        self.parts = None
        self.dies = None
        self.line_id = line_id


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

        working_time_texts = {
            day.woking_time
            for day in day_map.values()
            if day.woking_time is not None
        }
        working_time_map = {}
        if working_time_texts:
            working_times = db.session.query(WorkingTime).filter(
                WorkingTime.text.in_(working_time_texts)
            ).all()
            working_time_map = {
                working_time.text: working_time.minutes
                for working_time in working_times
            }

        self.day_capacity = [0] * self.days_count
        for i, d_str in enumerate(self.dates):
            day = day_map[d_str]
            working_minutes = working_time_map.get(day.woking_time) or 0
            out_minutes = day.out_minutes or 0
            self.day_capacity[i] = working_minutes + out_minutes

    def fetch_data(self):
        # 1. 获取生产线上的模具
        die_ids = self._fetch_die()

        # 2. 获取相关零件
        part_ids = self._fetch_part(die_ids)

        # 3. 获取需求 (Consumption)
        self._compute_consumption(part_ids)

        # 4. 获取初始库存
        self._fetch_part_inventory()

        # 5. 获取并补齐每日可用时间
        self._fetch_day_capacity()

        # 6. 获取器具数据
        # 根据零件获取
        dunnage_ids = list(set(p.dunnage_id for p in self.parts.values() if p.dunnage_id))
        self.dunnages = {}
        if dunnage_ids:
            dun_query = select(Dunnage).where(Dunnage.id.in_(dunnage_ids))
            dun_res = db.session.execute(dun_query).scalars().all()
            self.dunnages = {d.id: d for d in dun_res}

        # 关联零件和器具，计算初始可用总量
        for p_id, p in self.parts.items():
            if p.dunnage_id:
                # attach dunnage dict to Part object for later use
                setattr(p, 'dunnage', self.dunnages.get(p.dunnage_id))

        # 7. 获取 start_date 当天器具库存，用于计算同器具零件库存上限
        self.empty_dunnages = {d_id: 0 for d_id in dunnage_ids}
        if dunnage_ids:
            dun_inv_query = select(DunnageInventoryHistory).where(
                and_(
                    DunnageInventoryHistory.dunnage_id.in_(dunnage_ids),
                    DunnageInventoryHistory.day_id == self.start_date_str
                )
            )
            dun_inv_res = db.session.execute(dun_inv_query).scalars().all()
            for row in dun_inv_res:
                self.empty_dunnages[row.dunnage_id] = row.empty_quantity or 0


        self.dunnage_stock_capacity = {}
        for d_id, dunnage in self.dunnages.items():
            related_parts = [p_id for p_id, p in self.parts.items() if p.dunnage_id == d_id]
            initial_stock = sum(self.initial_inventory.get(p_id, 0) for p_id in related_parts)
            stock_capacity = self.empty_dunnages[d_id] * (dunnage.capacity or 1) + initial_stock
            self.dunnage_stock_capacity[d_id] = stock_capacity
            setattr(dunnage, 'available_quantity', stock_capacity)

        # 8. 获取锁定任务
        self.pinned_tasks = []
        task_query = select(Task).where(
            and_(
                Task.die_id.in_(die_ids),
                Task.day_id.in_(self.dates)
            )
        )
        task_res = db.session.execute(task_query).mappings().all()
        self.pinned_tasks = task_res

    def _fetch_part_inventory(self):
        part_ids = list(self.parts.keys())
        sd_str = self.start_date.isoformat()
        inv_map = {}
        try:
            inv_res = db.session.query(PartInventory).filter(
                PartInventory.part_id.in_(part_ids),
                PartInventory.day_id == sd_str
            ).all()
            inv_map = {row.part_id: row.quantity for row in inv_res}
        except Exception:
            inv_map = {}
        self.initial_inventory = {p_id: inv_map.get(p_id, 0) for p_id in self.parts}

    def _compute_consumption(self, part_ids: list[Any]):
        # Consumption(part, day) = Sum(car_usage(car, day) * car_part(car, part))
        self.consumption = {p_id: [0] * self.days_count for p_id in part_ids}
        usage_query = select(
            CarUsage.day_id,
            CarPart.part_id,
            func.sum(CarUsage.usage * CarPart.usage).label('total_usage')
        ).join(
            CarPart, CarUsage.car_id == CarPart.car_id
        ).where(
            and_(
                CarPart.part_id.in_(part_ids),
                CarUsage.day_id.in_(self.dates)
            )
        ).group_by(CarUsage.day_id, CarPart.part_id)
        usage_res = db.session.execute(usage_query).mappings().all()
        for row in usage_res:
            d_idx = self.dates.index(row['day_id'])
            self.consumption[row['part_id']][d_idx] = int(row['total_usage'])

    def _fetch_part(self, die_ids: list[InstrumentedAttribute[int]]) -> list[Any]:
        # Fetch Part ORM objects instead of mapping to dicts so scheduler can
        # access model attributes directly.
        parts_objs = db.session.query(Part).filter(Part.die_id.in_(die_ids)).all()
        self.parts = {p.id: p for p in parts_objs}
        part_ids = list(self.parts.keys())

        # 模具与零件的对应关系 (假设一个模具产出一个零件，或者一个模具产出多个零件)
        self.die_to_parts = {}
        for p_id, p in self.parts.items():
            d_id = p.die_id
            if d_id not in self.die_to_parts:
                self.die_to_parts[d_id] = []
            self.die_to_parts[d_id].append(p_id)
        return part_ids

    def _fetch_die(self) -> list[InstrumentedAttribute[int]]:
        # 1. 获取生产线上的模具
        dies = db.session.query(Die).filter(Die.line_id == self.line_id).all()
        self.dies = {die.id: die for die in dies}
        die_ids = list(self.dies.keys())
        return die_ids

    def solve(self):
        if self.pinned_tasks:
            for task in self.pinned_tasks:
                print("DEBUG: pinned task:", task)
        # quick checks
        for d_str, cap in zip(self.dates, self.day_capacity):
            if cap < 120:
                print(f"DEBUG: warning - day {d_str} capacity {cap} < 120")
        # 校验锁定任务与日容量的兼容性：如果某任务被锁定为必须在某日生产，但该日可用时间小于最小生产时长（120），则必然不可行
        if self.pinned_tasks:
            for task in self.pinned_tasks:
                try:
                    if task.get('is_day_pinned'):
                        d_str = task['day_id']
                        if d_str in self.dates:
                            t_idx = self.dates.index(d_str)
                            if self.day_capacity[t_idx] < 120:
                                raise RuntimeError(f"Infeasible: day {d_str} capacity {self.day_capacity[t_idx]} < 120 but task pinned.")
                except Exception:
                    # 忽略格式异常的任务记录，保守跳过
                    continue
        model = cp_model.CpModel()
        
        # 变量定义
        # produce_vars[die_id, day_idx]: bool, 是否在该日生产该模具
        produce_vars = {}
        # qty_vars[die_id, day_idx]: int, 生产量
        qty_vars = {}
        
        # 预估最大产量 (基于全天生产)
        for d_id, die in self.dies.items():
            akz = die.akz or 1
            max_qty = akz * 1440
            for t in range(self.days_count):
                produce_vars[d_id, t] = model.new_bool_var(f'produce_{d_id}_{t}')
                qty_vars[d_id, t] = model.new_int_var(0, max_qty * 2, f'qty_{d_id}_{t}')

        # 零件库存变量
        stock_vars = {}
        for p_id in self.parts.keys():
            for t in range(self.days_count):
                # 假设库存上限比较大
                stock_vars[p_id, t] = model.new_int_var(0, 1000000, f'stock_{p_id}_{t}')

        # 约束实现
        for t in range(self.days_count):
            # 1. 每日最大生产时间限制
            time_expr = []
            for d_id, die in self.dies.items():
                akz = die.akz or 1
                # 每个模具每天的生产时间
                minutes_var = model.new_int_var(0, self.day_capacity[t], f'minutes_{d_id}_{t}')
                # 模具产量 = 生产时间 * akz
                model.add(qty_vars[d_id, t] == minutes_var * akz).with_name(f'qty_eq_minutes_{d_id}_{t}')
                # 如果生产，则至少 120 分钟
                model.add(minutes_var >= 120 * produce_vars[d_id, t]).with_name(f'min_prod_time_{d_id}_{t}')
                time_expr.append(minutes_var)
            # 每天总生产时间 <= 每天可用时间
            model.add(sum(time_expr) <= self.day_capacity[t]).with_name(f'daily_time_{t}')

            # 每天至少有一个任务（可选约束）
            if self.constraints.get('require_daily_production', False):
                model.add(sum(produce_vars[d_id, t] for d_id in self.dies.keys()) >= 1).with_name(f'require_daily_prod_{t}')

            # 2. 库存平衡
            for p_id in self.parts.keys():
                die_id = self.parts[p_id].die_id
                prev_stock = self.initial_inventory[p_id] if t == 0 else stock_vars[p_id, t-1]  # 上一天零件的库存
                # 零件库存 ==  上一天库存 + 今天生产 - 今天消耗
                # 模具生产1次 == 该零件生产1次
                model.add(stock_vars[p_id, t] == prev_stock + qty_vars[die_id, t] - self.consumption[p_id][t]).with_name(f'stock_balance_{p_id}_{t}')

            # 3. 器具容量限制：同一器具下所有相关零件的库存总和不能超过起始日容量上限
            for dun_id, dunnage in self.dunnages.items():
                related_parts = [p_id for p_id, p in self.parts.items() if p.dunnage_id == dun_id]
                if not related_parts: continue

                model.add(
                    sum(stock_vars[p_id, t] for p_id in related_parts)
                    <= self.dunnage_stock_capacity[dun_id]
                ).with_name(f'dunnage_cap_{dun_id}_{t}')


        # 4. 锁定任务
        for task in self.pinned_tasks:
            d_id = task['die_id']
            d_str = task['day_id']
            t = self.dates.index(d_str)
            if task['is_day_pinned']:
                model.add(produce_vars[d_id, t] == 1).with_name(f'pinned_day_{d_id}_{t}')
            if task['is_quantity_pinned'] and task['quantity'] is not None:
                model.add(qty_vars[d_id, t] == task['quantity']).with_name(f'pinned_qty_{d_id}_{t}')

        # 5. 如果 produce_vars 为 0，则 qty_vars 为 0
        for (d_id, t), v in produce_vars.items():
            model.add(qty_vars[d_id, t] == 0).with_name(f'qty_zero_if_not_prod_{d_id}_{t}').only_enforce_if(v.Not())
            # 如果生产，qty 必须大于 0 (已经在 120min 约束中体现)

        # 目标函数：优先满足当前库存相对用量不足的零件
        # 定义 deficit = max(0, consumption - stock)。尽量最大化 deficit 的补足（即优先生产 deficit 较大的条目）。
        if self.constraints.get('deficit_objective', False):
            deficit_vars = {}
            obj_expr = []
            BIG = 10**6
            for p_id in self.parts.keys():
                for t in range(self.days_count):
                    dvar = model.new_int_var(0, BIG, f'deficit_{p_id}_{t}')
                    deficit_vars[p_id, t] = dvar
                    # deficit >= consumption - stock
                    model.add(dvar >= self.consumption[p_id][t] - stock_vars[p_id, t]).with_name(f'deficit_lowerbound_{p_id}_{t}')
                    # 权重：鼓励尽早解决紧缺
                    weight = (self.days_count - t)
                    obj_expr.append(dvar * weight)

            model.maximize(sum(obj_expr))
        else:
            # No objective: find any feasible solution
            pass
        
        # 求解
        solver = cp_model.CpSolver()
        solver.parameters.log_search_progress = True
        solver.parameters.cp_model_presolve = True
        solver.parameters.log_to_stdout = True
        status = solver.solve(model)
        print('DEBUG: solver status=', status)
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
                        if related_p_ids:
                            part = self.parts[related_p_ids[0]]
                        d = getattr(part, 'dunnage', None)
                        if d:
                            dunnage_info = {
                                "id": d.id,
                                "name": d.name,
                                "available_quantity": getattr(d, 'available_quantity', None)
                            }

                        day_tasks.append({
                            "die_id": d_id,
                            "die_name": die.name,
                            "die_code": die.code,
                            "quantity": q,
                            "duration_minutes": q / (die.akz or 1),
                            "dunnage": dunnage_info
                        })
                results.append({
                    "date": d_str,
                    "tasks": day_tasks
                })
            return results
        else:
            print('DEBUG: no feasible solution')
            return None
