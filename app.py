from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import logging
from controllers import solve_controller, solution_controller, fact_controller, im_controller, resource_controller, stomp_controller
from storage import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init DB engine, load persisted storage
    db.init_engine()
    db.load()
    logging.info("Storage loaded on startup")
    yield
    # Shutdown: save persisted storage, close engine
    db.save()
    db.close_engine()
    logging.info("Storage saved on shutdown")


app = FastAPI(
    title="OptaPlanner Scheduler API",
    description="基于 API_SUMMARY.md 实现的生产计划优化系统接口",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(solve_controller.router)
app.include_router(solution_controller.router)
app.include_router(fact_controller.router)
app.include_router(im_controller.router)
app.include_router(resource_controller.router)
app.include_router(stomp_controller.router)

# 挂载静态文件
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def root():
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Welcome to OptaPlanner Scheduler API. Visit /docs for documentation."}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
