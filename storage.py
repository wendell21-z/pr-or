import logging
import os
from contextlib import contextmanager
from datetime import date
from typing import Any, Dict, List

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from db_models import (
    AppData,
    CarPartRecord,
    CarRecord,
    CarUsageRecord,
    DayRecord,
    DieMemoRecord,
    DieRecord,
    DunnageInventoryHistoryRecord,
    DunnageRecord,
    LineRecord,
    PartInventoryRecord,
    PartRecord,
    TaskRecord,
    WorkingTimeRecord,
    get_session_factory,
    init_db,
    load_kv,
    save_kv,
)

# ---------------------------------------------------------------------------
# Default connection string — override via env var or constructor param
# Example: mysql+pymysql://user:pass@localhost:3306/vw_aps_pr?charset=utf8mb4
# ---------------------------------------------------------------------------
DEFAULT_DB_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:root@localhost:3306/vw_aps_pr?charset=utf8mb4",
)


class Storage:
    _LEGACY_KEYS = [
        "working_times", "days", "lines", "dies", "parts", "cars", "car_parts",
        "part_inventory", "dunnages", "dunnage_inventory", "car_usages",
        "solve_status", "solve_results", "memos", "pinned_tasks", "_next_id",
    ]
    _SUPPLEMENTAL_KEYS = ["solve_status", "solve_results", "_next_id"]
    _RELATIONAL_TABLES = {
        "working_time", "day", "line", "die", "part", "car", "car_part",
        "part_inventory", "dunnage", "dunnage_inventory_history", "car_usage",
        "die_memo", "task",
    }

    def __init__(self, db_url: str = None):
        self._db_url = db_url or DEFAULT_DB_URL
        self._engine = None
        self._session_factory = None
        self._use_relational_backend = False

        self.working_times: Dict[str, int] = {}
        self.days: Dict[date, Dict[str, Any]] = {}
        self.lines: Dict[int, Dict[str, Any]] = {}
        self.dies: Dict[int, Dict[str, Any]] = {}
        self.parts: Dict[int, Dict[str, Any]] = {}
        self.cars: Dict[int, Dict[str, Any]] = {}
        self.car_parts: Dict[int, Dict[str, Any]] = {}
        self.part_inventory: Dict[int, Dict[str, Any]] = {}
        self.dunnages: Dict[int, Dict[str, Any]] = {}
        self.dunnage_inventory: Dict[int, Dict[str, Any]] = {}
        self.car_usages: Dict[int, Dict[str, Any]] = {}
        self.solve_status: Dict[int, Dict[str, Any]] = {}
        self.solve_results: Dict[int, List[Dict[str, Any]]] = {}
        self.memos: Dict[int, Dict[str, Any]] = {}
        self.pinned_tasks: List[Dict[str, Any]] = []
        self._next_id: Dict[str, int] = self._default_next_id()

    def init_engine(self, db_url: str = None):
        url = db_url or self._db_url
        self._engine = create_engine(url, pool_pre_ping=True)
        self._session_factory = get_session_factory(self._engine)
        init_db(self._engine)
        self._use_relational_backend = self._detect_relational_backend()
        logging.info("Storage engine initialised: %s", url)
        logging.info("Storage backend mode: %s", "relational" if self._use_relational_backend else "legacy")

    def _detect_relational_backend(self) -> bool:
        if self._engine is None or self._engine.dialect.name != "mysql":
            return False
        table_names = set(inspect(self._engine).get_table_names())
        return self._RELATIONAL_TABLES.issubset(table_names)

    @contextmanager
    def session_scope(self):
        if self._session_factory is None:
            raise RuntimeError("Storage engine not initialised. Call init_engine() first.")
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close_engine(self):
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._use_relational_backend = False
            logging.info("Storage engine closed")

    def get_next_id(self, entity: str) -> int:
        id_val = self._next_id[entity]
        self._next_id[entity] += 1
        return id_val

    def save(self, session: Session = None):
        if session is not None:
            self._save_with_session(session)
            return
        with self.session_scope() as s:
            self._save_with_session(s)

    def _save_with_session(self, session: Session):
        if self._use_relational_backend:
            self._save_relational(session)
            self._save_supplemental(session)
        else:
            self._save_legacy(session)
        logging.debug("Storage saved")

    def load(self, session: Session = None) -> bool:
        if session is not None:
            return self._load_with_session(session)
        with self.session_scope() as s:
            return self._load_with_session(s)

    def _load_with_session(self, session: Session) -> bool:
        if self._use_relational_backend:
            found = self._load_relational(session)
            supplemental_found = self._load_supplemental(session)
            return found or supplemental_found
        return self._load_legacy(session)

    def clear_all(self):
        if self._use_relational_backend:
            with self.session_scope() as s:
                for model in [
                    CarUsageRecord,
                    PartInventoryRecord,
                    DunnageInventoryHistoryRecord,
                    CarPartRecord,
                    TaskRecord,
                    DieMemoRecord,
                    PartRecord,
                    DieRecord,
                    CarRecord,
                    DunnageRecord,
                    LineRecord,
                    DayRecord,
                    WorkingTimeRecord,
                ]:
                    s.query(model).delete()
                s.query(AppData).delete()
        else:
            with self.session_scope() as s:
                s.query(AppData).delete()

        self._reset_state()
        logging.info("Storage cleared")

    def _save_legacy(self, session: Session):
        for key in self._LEGACY_KEYS:
            save_kv(session, key, getattr(self, key))

    def _load_legacy(self, session: Session) -> bool:
        self._reset_state()
        found = False
        for key in self._LEGACY_KEYS:
            data = load_kv(session, key)
            if data:
                found = True
                setattr(self, key, data)
        return found

    def _save_supplemental(self, session: Session):
        for key in self._SUPPLEMENTAL_KEYS:
            save_kv(session, key, getattr(self, key))

    def _load_supplemental(self, session: Session) -> bool:
        found = False
        for key in self._SUPPLEMENTAL_KEYS:
            data = load_kv(session, key)
            if data:
                found = True
                setattr(self, key, data)
        return found

    def _load_relational(self, session: Session) -> bool:
        self._reset_state()

        working_time_rows = session.query(WorkingTimeRecord).all()
        day_rows = session.query(DayRecord).all()
        line_rows = session.query(LineRecord).all()
        die_rows = session.query(DieRecord).all()
        dunnage_rows = session.query(DunnageRecord).all()
        part_rows = session.query(PartRecord).all()
        car_rows = session.query(CarRecord).all()
        car_part_rows = session.query(CarPartRecord).all()
        part_inventory_rows = session.query(PartInventoryRecord).all()
        dunnage_inventory_rows = session.query(DunnageInventoryHistoryRecord).all()
        car_usage_rows = session.query(CarUsageRecord).all()
        memo_rows = session.query(DieMemoRecord).all()
        task_rows = session.query(TaskRecord).all()

        self.working_times = {
            row.text: row.minutes
            for row in working_time_rows
            if row.text is not None
        }
        self.days = {
            date.fromisoformat(row.id): {
                "day": date.fromisoformat(row.id),
                "workingTimeText": row.woking_time,
                "outMinutes": row.out_minutes or 0,
            }
            for row in day_rows
            if row.id
        }
        self.lines = {
            row.id: {
                "id": row.id,
                "code": row.code,
                "description": row.description,
            }
            for row in line_rows
            if row.id is not None
        }
        self.dies = {
            row.id: {
                "id": row.id,
                "code": row.code,
                "name": row.name,
                "akz": row.akz or 0,
                "lineId": row.line_id,
            }
            for row in die_rows
            if row.id is not None
        }
        self.dunnages = {
            row.id: {
                "id": row.id,
                "name": row.name,
                "capacity": row.capacity or 0,
            }
            for row in dunnage_rows
            if row.id is not None
        }
        self.parts = {
            row.id: {
                "id": row.id,
                "code": row.code,
                "name": row.name,
                "min": row.min or 0,
                "dieId": row.die_id,
                "dunnageId": row.dunnage_id,
            }
            for row in part_rows
            if row.id is not None
        }
        self.cars = {
            row.id: {
                "id": row.id,
                "code": row.code,
                "name": row.name,
            }
            for row in car_rows
            if row.id is not None
        }
        self.car_parts = {
            int(row.id): {
                "id": int(row.id),
                "usage": row.usage or 0,
                "carId": row.car_id,
                "partId": row.part_id,
            }
            for row in car_part_rows
            if row.id is not None
        }

        part_code_by_id = {part_id: part["code"] for part_id, part in self.parts.items()}
        self.part_inventory = {
            int(row.id): {
                "id": int(row.id),
                "part": part_code_by_id.get(row.part_id),
                "partId": row.part_id,
                "day": row.day,
                "quantity": row.quantity or 0,
            }
            for row in part_inventory_rows
            if row.id is not None
        }
        self.dunnage_inventory = {
            row.id: {
                "id": row.id,
                "day": row.day,
                "dunnageId": row.dunnage_id,
                "quantity": row.quantity or 0,
                "emptyQuantity": row.empty_quantity or 0,
                "repairQuantity": row.repair_quantity or 0,
                "sealedQuantity": row.sealed_quantity or 0,
                "pendingRepairQuantity": row.pending_repair_quantity or 0,
                "weldingQuantity": row.welding_quantity or 0,
            }
            for row in dunnage_inventory_rows
            if row.id is not None
        }
        self.car_usages = {
            row.id: {
                "id": row.id,
                "carId": row.car_id,
                "day": date.fromisoformat(row.day_id) if row.day_id else None,
                "num": row.usage or 0,
            }
            for row in car_usage_rows
            if row.id is not None and row.day_id
        }
        self.memos = {
            int(row.id): {
                "id": int(row.id),
                "dieId": row.die_id,
                "content": row.content,
            }
            for row in memo_rows
            if row.id is not None
        }
        self.pinned_tasks = [
            {
                "taskId": int(row.id),
                "day": date.fromisoformat(row.day_id) if row.day_id else None,
                "dieId": row.die_id,
                "seqInDay": row.seq_in_day,
                "quantity": row.quantity,
                "pinnedType": row.pinned_type,
                "memo": row.memo,
                "priority": row.priority,
            }
            for row in task_rows
            if row.id is not None
        ]
        self.pinned_tasks.sort(key=lambda item: (item["day"] or date.min, item["seqInDay"] or 0, item["taskId"]))

        self._refresh_next_id_from_loaded_data()
        return any([
            self.working_times, self.days, self.lines, self.dies, self.parts, self.cars,
            self.car_parts, self.part_inventory, self.dunnages, self.dunnage_inventory,
            self.car_usages, self.memos, self.pinned_tasks,
        ])

    def _save_relational(self, session: Session):
        self._replace_rows(
            session,
            WorkingTimeRecord,
            [WorkingTimeRecord(text=text, minutes=minutes) for text, minutes in self.working_times.items()],
        )
        self._replace_rows(
            session,
            DayRecord,
            [
                DayRecord(
                    id=self._iso(day_value.get("day") or day_key),
                    woking_time=day_value.get("workingTimeText"),
                    out_minutes=day_value.get("outMinutes"),
                )
                for day_key, day_value in self.days.items()
            ],
        )
        self._replace_rows(
            session,
            LineRecord,
            [
                LineRecord(id=int(line_id), code=value.get("code"), description=value.get("description"))
                for line_id, value in self.lines.items()
            ],
        )
        self._replace_rows(
            session,
            DieRecord,
            [
                DieRecord(
                    id=int(die_id),
                    code=value.get("code"),
                    name=value.get("name"),
                    akz=value.get("akz"),
                    line_id=value.get("lineId"),
                )
                for die_id, value in self.dies.items()
            ],
        )
        self._replace_rows(
            session,
            DunnageRecord,
            [
                DunnageRecord(id=int(dunnage_id), name=value.get("name"), capacity=value.get("capacity"))
                for dunnage_id, value in self.dunnages.items()
            ],
        )
        self._replace_rows(
            session,
            PartRecord,
            [
                PartRecord(
                    id=int(part_id),
                    code=value.get("code"),
                    name=value.get("name"),
                    min=value.get("min"),
                    die_id=value.get("dieId"),
                    dunnage_id=value.get("dunnageId"),
                )
                for part_id, value in self.parts.items()
            ],
        )
        self._replace_rows(
            session,
            CarRecord,
            [
                CarRecord(id=int(car_id), code=value.get("code"), name=value.get("name"))
                for car_id, value in self.cars.items()
            ],
        )
        self._replace_rows(
            session,
            CarPartRecord,
            [
                CarPartRecord(
                    id=int(record_id),
                    usage=value.get("usage"),
                    car_id=value.get("carId"),
                    part_id=value.get("partId"),
                )
                for record_id, value in self.car_parts.items()
            ],
        )

        part_id_by_code = {
            value.get("code"): int(part_id)
            for part_id, value in self.parts.items()
            if value.get("code")
        }
        self._replace_rows(
            session,
            PartInventoryRecord,
            [
                PartInventoryRecord(
                    id=int(record_id),
                    day=value.get("day"),
                    part_id=value.get("partId") or part_id_by_code.get(value.get("part")),
                    quantity=value.get("quantity"),
                )
                for record_id, value in self.part_inventory.items()
            ],
        )
        self._replace_rows(
            session,
            DunnageInventoryHistoryRecord,
            [
                DunnageInventoryHistoryRecord(
                    id=int(record_id),
                    day=value.get("day"),
                    dunnage_id=value.get("dunnageId"),
                    quantity=value.get("quantity"),
                    empty_quantity=value.get("emptyQuantity"),
                    repair_quantity=value.get("repairQuantity"),
                    sealed_quantity=value.get("sealedQuantity"),
                    pending_repair_quantity=value.get("pendingRepairQuantity"),
                    welding_quantity=value.get("weldingQuantity"),
                )
                for record_id, value in self.dunnage_inventory.items()
            ],
        )
        self._replace_rows(
            session,
            CarUsageRecord,
            [
                CarUsageRecord(
                    id=int(record_id),
                    car_id=value.get("carId"),
                    day_id=self._iso(value.get("day")),
                    usage=value.get("num"),
                )
                for record_id, value in self.car_usages.items()
            ],
        )
        self._replace_rows(
            session,
            DieMemoRecord,
            [
                DieMemoRecord(id=int(record_id), die_id=value.get("dieId"), content=value.get("content"))
                for record_id, value in self.memos.items()
            ],
        )
        self._replace_rows(
            session,
            TaskRecord,
            [
                TaskRecord(
                    id=int(task["taskId"]),
                    day_id=self._iso(task.get("day")),
                    die_id=task.get("dieId"),
                    seq_in_day=task.get("seqInDay"),
                    quantity=task.get("quantity"),
                    pinned_type=task.get("pinnedType"),
                    memo=task.get("memo"),
                    priority=task.get("priority"),
                    is_day_pinned=task.get("day") is not None,
                    is_die_pinned=task.get("dieId") is not None,
                    is_quantity_pinned=task.get("quantity") is not None,
                    is_seq_pinned=task.get("seqInDay") is not None,
                )
                for task in self.pinned_tasks
            ],
        )

    def _replace_rows(self, session: Session, model, rows: List[Any]):
        session.query(model).delete()
        if rows:
            session.add_all(rows)

    def _refresh_next_id_from_loaded_data(self):
        defaults = self._default_next_id()
        defaults["line"] = self._next_value(self.lines.keys())
        defaults["die"] = self._next_value(self.dies.keys())
        defaults["part"] = self._next_value(self.parts.keys())
        defaults["car"] = self._next_value(self.cars.keys())
        defaults["car_part"] = self._next_value(self.car_parts.keys())
        defaults["part_inventory"] = self._next_value(self.part_inventory.keys())
        defaults["dunnage"] = self._next_value(self.dunnages.keys())
        defaults["dunnage_inventory"] = self._next_value(self.dunnage_inventory.keys())
        defaults["car_usage"] = self._next_value(self.car_usages.keys())
        defaults["memo"] = self._next_value(self.memos.keys())
        defaults["task"] = self._next_value(task["taskId"] for task in self.pinned_tasks)
        self._next_id = defaults

    @staticmethod
    def _next_value(values) -> int:
        normalized = [int(value) for value in values if value is not None]
        return (max(normalized) + 1) if normalized else 1

    @staticmethod
    def _iso(value):
        if value is None:
            return None
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    def _reset_state(self):
        self.working_times = {}
        self.days = {}
        self.lines = {}
        self.dies = {}
        self.parts = {}
        self.cars = {}
        self.car_parts = {}
        self.part_inventory = {}
        self.dunnages = {}
        self.dunnage_inventory = {}
        self.car_usages = {}
        self.solve_status = {}
        self.solve_results = {}
        self.memos = {}
        self.pinned_tasks = []
        self._next_id = self._default_next_id()

    @staticmethod
    def _default_next_id():
        return {
            "line": 1,
            "die": 1,
            "part": 1,
            "car": 1,
            "car_part": 1,
            "part_inventory": 1,
            "dunnage": 1,
            "dunnage_inventory": 1,
            "car_usage": 1,
            "memo": 1,
            "task": 1,
        }


db = Storage()
