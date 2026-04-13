from fastapi import APIRouter, HTTPException, Query
from dto import (
    WokingTimeDto, DayDto, LineDto, DieDto, PartDto, CarDto, CarPartDto,
    PartInventoryDto, DunnageDto, DunnageInventoryHistoryDto, CarUsageDto
)
from typing import List, Optional
from datetime import date
from storage import db

router = APIRouter(prefix="/fact", tags=["Fact"])


def persist():
    with db.session_scope() as s:
        db.save(s)

# 3.1 工作时间 (WorkingTime)
@router.post("/working-time")
async def save_working_time(dto: WokingTimeDto):
    db.working_times[dto.text] = dto.minutes
    persist()
    return {"message": "Working time saved"}

@router.get("/working-time")
async def get_all_working_time():
    data = [{"text": k, "minutes": v} for k, v in db.working_times.items()]
    return {"data": data}

@router.delete("/working-time/{text}")
async def delete_working_time(text: str):
    if text in db.working_times:
        del db.working_times[text]
        persist()
        return {"message": f"Working time {text} deleted"}
    raise HTTPException(status_code=404, detail="Working time not found")

# 3.2 日期配置 (Day)
@router.post("/day")
async def save_day(dto: DayDto):
    db.days[dto.day] = dto.model_dump()
    persist()
    return {"message": "Day saved"}

@router.post("/day/batch")
async def batch_save_day(dtos: List[DayDto]):
    for dto in dtos:
        db.days[dto.day] = dto.model_dump()
    persist()
    return {"message": f"{len(dtos)} days saved"}

@router.get("/day")
async def get_all_days():
    data = list(db.days.values())
    return {"data": data}

# 3.3 线体 (Line)
@router.post("/line")
async def save_line(dto: LineDto):
    line_id = dto.id or db.get_next_id("line")
    db.lines[line_id] = dto.model_dump()
    db.lines[line_id]["id"] = line_id
    persist()
    return {"message": "Line saved", "id": line_id}

@router.get("/line")
async def get_all_lines():
    return {"data": list(db.lines.values())}

@router.delete("/line/{id}")
async def delete_line(id: int):
    if id in db.lines:
        del db.lines[id]
        persist()
        return {"message": f"Line {id} deleted"}
    raise HTTPException(status_code=404, detail="Line not found")

# 3.4 模具 (Die)
@router.post("/die")
async def save_die(dto: DieDto):
    die_id = db.get_next_id("die")
    db.dies[die_id] = dto.model_dump()
    db.dies[die_id]["id"] = die_id
    persist()
    return {"message": "Die saved", "id": die_id}

@router.post("/die/batch")
async def batch_save_die(dtos: List[DieDto]):
    for dto in dtos:
        die_id = db.get_next_id("die")
        db.dies[die_id] = dto.model_dump()
        db.dies[die_id]["id"] = die_id
    persist()
    return {"message": f"{len(dtos)} dies saved"}

@router.get("/die/all")
async def get_all_dies():
    return {"data": list(db.dies.values())}

@router.delete("/die/{id}")
async def delete_die(id: int):
    if id in db.dies:
        del db.dies[id]
        persist()
        return {"message": f"Die {id} deleted"}
    raise HTTPException(status_code=404, detail="Die not found")

# 3.5 零件 (Part)
@router.post("/part")
async def save_part(dto: PartDto):
    part_id = db.get_next_id("part")
    db.parts[part_id] = dto.model_dump()
    db.parts[part_id]["id"] = part_id
    persist()
    return {"message": "Part saved", "id": part_id}

@router.get("/part/all")
async def get_all_parts():
    return {"data": list(db.parts.values())}

@router.delete("/part/{id}")
async def delete_part(id: int):
    if id in db.parts:
        del db.parts[id]
        persist()
        return {"message": f"Part {id} deleted"}
    raise HTTPException(status_code=404, detail="Part not found")

# 3.6 车型 (Car)
@router.post("/car")
async def save_car(dto: CarDto):
    car_id = db.get_next_id("car")
    db.cars[car_id] = dto.model_dump()
    db.cars[car_id]["id"] = car_id
    persist()
    return {"message": "Car saved", "id": car_id}

@router.get("/car/all")
async def get_all_cars():
    return {"data": list(db.cars.values())}

@router.delete("/car/{id}")
async def delete_car(id: int):
    if id in db.cars:
        del db.cars[id]
        persist()
        return {"message": f"Car {id} deleted"}
    raise HTTPException(status_code=404, detail="Car not found")

# 3.7 车型-零件关系 (CarPart)
@router.post("/part-car")
async def save_part_car(dto: CarPartDto):
    cp_id = db.get_next_id("car_part")
    db.car_parts[cp_id] = dto.model_dump()
    db.car_parts[cp_id]["id"] = cp_id
    persist()
    return {"message": "Car-Part relationship saved", "id": cp_id}

@router.get("/part-car")
async def get_all_part_cars():
    return {"data": list(db.car_parts.values())}

@router.delete("/part-car/{id}")
async def delete_part_car(id: int):
    if id in db.car_parts:
        del db.car_parts[id]
        persist()
        return {"message": f"Car-Part relationship {id} deleted"}
    raise HTTPException(status_code=404, detail="Car-Part relationship not found")

# 4.1 零件库存 (PartInventory)
@router.post("/part-inventory")
async def save_part_inventory(dto: PartInventoryDto):
    pi_id = db.get_next_id("part_inventory")
    db.part_inventory[pi_id] = dto.model_dump()
    db.part_inventory[pi_id]["id"] = pi_id
    persist()
    return {"message": "Part inventory saved", "id": pi_id}

@router.post("/part-inventory/batch")
async def batch_save_part_inventory(dtos: List[PartInventoryDto]):
    for dto in dtos:
        pi_id = db.get_next_id("part_inventory")
        db.part_inventory[pi_id] = dto.model_dump()
        db.part_inventory[pi_id]["id"] = pi_id
    persist()
    return {"message": f"{len(dtos)} part inventories saved"}

@router.get("/part-inventory/all")
async def get_all_part_inventories():
    return {"data": list(db.part_inventory.values())}

@router.delete("/part-inventory/{id}")
async def delete_part_inventory(id: int):
    if id in db.part_inventory:
        del db.part_inventory[id]
        persist()
        return {"message": f"Part inventory {id} deleted"}
    raise HTTPException(status_code=404, detail="Part inventory not found")

# 4.2 器具管理 (Dunnage)
@router.post("/dunnage")
async def save_dunnage(dto: DunnageDto):
    d_id = db.get_next_id("dunnage")
    db.dunnages[d_id] = dto.model_dump()
    db.dunnages[d_id]["id"] = d_id
    persist()
    return {"message": "Dunnage saved", "id": d_id}

@router.post("/dunnage/batch")
async def batch_save_dunnage(dtos: List[DunnageDto]):
    for dto in dtos:
        d_id = db.get_next_id("dunnage")
        db.dunnages[d_id] = dto.model_dump()
        db.dunnages[d_id]["id"] = d_id
    persist()
    return {"message": f"{len(dtos)} dunnages saved"}

@router.get("/dunnage")
async def get_all_dunnages():
    return {"data": list(db.dunnages.values())}

@router.delete("/dunnage/{id}")
async def delete_dunnage(id: int):
    if id in db.dunnages:
        del db.dunnages[id]
        persist()
        return {"message": f"Dunnage {id} deleted"}
    raise HTTPException(status_code=404, detail="Dunnage not found")

# 4.3 器具库存 (DunnageInventoryHistory)
@router.post("/dunnage-inventory")
async def save_dunnage_inventory(dto: DunnageInventoryHistoryDto):
    di_id = db.get_next_id("dunnage_inventory")
    db.dunnage_inventory[di_id] = dto.model_dump()
    db.dunnage_inventory[di_id]["id"] = di_id
    persist()
    return {"message": "Dunnage inventory saved", "id": di_id}

@router.post("/dunnage-inventory/batch")
async def batch_save_dunnage_inventory(dtos: List[DunnageInventoryHistoryDto]):
    for dto in dtos:
        di_id = db.get_next_id("dunnage_inventory")
        db.dunnage_inventory[di_id] = dto.model_dump()
        db.dunnage_inventory[di_id]["id"] = di_id
    persist()
    return {"message": f"{len(dtos)} dunnage inventories saved"}

@router.get("/dunnage-inventory/all")
async def get_all_dunnage_inventory_history():
    return {"data": list(db.dunnage_inventory.values())}


@router.get("/dunnage-inventory/latest")
async def get_latest_dunnage_inventory():
    data = sorted(db.dunnage_inventory.values(), key=lambda x: x["day"], reverse=True)
    return {"data": data[:1]}


@router.delete("/dunnage-inventory/{id}")
async def delete_dunnage_inventory(id: int):
    if id in db.dunnage_inventory:
        del db.dunnage_inventory[id]
        persist()
        return {"message": f"Dunnage inventory {id} deleted"}
    raise HTTPException(status_code=404, detail="Dunnage inventory not found")

# 4.4 车身流信息 (CarUsage)
@router.post("/car-usage")
async def save_car_usage(dto: CarUsageDto):
    cu_id = db.get_next_id("car_usage")
    db.car_usages[cu_id] = dto.model_dump()
    db.car_usages[cu_id]["id"] = cu_id
    persist()
    return {"message": "Car usage saved", "id": cu_id}

@router.post("/car-usage/batch")
async def batch_save_car_usage(dtos: List[CarUsageDto]):
    for dto in dtos:
        cu_id = db.get_next_id("car_usage")
        db.car_usages[cu_id] = dto.model_dump()
        db.car_usages[cu_id]["id"] = cu_id
    persist()
    return {"message": f"{len(dtos)} car usages saved"}

@router.get("/car-usage/all")
async def get_all_car_usages():
    return {"data": list(db.car_usages.values())}

@router.delete("/car-usage/{id}")
async def delete_car_usage(id: int):
    if id in db.car_usages:
        del db.car_usages[id]
        persist()
        return {"message": f"Car usage {id} deleted"}
    raise HTTPException(status_code=404, detail="Car usage not found")
