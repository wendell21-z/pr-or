"""
Resource controller for production resources, materials, and processes.
These endpoints are called from the frontend but may not be essential for core functionality.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from storage import db

router = APIRouter(prefix="/jvs-aps", tags=["JVSMAPS Resources"])


# --- Mock Data Models ---

class ProductionResource(BaseModel):
    id: Optional[int] = None
    code: str
    name: str
    type: str  # 'line', 'die', 'part', etc.
    groupId: Optional[int] = None
    status: int = 1  # 1-active, 0-inactive


class Material(BaseModel):
    id: Optional[int] = None
    code: str
    name: str
    description: Optional[str] = None
    status: int = 1


class Process(BaseModel):
    id: Optional[int] = None
    code: str
    name: str
    description: Optional[str] = None
    templateId: Optional[int] = None


class ResourceGroup(BaseModel):
    id: int
    name: str
    code: str


# --- In-memory storage for resources (temporary) ---
_resources: dict[int, dict] = {}
_materials: dict[int, dict] = {}
_processes: dict[int, dict] = {}
_resource_groups: dict[int, dict] = {
    1: {"id": 1, "name": "冲压线", "code": "pressing"},
    2: {"id": 2, "name": "焊接线", "code": "welding"},
    3: {"id": 3, "name": "涂装线", "code": "painting"},
}
_next_resource_id = 1
_next_material_id = 1
_next_process_id = 1


# --- Production Resource Endpoints ---

@router.get("/production-resource/page")
async def get_production_resources_page(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    type: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None)
):
    """获取分页资源列表"""
    # TODO: 实现实际的数据库查询
    data = list(_resources.values())
    
    # 过滤
    if type:
        data = [r for r in data if r.get("type") == type]
    if keyword:
        data = [r for r in data if keyword.lower() in r.get("code", "").lower() or keyword.lower() in r.get("name", "").lower()]
    
    total = len(data)
    start = (page - 1) * size
    end = start + size
    page_data = data[start:end]
    
    return {
        "code": 200,
        "data": {
            "records": page_data,
            "total": total,
            "page": page,
            "size": size
        }
    }


@router.post("/production-resource")
async def create_production_resource(resource: ProductionResource):
    """创建生产资源"""
    global _next_resource_id
    resource_id = _next_resource_id
    _next_resource_id += 1
    
    data = resource.model_dump()
    data["id"] = resource_id
    _resources[resource_id] = data
    
    return {"code": 200, "message": "Resource created", "data": {"id": resource_id}}


@router.put("/production-resource")
async def update_production_resource(resource: ProductionResource):
    """更新生产资源"""
    if not resource.id or resource.id not in _resources:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    _resources[resource.id].update(resource.model_dump(exclude_unset=True))
    return {"code": 200, "message": "Resource updated"}


@router.delete("/production-resource/{resource_id}")
async def delete_production_resource(resource_id: int):
    """删除生产资源"""
    if resource_id not in _resources:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    del _resources[resource_id]
    return {"code": 200, "message": "Resource deleted"}


@router.get("/production-resource/group/list")
async def get_resource_groups():
    """获取资源分组列表"""
    return {"code": 200, "data": list(_resource_groups.values())}


# --- Material Endpoints ---

@router.get("/material/page")
async def get_materials_page(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    keyword: Optional[str] = Query(default=None)
):
    """获取分页物料列表"""
    # TODO: 实现实际的数据库查询
    data = list(_materials.values())
    
    if keyword:
        data = [m for m in data if keyword.lower() in m.get("code", "").lower() or keyword.lower() in m.get("name", "").lower()]
    
    total = len(data)
    start = (page - 1) * size
    end = start + size
    page_data = data[start:end]
    
    return {
        "code": 200,
        "data": {
            "records": page_data,
            "total": total,
            "page": page,
            "size": size
        }
    }


@router.post("/material")
async def create_material(material: Material):
    """创建物料"""
    global _next_material_id
    material_id = _next_material_id
    _next_material_id += 1
    
    data = material.model_dump()
    data["id"] = material_id
    _materials[material_id] = data
    
    return {"code": 200, "message": "Material created", "data": {"id": material_id}}


@router.put("/material")
async def update_material(material: Material):
    """更新物料"""
    if not material.id or material.id not in _materials:
        raise HTTPException(status_code=404, detail="Material not found")
    
    _materials[material.id].update(material.model_dump(exclude_unset=True))
    return {"code": 200, "message": "Material updated"}


@router.delete("/material/{material_id}")
async def delete_material(material_id: int):
    """删除物料"""
    if material_id not in _materials:
        raise HTTPException(status_code=404, detail="Material not found")
    
    del _materials[material_id]
    return {"code": 200, "message": "Material deleted"}


# --- Process Endpoints ---

@router.post("/process")
async def create_process(process: Process):
    """创建工序"""
    global _next_process_id
    process_id = _next_process_id
    _next_process_id += 1
    
    data = process.model_dump()
    data["id"] = process_id
    _processes[process_id] = data
    
    return {"code": 200, "message": "Process created", "data": {"id": process_id}}


@router.get("/process/{process_id}")
async def get_process(process_id: int):
    """获取工序详情"""
    if process_id not in _processes:
        raise HTTPException(status_code=404, detail="Process not found")
    
    return {"code": 200, "data": _processes[process_id]}


@router.put("/process")
async def update_process(process: Process):
    """更新工序"""
    if not process.id or process.id not in _processes:
        raise HTTPException(status_code=404, detail="Process not found")
    
    _processes[process.id].update(process.model_dump(exclude_unset=True))
    return {"code": 200, "message": "Process updated"}


@router.get("/process/page")
async def get_processes_page(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    keyword: Optional[str] = Query(default=None)
):
    """获取分页工序模板列表"""
    data = list(_processes.values())
    
    if keyword:
        data = [p for p in data if keyword.lower() in p.get("code", "").lower() or keyword.lower() in p.get("name", "").lower()]
    
    total = len(data)
    start = (page - 1) * size
    end = start + size
    page_data = data[start:end]
    
    return {
        "code": 200,
        "data": {
            "records": page_data,
            "total": total,
            "page": page,
            "size": size
        }
    }


# --- Smart Scheduling Plan Endpoints ---

@router.post("/smart-scheduling/plan/pending/cancel")
async def cancel_pending_plan():
    """取消待确认的排产计划"""
    # TODO: 实现实际的取消逻辑
    return {"code": 200, "message": "Pending plan cancelled"}


@router.post("/smart-scheduling/plan/pending/confirm")
async def confirm_pending_plan():
    """确认待确认的排产计划"""
    # TODO: 实现实际的确认逻辑
    return {"code": 200, "message": "Pending plan confirmed"}
