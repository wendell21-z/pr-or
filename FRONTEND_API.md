# 前端接口适配文档

## 概述
本文档记录了为适配前端Vue应用而创建的所有后端API接口。

## 已实现的控制器

### 1. Fact Controller (`/fact/*`) - 基础数据管理
已存在，包含以下接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/fact/working-time` | 获取工作时间配置 |
| POST | `/fact/working-time` | 保存工作时间 |
| DELETE | `/fact/working-time/{text}` | 删除工作时间 |
| GET | `/fact/day` | 获取工作日列表 |
| POST | `/fact/day` | 添加工作日 |
| POST | `/fact/day/batch` | 批量添加工作日 |
| GET | `/fact/line` | 获取生产线列表 |
| POST | `/fact/line` | 添加生产线 |
| DELETE | `/fact/line/{id}` | 删除生产线 |
| GET | `/fact/die/all` | 获取所有模具 |
| POST | `/fact/die` | 添加模具 |
| POST | `/fact/die/batch` | 批量添加模具 |
| DELETE | `/fact/die/{id}` | 删除模具 |
| GET | `/fact/part/all` | 获取所有零件 |
| POST | `/fact/part` | 添加零件 |
| DELETE | `/fact/part/{id}` | 删除零件 |
| GET | `/fact/car/all` | 获取所有车型 |
| POST | `/fact/car` | 添加车型 |
| DELETE | `/fact/car/{id}` | 删除车型 |
| GET | `/fact/part-car` | 获取车型-零件关系 |
| POST | `/fact/part-car` | 添加车型-零件关系 |
| DELETE | `/fact/part-car/{id}` | 删除车型-零件关系 |
| GET | `/fact/part-inventory/all` | 获取所有零件库存 |
| POST | `/fact/part-inventory` | 更新零件库存 |
| POST | `/fact/part-inventory/batch` | 批量更新零件库存 |
| DELETE | `/fact/part-inventory/{id}` | 删除零件库存 |
| GET | `/fact/dunnage` | 获取器具列表 |
| POST | `/fact/dunnage` | 添加器具 |
| POST | `/fact/dunnage/batch` | 批量添加器具 |
| DELETE | `/fact/dunnage/{id}` | 删除器具 |
| GET | `/fact/dunnage-inventory/all` | 获取所有器具库存历史 |
| POST | `/fact/dunnage-inventory` | 添加器具库存 |
| POST | `/fact/dunnage-inventory/batch` | 批量添加器具库存 |
| DELETE | `/fact/dunnage-inventory/{id}` | 删除器具库存 |
| GET | `/fact/car-usage/all` | 获取所有车身流信息 |
| POST | `/fact/car-usage` | 添加车身流 |
| POST | `/fact/car-usage/batch` | 批量添加车身流 |
| DELETE | `/fact/car-usage/{id}` | 删除车身流 |

### 2. Solve Controller (`/solve/*`) - 排产求解
已扩展，新增接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/solve/start` | 启动排产求解 |
| GET | `/solve/is-running` | **[新增]** 检查是否有排产正在运行 |

| GET | `/solve/result/all` | **[新增]** 获取所有排产结果 |
| GET | `/solve/result/latest` | **[新增]** 获取最新排产结果预览 |

### 3. Solution Controller (`/solution/*`) - 方案管理
已扩展，包含以下接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/solution/task` | 添加固定任务 |
| PUT | `/solution/task` | 更新任务 |
| DELETE | `/solution/task?id={id}` | 删除任务 |
| GET | `/solution/task/swap?task1Id=&task2Id=` | 交换两个任务 |
| GET | `/solution/solve-result?lineId=&begin=&end=` | 获取排产结果（按周） |
| POST | `/solution/die-memo` | 添加模具备注 |
| DELETE | `/solution/die-memo?memoId=` | 删除模具备注 |
| GET | `/solution/die-memo` | 获取所有模具备注 |

### 4. IM Controller (`/im/*`) - WebSocket即时通讯
**新创建**，包含以下接口：

| 类型 | 路径 | 说明 |
|------|------|------|
| WebSocket | `/im/{tempLinkId}?logType=&value=` | IM WebSocket连接 |
| GET | `/im/message/count` | 获取剩余消息数量 |
| POST | `/im/message/count?count=` | 更新剩余消息数量 |

**WebSocket功能：**
- 连接时自动发送 `COMMAND_LOGIN_RESP` 触发前端回调
- 支持消息收发
- 断开时发送 `close` 类型消息
- Token验证占位符（需实现 `validate_token`）

### 5. Resource Controller (`/jvs-aps/*`) - 资源管理
**新创建**，包含以下接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/jvs-aps/production-resource/page` | 分页获取生产资源 |
| POST | `/jvs-aps/production-resource` | 创建生产资源 |
| PUT | `/jvs-aps/production-resource` | 更新生产资源 |
| GET | `/jvs-aps/production-resource/group/list` | 获取资源分组列表 |
| GET | `/jvs-aps/material/page` | 分页获取物料列表 |
| POST | `/jvs-aps/material` | 创建物料 |
| PUT | `/jvs-aps/material` | 更新物料 |
| DELETE | `/jvs-aps/material/{id}` | 删除物料 |
| POST | `/jvs-aps/process` | 创建工序 |
| GET | `/jvs-aps/process/{id}` | 获取工序详情 |
| PUT | `/jvs-aps/process` | 更新工序 |
| GET | `/jvs-aps/process/page` | 分页获取工序列表 |
| POST | `/jvs-aps/smart-scheduling/plan/pending/cancel` | 取消待确认排产计划 |
| POST | `/jvs-aps/smart-scheduling/plan/pending/confirm` | 确认待确认排产计划 |

**注意：** 这些接口目前返回临时模拟数据，需根据实际业务需求实现。

### 6. STOMP Controller (`/ws/*`) - WebSocket排产推送
**新创建**，包含以下接口：

| 类型 | 路径 | 说明 |
|------|------|------|
| WebSocket | `/ws/` | STOMP WebSocket连接 |

**STOMP功能：**
- 支持 STOMP 1.1 协议
- 前端连接到 `/ws` 并订阅 `/topic/solution`
- 实时推送排产方案更新
- 支持 CONNECT, SUBSCRIBE, UNSUBSCRIBE, SEND, DISCONNECT 命令

## 文件结构

```
controllers/
├── __init__.py                 # 导出所有控制器
├── fact_controller.py          # 基础数据管理 (已存在)
├── solve_controller.py         # 排产求解 (已扩展)
├── solution_controller.py      # 方案管理 (已扩展)
├── im_controller.py            # IM WebSocket (新增)
├── resource_controller.py      # 资源管理 (新增)
└── stomp_controller.py         # STOMP WebSocket (新增)
```

## 启动说明

```bash
# 激活虚拟环境并启动
cd /Users/Wendell/Development/fawvw/pr-or
.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# 访问文档
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

## 数据库配置

确保已配置MySQL连接：
```bash
export DATABASE_URL="mysql+pymysql://root:root@localhost:3306/pr_or?charset=utf8mb4"
```

并创建数据库：
```sql
CREATE DATABASE IF NOT EXISTS pr_or 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
```

## TODO项

以下功能需要后续实现：

1. **IM Controller**
   - [ ] Token验证逻辑 (`validate_token`)
   - [ ] 实际的消息存储和推送
   - [ ] 群组聊天支持

2. **Resource Controller**
   - [ ] 将临时内存数据改为数据库存储
   - [ ] 实现实际的业务逻辑

3. **STOMP Controller**
   - [ ] 在求解过程中实时推送进度更新
   - [ ] 添加身份验证

4. **通用**
   - [ ] 添加请求日志
   - [ ] 添加性能监控
   - [ ] 完善错误处理

## 前端连接示例

### REST API
```javascript
import request from '@/api/request'

// 获取所有模具
export function getAllDies() {
  return request({
    url: '/mgr/fact/die/all',
    method: 'get'
  })
}
```

### IM WebSocket
```javascript
const wsUrl = `ws://${location.host}/im/${tempLinkId}?logType=default&value=Bearer ${token}`
const socket = new WebSocket(wsUrl)
```

### STOMP WebSocket
```javascript
import SockJS from 'sockjs-client'
import Stomp from 'webstomp-client'

const socket = new SockJS('http://localhost:8000/ws')
const stompClient = Stomp.over(socket)
stompClient.connect({}, () => {
  stompClient.subscribe('/topic/solution', (message) => {
    const solution = JSON.parse(message.body)
    // 处理排产更新
  })
})
```
