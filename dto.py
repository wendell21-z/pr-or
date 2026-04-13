from pydantic import BaseModel
from typing import List, Optional
from datetime import date

# --- SolveController DTOs ---

class SolveDto(BaseModel):
    lineId: int
    begin: date

# --- SolutionController DTOs ---

class PinnedTaskDto(BaseModel):
    day: date
    dieId: int
    seqInDay: Optional[int] = None
    quantity: Optional[int] = None

class UpdateTaskDto(BaseModel):
    taskId: int
    pinnedType: Optional[int] = None  # 0-普通, 1-用户指定, 2-已完成
    quantity: Optional[int] = None

class MemoDto(BaseModel):
    dieId: int
    content: str

# --- FactController DTOs ---

class WokingTimeDto(BaseModel):
    text: str
    minutes: int

class DayDto(BaseModel):
    day: date
    workingTimeText: str
    outMinutes: int

class LineDto(BaseModel):
    id: Optional[int] = None
    code: str
    description: str

class DieDto(BaseModel):
    code: str
    name: str
    akz: int
    lineId: int

class PartDto(BaseModel):
    code: str
    name: str
    min: int
    dieId: int
    dunnageId: int

class CarDto(BaseModel):
    code: str
    name: str

class CarPartDto(BaseModel):
    carId: int
    partId: int
    usage: int

class PartInventoryDto(BaseModel):
    part: str
    day: date
    quantity: int

class DunnageDto(BaseModel):
    name: str
    capacity: int

class DunnageInventoryHistoryDto(BaseModel):
    day: date
    dunnageId: int
    quantity: int
    emptyQuantity: int
    repairQuantity: int
    sealedQuantity: int
    pendingRepairQuantity: int
    weldingQuantity: int

class CarUsageDto(BaseModel):
    carId: int
    day: date
    num: int
