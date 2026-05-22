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
                    DunnageInventoryHistory.day == self.start_date
                )
            )
            dun_inv_res = db.session.execute(dun_inv_query).mappings().all()
            for row in dun_inv_res:
                self.empty_dunnages[row['dunnage_id']] = row['empty_quantity'] or 0

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
            # sum(qty / akz) <= day_capacity
            # 线性化: sum(qty * 1) <= day_capacity * akz ... 不对，akz 每个 die 不同
            # sum(qty_vars[d_id, t] // akz) <= day_capacity[t]
            time_expr = []
            for d_id, die in self.dies.items():
                akz = die.akz or 1
                # qty = minutes * akz
                # 创建一个时间变量
                minutes_var = model.new_int_var(0, self.day_capacity[t], f'minutes_{d_id}_{t}')
                model.add(qty_vars[d_id, t] == minutes_var * akz)
                # 此外，如果生产，则至少 120 分钟
                model.add(minutes_var >= 120 * produce_vars[d_id, t])
                time_expr.append(minutes_var)
            
            model.add(sum(time_expr) <= self.day_capacity[t])

            # 2. 库存平衡
            for p_id in self.parts.keys():
                die_id = self.parts[p_id].die_id
                prev_stock = self.initial_inventory[p_id] if t == 0 else stock_vars[p_id, t-1]
                # 这里的 qty 是模具产量。如果一个模具产出多个零件，这里需要调整。目前假设 1:1 或模具产出即零件产出
                model.add(stock_vars[p_id, t] == prev_stock + qty_vars[die_id, t] - self.consumption[p_id][t])

            # 3. 器具容量限制：同一器具下所有相关零件的库存总和不能超过起始日容量上限
            for dun_id, dunnage in self.dunnages.items():
                related_parts = [p_id for p_id, p in self.parts.items() if p.dunnage_id == dun_id]
                if not related_parts: continue

                model.add(
                    sum(stock_vars[p_id, t] for p_id in related_parts)
                    <= self.dunnage_stock_capacity[dun_id]
                )

        # 4. 锁定任务
        for task in self.pinned_tasks:
            d_id = task['die_id']
            d_str = task['day_id']
            t = self.dates.index(d_str)
            if task['is_day_pinned']:
                model.add(produce_vars[d_id, t] == 1)
            if task['is_quantity_pinned'] and task['quantity'] is not None:
                model.add(qty_vars[d_id, t] == task['quantity'])

        # 5. 如果 produce_vars 为 0，则 qty_vars 为 0
        for (d_id, t), v in produce_vars.items():
            model.add(qty_vars[d_id, t] == 0).only_enforce_if(v.Not())
            # 如果生产，qty 必须大于 0 (已经在 120min 约束中体现)

        # 目标函数：优化优先级
        # 优先级逻辑：库存越低（相对于未来需求），优先级越高。
        # 我们希望尽量满足需求，避免库存为0（已经约束了 stock >= 0）。
        # 为了体现优先级变化，我们可以最大化期末总库存，或者最小化由于库存低带来的“风险值”。
        # 用户提到“哪天生产取决于使用量和库存”，我们可以引入一个基于库存水平的惩罚。
        
        # 简单的目标：最小化 stock 的总和的负值（即最大化库存），
        # 但这会导致一直生产。
        # 更好的目标：满足需求的前提下，尽量推迟生产以节省器具，或者尽早生产以满足紧缺。
        # 这里我们按用户要求的优先级：零件使用量大、库存低的优先。
        
        obj_expr = []
        for p_id in self.parts.keys():
            # 计算该零件的总需求，用于归一化
            total_cons = sum(self.consumption[p_id]) or 1
            for t in range(self.days_count):
                # 权重：随时间递减，鼓励尽早解决紧缺
                # 库存权重：库存越低，贡献的目标值越大（如果目标是 Maximize）
                # 我们可以使用一个倒置的库存衡量： (Total_7day_Cons - stock)
                weight = (self.days_count - t) 
                obj_expr.append(stock_vars[p_id, t] * weight)

        model.maximize(sum(obj_expr))
        
        # 求解
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        status = solver.solve(model)
        
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
            return None
