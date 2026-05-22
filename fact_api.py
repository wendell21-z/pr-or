import datetime
from collections.abc import Iterable, Mapping
from typing import Any, TypeAlias, TypeVar

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from sqlalchemy import func

from models import (
    db, Car, CarPart, CarUsage, Day, Die, Dunnage, DunnageInventoryHistory,
    Line, Part, PartInventory, WorkingTime,
)


fact_bp = Blueprint("fact", __name__, url_prefix="/fact")

JsonDict: TypeAlias = dict[str, Any]
JsonList: TypeAlias = list[JsonDict]
JsonBody: TypeAlias = JsonDict | list[JsonDict]
ModelT = TypeVar("ModelT")


# Conflict note: Kotlin FactController exposes Day.workingTime, while this
# SQLAlchemy model stores the foreign-key text in Day.woking_time. This API
# accepts workingTimeText and returns both workingTime and workingTimeText.
#
# Conflict note: DunnageInventoryHistoryDto has availableQuantity, but the
# Kotlin entity and current SQLAlchemy model do not persist that column. This
# API returns a derived value: quantity - repair/sealed/pending/welding.
#
# Conflict note: Kotlin Day.availableMinutes is workingTime.minutes - outMinutes.
# Existing scheduler code may use a different business interpretation.


def _json(data: Any, status: int = 200) -> ResponseReturnValue:
    if status == 204:
        return "", 204
    return jsonify(data), status


def _error(message: str, status: int = 400) -> ResponseReturnValue:
    return _json({"status": "error", "message": message}, status)


def _payload() -> JsonBody:
    return request.get_json(silent=True) or {}


def _get(data: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in data:
            return data[name]
    return default


def _parse_date(value: Any) -> datetime.date | None:
    if isinstance(value, datetime.date):
        return value
    if not value:
        return None
    text = str(value)[:10]
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        year, month, day = text.split("-")
        return datetime.date(int(year), int(month), int(day))


def _commit(entity: ModelT) -> ModelT:
    db.session.add(entity)
    db.session.commit()
    return entity


def _save_json(entity: ModelT) -> JsonDict | None:
    db.session.add(entity)
    db.session.flush()
    data = _serialize(entity)
    db.session.commit()
    return data


def _save_all_json(entities: Iterable[ModelT]) -> JsonList:
    entity_list = list(entities)
    db.session.add_all(entity_list)
    db.session.flush()
    data = _serialize_all(entity_list)
    db.session.commit()
    return data


def _delete(model: type[ModelT], id_: Any) -> ResponseReturnValue:
    entity = db.session.get(model, id_)
    if entity is not None:
        db.session.delete(entity)
        db.session.commit()
    return _json(None, 204)


def _all(model: type[ModelT]) -> list[ModelT]:
    return db.session.query(model).all()


def _first_by(model: type[ModelT], **kwargs: Any) -> ModelT | None:
    return db.session.query(model).filter_by(**kwargs).first()


from utils import ensure_default_working_time, ensure_day


def _serialize(entity: Any | None) -> JsonDict | None:
    if entity is None:
        return None
    if isinstance(entity, WorkingTime):
        return {"text": entity.text, "minutes": entity.minutes}
    if isinstance(entity, Day):
        working_time = db.session.get(WorkingTime, entity.woking_time)
        total_minutes = working_time.minutes if working_time and working_time.minutes is not None else 0
        out_minutes = entity.out_minutes or 0
        date_value = _parse_date(entity.id)
        return {
            "id": entity.id,
            "day": entity.id,
            "outMinutes": out_minutes,
            "workingTime": _serialize(working_time),
            "workingTimeText": entity.woking_time,
            "totalMinutes": total_minutes,
            "availableMinutes": total_minutes - out_minutes,
            "canTask": total_minutes > 0,
            "week": date_value.isocalendar().week if date_value else None,
        }
    if isinstance(entity, Line):
        return {"id": entity.id, "code": entity.code, "description": entity.description}
    if isinstance(entity, Die):
        return {
            "id": entity.id,
            "code": entity.code,
            "name": entity.name,
            "akz": entity.akz,
            "line": _serialize(db.session.get(Line, entity.line_id)),
            "lineId": entity.line_id,
        }
    if isinstance(entity, Dunnage):
        return {"id": entity.id, "name": entity.name, "capacity": entity.capacity}
    if isinstance(entity, DunnageInventoryHistory):
        return {
            "id": entity.id,
            "day": entity.day.isoformat() if entity.day else None,
            "dunnage": _serialize(db.session.get(Dunnage, entity.dunnage_id)),
            "dunnageId": entity.dunnage_id,
            "quantity": entity.quantity,
            "emptyQuantity": entity.empty_quantity,
            "repairQuantity": entity.repair_quantity,
            "sealedQuantity": entity.sealed_quantity,
            "pendingRepairQuantity": entity.pending_repair_quantity,
            "weldingQuantity": entity.welding_quantity,
            "availableQuantity": (
                (entity.quantity or 0)
                - (entity.repair_quantity or 0)
                - (entity.sealed_quantity or 0)
                - (entity.pending_repair_quantity or 0)
                - (entity.welding_quantity or 0)
            ),
        }
    if isinstance(entity, Part):
        return {
            "id": entity.id,
            "code": entity.code,
            "name": entity.name,
            "min": entity.min,
            "die": _serialize(db.session.get(Die, entity.die_id)),
            "dieId": entity.die_id,
            "dunnage": _serialize(db.session.get(Dunnage, entity.dunnage_id)),
            "dunnageId": entity.dunnage_id,
        }
    if isinstance(entity, Car):
        return {"id": entity.id, "code": entity.code, "name": entity.name}
    if isinstance(entity, CarPart):
        return {
            "id": entity.id,
            "car": _serialize(db.session.get(Car, entity.car_id)),
            "carId": entity.car_id,
            "part": _serialize(db.session.get(Part, entity.part_id)),
            "partId": entity.part_id,
            "usage": entity.usage,
        }
    if isinstance(entity, CarUsage):
        return {
            "car": _serialize(db.session.get(Car, entity.car_id)),
            "carId": entity.car_id,
            "day": _serialize(db.session.get(Day, entity.day_id)),
            "dayId": entity.day_id,
            "usage": entity.usage,
            "num": entity.usage,
        }
    if isinstance(entity, PartInventory):
        return {
            "part": _serialize(db.session.get(Part, entity.part_id)),
            "partId": entity.part_id,
            "day": entity.day_id,
            "dayId": entity.day_id,
            "quantity": entity.quantity,
        }
    return {}


def _serialize_all(items: Iterable[Any]) -> JsonList:
    return [serialized for item in items if (serialized := _serialize(item)) is not None]


@fact_bp.post("/working-time")
def upsert_working_time() -> ResponseReturnValue:
    """Body: {"text": str, "minutes": int}. Returns: WorkingTime."""
    data = _payload()
    text = _get(data, "text")
    if text is None:
        return _error("text is required")
    entity = db.session.get(WorkingTime, text) or WorkingTime(text=text)
    entity.minutes = _get(data, "minutes", default=0)
    return _json(_save_json(entity))


@fact_bp.get("/working-time")
def list_working_time() -> ResponseReturnValue:
    """No params. Returns: list[WorkingTime]."""
    return _json(_serialize_all(_all(WorkingTime)))


@fact_bp.delete("/working-time/<path:text>")
def delete_working_time(text: str) -> ResponseReturnValue:
    """Path: text: str. Returns: 204 No Content."""
    if _first_by(Day, woking_time=text):
        return _error("有日期引用该排产，无法删除")
    return _delete(WorkingTime, text)


@fact_bp.post("/day")
def upsert_day() -> ResponseReturnValue:
    """Body: {"day": date, "workingTimeText": str, "outMinutes": int=0}. Returns: Day."""
    data = _payload()
    day = _parse_date(_get(data, "day", "id"))
    working_time_text = _get(data, "workingTimeText", "woking_time", "working_time")
    if db.session.get(WorkingTime, working_time_text) is None:
        return _error(f"{working_time_text}未设置")
    entity = ensure_day(day)
    entity.woking_time = working_time_text
    entity.out_minutes = _get(data, "outMinutes", "out_minutes", default=0)
    return _json(_save_json(entity))


@fact_bp.post("/day/batch")
def upsert_day_batch() -> ResponseReturnValue:
    """Body: list[{"day": date, "workingTimeText": str, "outMinutes": int=0}]. Returns: list[Day]."""
    result = []
    for data in _payload():
        day = _parse_date(_get(data, "day", "id"))
        working_time_text = _get(data, "workingTimeText", "woking_time", "working_time")
        if db.session.get(WorkingTime, working_time_text) is None:
            db.session.rollback()
            return _error(f"{working_time_text}未设置")
        entity = ensure_day(day)
        entity.woking_time = working_time_text
        entity.out_minutes = _get(data, "outMinutes", "out_minutes", default=0)
        result.append(entity)
    return _json(_save_all_json(result))


@fact_bp.get("/day")
def list_days() -> ResponseReturnValue:
    """No params. Returns: list[Day]."""
    return _json(_serialize_all(_all(Day)))


@fact_bp.post("/line")
def upsert_line() -> ResponseReturnValue:
    """Body: {"id": int|None, "code": str, "description": str=""}. Returns: Line."""
    data = _payload()
    id_ = _get(data, "id")
    code = _get(data, "code")
    old = _first_by(Line, code=code)
    if old is not None and old.id != id_:
        return _error(f"线体编码{code}已存在")
    entity = db.session.get(Line, id_) if id_ is not None else None
    entity = entity or Line()
    entity.code = code
    entity.description = _get(data, "description", default="")
    return _json(_save_json(entity))


@fact_bp.get("/line")
def list_lines() -> ResponseReturnValue:
    """No params. Returns: list[Line]."""
    return _json(_serialize_all(_all(Line)))


@fact_bp.delete("/line/<int:id_>")
def delete_line(id_: int) -> ResponseReturnValue:
    """Path: id: int. Returns: 204 No Content."""
    if _first_by(Die, line_id=id_):
        return _error("该 Line 存在依赖的 Parties，无法删除")
    return _delete(Line, id_)


@fact_bp.post("/die")
def upsert_die() -> ResponseReturnValue:
    """Body: {"code": str, "name": str, "akz": int, "lineId": int}. Returns: Die."""
    data = _payload()
    line_id = _get(data, "lineId", "line_id")
    if db.session.get(Line, line_id) is None:
        return _error("线体不存在")
    code = _get(data, "code")
    entity = _first_by(Die, code=code) or Die()
    entity.code = code
    entity.name = _get(data, "name")
    entity.akz = _get(data, "akz")
    entity.line_id = line_id
    return _json(_save_json(entity))


@fact_bp.post("/die/batch")
def upsert_die_batch() -> ResponseReturnValue:
    """Body: list[{"code": str, "name": str, "akz": int, "lineId": int}]. Returns: list[Die]."""
    result = []
    for data in _payload():
        line_id = _get(data, "lineId", "line_id")
        if db.session.get(Line, line_id) is None:
            db.session.rollback()
            return _error(f"线体lineId={line_id}不存在")
        code = _get(data, "code")
        entity = _first_by(Die, code=code) or Die()
        entity.code = code
        entity.name = _get(data, "name")
        entity.akz = _get(data, "akz")
        entity.line_id = line_id
        result.append(entity)
    return _json(_save_all_json(result))


@fact_bp.get("/die/all")
def list_dies() -> ResponseReturnValue:
    """No params. Returns: list[Die]."""
    return _json(_serialize_all(_all(Die)))


@fact_bp.delete("/die/<int:id_>")
def delete_die(id_: int) -> ResponseReturnValue:
    """Path: id: int. Returns: 204 No Content."""
    if _first_by(Part, die_id=id_):
        return _error("存在零件依赖该模具")
    return _delete(Die, id_)


@fact_bp.post("/dunnage")
def upsert_dunnage() -> ResponseReturnValue:
    """Body: {"name": str, "capacity": int}. Returns: Dunnage."""
    data = _payload()
    name = _get(data, "name")
    entity = _first_by(Dunnage, name=name) or Dunnage()
    entity.name = name
    entity.capacity = _get(data, "capacity")
    return _json(_save_json(entity))


@fact_bp.post("/dunnage/batch")
def upsert_dunnage_batch() -> ResponseReturnValue:
    """Body: list[{"name": str, "capacity": int}]. Returns: list[Dunnage]."""
    result = []
    for data in _payload():
        name = _get(data, "name")
        entity = _first_by(Dunnage, name=name) or Dunnage()
        entity.name = name
        entity.capacity = _get(data, "capacity")
        result.append(entity)
    return _json(_save_all_json(result))


@fact_bp.get("/dunnage")
def list_dunnage() -> ResponseReturnValue:
    """No params. Returns: list[Dunnage]."""
    return _json(_serialize_all(_all(Dunnage)))


@fact_bp.delete("/dunnage/<int:id_>")
def delete_dunnage(id_: int) -> ResponseReturnValue:
    """Path: id: int. Returns: 204 No Content."""
    if _first_by(Part, dunnage_id=id_):
        return _error("存在零件依赖该器具")
    return _delete(Dunnage, id_)


def _upsert_dunnage_inventory(data: Mapping[str, Any]) -> DunnageInventoryHistory:
    dunnage_id = _get(data, "dunnageId", "dunnage_id")
    day = _parse_date(_get(data, "day"))
    # ensure Day row exists for this date
    ensure_day(day)
    if db.session.get(Dunnage, dunnage_id) is None:
        raise ValueError(f"器具（{dunnage_id}）不存在")
    entity = _first_by(DunnageInventoryHistory, day=day, dunnage_id=dunnage_id)
    entity = entity or DunnageInventoryHistory(day=day, dunnage_id=dunnage_id)
    entity.quantity = _get(data, "quantity")
    entity.empty_quantity = _get(data, "emptyQuantity", "empty_quantity")
    entity.repair_quantity = _get(data, "repairQuantity", "repair_quantity")
    entity.sealed_quantity = _get(data, "sealedQuantity", "sealed_quantity")
    entity.pending_repair_quantity = _get(data, "pendingRepairQuantity", "pending_repair_quantity")
    entity.welding_quantity = _get(data, "weldingQuantity", "welding_quantity")
    return entity


@fact_bp.post("/dunnage-inventory")
def upsert_dunnage_inventory() -> ResponseReturnValue:
    """Body: {"day": date, "dunnageId": int, "quantity": int, "emptyQuantity": int, "repairQuantity": int, "sealedQuantity": int, "pendingRepairQuantity": int, "weldingQuantity": int}. Returns: DunnageInventoryHistory."""
    try:
        return _json(_save_json(_upsert_dunnage_inventory(_payload())))
    except ValueError as exc:
        return _error(str(exc))


@fact_bp.post("/dunnage-inventory/batch")
def upsert_dunnage_inventory_batch() -> ResponseReturnValue:
    """Body: list[{"day": date, "dunnageId": int, "quantity": int, "emptyQuantity": int, "repairQuantity": int, "sealedQuantity": int, "pendingRepairQuantity": int, "weldingQuantity": int}]. Returns: list[DunnageInventoryHistory]."""
    result = []
    try:
        for data in _payload():
            entity = _upsert_dunnage_inventory(data)
            result.append(entity)
        data = _save_all_json(result)
    except ValueError as exc:
        db.session.rollback()
        return _error(str(exc))
    return _json(data)


@fact_bp.get("/dunnage-inventory/latest")
def latest_dunnage_inventory() -> ResponseReturnValue:
    """No params. Returns: list[DunnageInventoryHistory]."""
    latest_day = db.session.query(func.max(DunnageInventoryHistory.day)).scalar()
    if latest_day is None:
        return _json([])
    records = db.session.query(DunnageInventoryHistory).filter_by(day=latest_day).all()
    return _json(_serialize_all(records))


@fact_bp.get("/dunnage-inventory")
def list_dunnage_inventory_by_day() -> ResponseReturnValue:
    """Query: day: date. Returns: list[DunnageInventoryHistory]."""
    records = db.session.query(DunnageInventoryHistory).filter_by(
        day=_parse_date(request.args.get("day"))
    ).all()
    return _json(_serialize_all(records))


@fact_bp.get("/dunnage-inventory/all")
def list_dunnage_inventory() -> ResponseReturnValue:
    """No params. Returns: list[DunnageInventoryHistory]."""
    return _json(_serialize_all(_all(DunnageInventoryHistory)))


@fact_bp.delete("/dunnage-inventory/<int:id_>")
def delete_dunnage_inventory(id_: int) -> ResponseReturnValue:
    """Path: id: int. Returns: 204 No Content."""
    return _delete(DunnageInventoryHistory, id_)


@fact_bp.post("/part")
def upsert_part() -> ResponseReturnValue:
    """Body: {"code": str, "name": str, "min": int, "dieId": int, "dunnageId": int}. Returns: Part."""
    data = _payload()
    die_id = _get(data, "dieId", "die_id")
    dunnage_id = _get(data, "dunnageId", "dunnage_id")
    if db.session.get(Die, die_id) is None:
        return _error(f"die {{id = {die_id} 不存在}}")
    if db.session.get(Dunnage, dunnage_id) is None:
        return _error(f"器具（id={dunnage_id}）不存在", 404)
    code = _get(data, "code")
    entity = _first_by(Part, code=code) or Part()
    entity.code = code
    entity.name = _get(data, "name")
    entity.min = _get(data, "min")
    entity.die_id = die_id
    entity.dunnage_id = dunnage_id
    return _json(_save_json(entity))


@fact_bp.get("/part/all")
def list_parts() -> ResponseReturnValue:
    """No params. Returns: list[Part]."""
    return _json(_serialize_all(_all(Part)))


@fact_bp.delete("/part/<int:id_>")
def delete_part(id_: int) -> ResponseReturnValue:
    """Path: id: int. Returns: 204 No Content."""
    if _first_by(CarPart, part_id=id_):
        return _error("车型-零件对应表存在依赖")
    return _delete(Part, id_)


@fact_bp.post("/car")
def upsert_car() -> ResponseReturnValue:
    """Body: {"code": str, "name": str}. Returns: Car."""
    data = _payload()
    code = _get(data, "code")
    entity = _first_by(Car, code=code) or Car()
    entity.code = code
    entity.name = _get(data, "name")
    return _json(_save_json(entity))


@fact_bp.get("/car/all")
def list_cars() -> ResponseReturnValue:
    """No params. Returns: list[Car]."""
    return _json(_serialize_all(_all(Car)))


@fact_bp.delete("/car/<int:id_>")
def delete_car(id_: int) -> ResponseReturnValue:
    """Path: id: int. Returns: 204 No Content."""
    return _delete(Car, id_)


@fact_bp.post("/part-car")
def upsert_car_part() -> ResponseReturnValue:
    """Body: {"carId": int, "partId": int, "usage": int=1}. Returns: CarPart."""
    data = _payload()
    car_id = _get(data, "carId", "car_id")
    part_id = _get(data, "partId", "part_id")
    if db.session.get(Car, car_id) is None or db.session.get(Part, part_id) is None:
        return _error("carId or partId not found", 404)
    entity = _first_by(CarPart, car_id=car_id, part_id=part_id)
    entity = entity or CarPart(car_id=car_id, part_id=part_id)
    entity.usage = _get(data, "usage", default=1)
    return _json(_save_json(entity))


@fact_bp.get("/part-car")
def list_car_parts() -> ResponseReturnValue:
    """No params. Returns: list[CarPart]."""
    return _json(_serialize_all(_all(CarPart)))


@fact_bp.delete("/part-car/<int:id_>")
def delete_car_part(id_: int) -> ResponseReturnValue:
    """Path: id: int. Returns: 204 No Content."""
    return _delete(CarPart, id_)


@fact_bp.post("/car-usage")
def upsert_car_usage() -> ResponseReturnValue:
    """Body: {"carId": int, "day": date, "num": int}. Returns: CarUsage."""
    data = _payload()
    day = ensure_day(_parse_date(_get(data, "day")))
    car_id = _get(data, "carId", "car_id")
    if db.session.get(Car, car_id) is None:
        return _error(f"carId = {car_id} 未定义", 404)
    entity = _first_by(CarUsage, car_id=car_id, day_id=day.id)
    entity = entity or CarUsage(car_id=car_id, day_id=day.id)
    entity.usage = _get(data, "num", "usage")
    return _json(_save_json(entity))


@fact_bp.post("/car-usage/batch")
def upsert_car_usage_batch() -> ResponseReturnValue:
    """Body: list[{"carId": int, "day": date, "num": int}]. Returns: list[CarUsage]."""
    result = []
    for data in _payload():
        day = ensure_day(_parse_date(_get(data, "day")))
        car_id = _get(data, "carId", "car_id")
        if db.session.get(Car, car_id) is None:
            db.session.rollback()
            return _error(f"carId = {car_id} 未定义", 404)
        entity = _first_by(CarUsage, car_id=car_id, day_id=day.id)
        entity = entity or CarUsage(car_id=car_id, day_id=day.id)
        entity.usage = _get(data, "num", "usage")
        result.append(entity)
    return _json(_save_all_json(result))


@fact_bp.get("/car-usage/all")
def list_car_usage() -> ResponseReturnValue:
    """No params. Returns: list[CarUsage]."""
    return _json(_serialize_all(_all(CarUsage)))


@fact_bp.delete("/car-usage/<int:car_id>/<path:day_id>")
def delete_car_usage(car_id: int, day_id: str) -> ResponseReturnValue:
    """Path: car_id:int, day_id:str (YYYY-MM-DD). Returns: 204 No Content."""
    return _delete(CarUsage, (car_id, day_id))


def _upsert_part_inventory(data: Mapping[str, Any]) -> PartInventory:
    code = _get(data, "part")
    part = _first_by(Part, code=code)
    if part is None:
        raise ValueError(f"对应零件（{code}）不存在")
    day = _parse_date(_get(data, "day"))
    # ensure Day row exists and use its id as day_id
    day_obj = ensure_day(day)
    day_id = day_obj.id if day_obj is not None else (day.isoformat() if day is not None else None)
    entity = _first_by(PartInventory, day_id=day_id, part_id=part.id)
    entity = entity or PartInventory(day_id=day_id, part_id=part.id)
    entity.quantity = _get(data, "quantity")
    return entity


@fact_bp.post("/part-inventory")
def upsert_part_inventory() -> ResponseReturnValue:
    """Body: {"part": str, "day": date, "quantity": int}. Returns: PartInventory."""
    try:
        return _json(_save_json(_upsert_part_inventory(_payload())))
    except ValueError as exc:
        return _error(str(exc))


@fact_bp.post("/part-inventory/batch")
def upsert_part_inventory_batch() -> ResponseReturnValue:
    """Body: list[{"part": str, "day": date, "quantity": int}]. Returns: list[PartInventory]."""
    result = []
    try:
        for data in _payload():
            entity = _upsert_part_inventory(data)
            result.append(entity)
        data = _save_all_json(result)
    except ValueError as exc:
        db.session.rollback()
        return _error(str(exc))
    return _json(data)


@fact_bp.get("/part-inventory/all")
def list_part_inventory() -> ResponseReturnValue:
    """No params. Returns: list[PartInventory]."""
    return _json(_serialize_all(_all(PartInventory)))


@fact_bp.delete("/part-inventory/<int:part_id>/<path:day_id>")
def delete_part_inventory(part_id: int, day_id: str) -> ResponseReturnValue:
    """Path: part_id:int, day_id:str (YYYY-MM-DD). Returns: 204 No Content."""
    return _delete(PartInventory, (day_id, part_id))
