from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class Day:
    id: str
    working_time: int
    out_minutes: int
    pass


@dataclass
class Die:
    id: str
    min_batch: int
    production_time: int  # 每个 hits 所需的时间（单位：秒）


@dataclass
class Part:
    id: str
    initial_stock: int
    max_stock: int


@dataclass
class DiePart:
    die_id: str
    part_id: str
    yield_rate: int


@dataclass
class PartDemand:
    day_id: str
    part_id: str
    demand: int


@dataclass
class Task:
    id: str
    day_id: str
    die_id: str
    order: Any = None
    quantity: Any = None
    active: Any = None
    start: Any = None
    duration: Any = None
    end: Any = None
    interval: Any = None
    pinned_order: int = None
    pinned_quantity: int = None


@dataclass
class ScheduleData:
    day_map: Dict[str, Day]
    die_map: Dict[str, Die]
    part_map: Dict[str, Part]
    die_part_map: Dict[Tuple[str, str], DiePart]  # （模具，零件）：数量映射
    part_demand_map: Dict[Tuple[str, str], PartDemand]  # （日期，零件）：需求映射
    tasks: List[Task]   # 占位与用户安排的任务


def get_default_data() -> ScheduleData:
    day_ids = ["2026-4-7", "2026-4-8", "2026-4-9", "2026-4-10", "2026-4-11", "2026-4-12", "2026-4-13"]
    day_map = {day_id: Day(day_id, 480, 0) for day_id in day_ids}

    dies = [
        Die("Die_A", 100, 120),  # 每个 hits 120 秒 (2 分钟)
        Die("Die_B", 50, 180),   # 每个 hits 180 秒 (3 分钟)
        Die("Die_C", 80, 240),   # 每个 hits 240 秒 (4 分钟)
    ]
    die_map = {d.id: d for d in dies}

    parts = [
        Part("Part_1", 1000, 3000),
        Part("Part_2", 1000, 1800),
        Part("Part_3", 1000, 1500),
        Part("Part_4", 1000, 1500),
    ]
    part_map = {p.id: p for p in parts}

    die_parts = [
        DiePart("Die_A", "Part_1", 1),
        DiePart("Die_A", "Part_2", 1),
        DiePart("Die_B", "Part_3", 1),
        DiePart("Die_C", "Part_4", 1),
    ]
    die_part_map = {(dp.die_id, dp.part_id): dp for dp in die_parts}

    demands = [
        ("2026-4-7", "Part_1", 1000),
        ("2026-4-7", "Part_2", 1000),
        ("2026-4-8", "Part_2", 1000),
        ("2026-4-8", "Part_3", 1000),
        ("2026-4-8", "Part_4", 1000),
        ("2026-4-9", "Part_3", 1000),
        ("2026-4-10", "Part_4", 1000),
        ("2026-4-11", "Part_1", 1000),
        ("2026-4-12", "Part_2", 1000),
        ("2026-4-13", "Part_3", 1000),
    ]
    part_demand_map = {
        (day_id, part_id): PartDemand(day_id, part_id, demand)
        for day_id, part_id, demand in demands
    }

    tasks = []
    i = 0
    # 每个模具每天安排一个任务
    for day_id, day in day_map.items():
        for die_id, die in die_map.items():
            tasks.append(Task(str(i),day_id, die_id))
            i+=1

    return ScheduleData(day_map, die_map, part_map, die_part_map, part_demand_map, tasks)
