# API 接口文档汇总

本文档总结了项目中所有的 API 接口，按功能模块进行分类。

---

## 1. 求解器接口 (SolveController)
用于管理和监控 OptaPlanner 求解器的运行状态。

### 1.1 启动求解器
- **URL**: `/solve/start`
- **方法**: `POST`
- **描述**: 从数据库读取基础数据并启动 OptaPlanner 求解器进行生产计划优化（排产7天计划）。
- **请求体**: `SolveDto`
    - `lineId` (Int): 线体ID
    - `begin` (LocalDate): 开始日期
- **校验**: 
    - 开始日期必须有器具和零件库存记录。
    - 开始日期不能晚于该线体最新已完成任务的日期。


### 1.3 查看运行中的任务
- **URL**: `/solve/is-running`
- **方法**: `GET`
- **描述**: 获取当前正在运行的求解任务列表。

### 1.4 查看求解器状态
- **URL**: `/solve/status`
- **方法**: `GET`
- **描述**: 根据线体 ID 获取求解器的具体状态。
- **请求参数**: `linId` (线体ID)

---

## 2. 任务与排产结果 (SolutionController)
用于管理排产任务（添加、修改、删除、交换）以及获取排产结果。

### 2.1 添加固定任务
- **URL**: `/solution/task`
- **方法**: `POST`
- **描述**: 为指定模具在特定日期和顺序位置添加固定任务。
- **请求体**: `PinnedTaskDto`
    - `day` (LocalDate): 日期
    - `dieId` (Int): 模具ID
    - `seqInDay` (Int, optional): 日期内顺序位置
    - `quantity` (Int, optional): 任务数量

### 2.2 修改任务
- **URL**: `/solution/task`
- **方法**: `PUT`
- **描述**: 修改指定 ID 的任务信息（如数量、固定类型等）。如果标记为已完成，会触发备忘录处理。
- **请求体**: `UpdateTaskDto`
    - `taskId` (Long): 任务ID
    - `pinnedType` (Int, optional): 固定类型 (0-普通, 1-用户指定, 2-已完成)
    - `quantity` (Int, optional): 任务数量

### 2.3 删除任务
- **URL**: `/solution/task`
- **方法**: `DELETE`
- **描述**: 根据 ID 删除指定的任务。
- **请求参数**: `id` (任务ID)

### 2.4 交换两个任务位置
- **URL**: `/solution/task/swap`
- **方法**: `GET`
- **描述**: 交换两个任务的日期和顺序。两个任务必须属于同一线体且未完成。
- **请求参数**: `task1Id`, `task2Id`

### 2.5 获取排产结果列表
- **URL**: `/solution/solve-result`
- **方法**: `GET`
- **描述**: 根据线体 ID 和时间范围获取排产结果。
- **请求参数**: `lineId`, `begin`, `end`

### 2.6 记录 (DieMemo)
- **添加/修改**: `POST /solution/die-memo`
    - **请求体**: `MemoDto`
        - `dieId` (Int): 模具ID
        - `content` (String): 备注内容
- **删除**: `DELETE /solution/die-memo` (请求参数: `memoId`)
- **获取所有**: `GET /solution/die-memo`

---

## 3. 基础数据管理 (FactController)
用于维护系统中的基础数据（零件、车型、模具、线体、工作时间等）。

### 3.1 工作时间 (WorkingTime)
- **添加/更新**: `POST /fact/working-time`
    - **请求体**: `WokingTimeDto`
        - `text` (String): 工作时间描述
        - `minutes` (Int): 工作时间 (分钟)
- **获取所有**: `GET /fact/working-time`
- **删除**: `DELETE /fact/working-time/{text}`

### 3.2 日期配置 (Day)
- **添加/更新**: `POST /fact/day`
    - **请求体**: `DayDto`
        - `day` (LocalDate): 日期
        - `workingTimeText` (String): 工作时间文本
        - `outMinutes` (Int): 计划外时间 (分钟)
- **批量添加/更新**: `POST /fact/day/batch`
    - **请求体**: `List<DayDto>`
- **获取所有**: `GET /fact/day`

### 3.3 线体 (Line)
- **添加/更新**: `POST /fact/line`
    - **请求体**: `LineDto`
        - `id` (Int, optional): 线体ID
        - `code` (String): 线体编码
        - `description` (String): 线体描述
- **获取所有**: `GET /fact/line`
- **删除**: `DELETE /fact/line/{id}`

### 3.4 模具 (Die)
- **添加/更新**: `POST /fact/die`
    - **请求体**: `DieDto`
        - `code` (String): 模具编码
        - `name` (String): 模具名称
        - `akz` (Int): 每分钟产能 (AKZ)
        - `lineId` (Int): 线体ID
- **批量添加**: `POST /fact/die/batch`
    - **请求体**: `List<DieDto>`
- **获取所有**: `GET /fact/die/all`
- **删除**: `DELETE /fact/die/{id}`

### 3.5 零件 (Part)
- **添加**: `POST /fact/part`
    - **请求体**: `PartDto`
        - `code` (String): 零件号
        - `name` (String): 零件名称
        - `min` (Int): 最小库存
        - `dieId` (Int): 所属模具ID
        - `dunnageId` (Int): 所属器具ID
- **获取所有**: `GET /fact/part/all`
- **删除**: `DELETE /fact/part/{id}`

### 3.6 车型 (Car)
- **添加/更新**: `POST /fact/car`
    - **请求体**: `CarDto`
        - `code` (String): 车型编码
        - `name` (String): 车型名称
- **获取所有**: `GET /fact/car/all`
- **删除**: `DELETE /fact/car/{id}`

### 3.7 车型-零件关系 (CarPart)
- **添加/更新**: `POST /fact/part-car`
    - **请求体**: `CarPartDto`
        - `carId` (Int): 车型ID
        - `partId` (Int): 零件ID
        - `usage` (Int): 使用量
- **获取所有**: `GET /fact/part-car`
- **删除**: `DELETE /fact/part-car/{id}`

---

## 4. 库存与车身流 (FactController)

### 4.1 零件库存 (PartInventory)
- **添加/更新**: `POST /fact/part-inventory`
    - **请求体**: `PartInventoryDto`
        - `part` (String): 零件号
        - `day` (LocalDate): 日期
        - `quantity` (Int): 库存数量
- **批量添加/更新**: `POST /fact/part-inventory/batch`
    - **请求体**: `List<PartInventoryDto>`
- **获取所有**: `GET /fact/part-inventory/all`
- **删除**: `DELETE /fact/part-inventory/{id}`

### 4.2 器具管理 (Dunnage)
- **添加/更新**: `POST /fact/dunnage`
    - **请求体**: `DunnageDto`
        - `name` (String): 器具名称
        - `capacity` (Int): 器具容量
- **批量添加**: `POST /fact/dunnage/batch`
    - **请求体**: `List<DunnageDto>`
- **获取所有**: `GET /fact/dunnage`
- **删除**: `DELETE /fact/dunnage/{id}`

### 4.3 器具库存 (DunnageInventoryHistory)
- **添加/更新**: `POST /fact/dunnage-inventory`
    - **请求体**: `DunnageInventoryHistoryDto`
        - `day` (LocalDate): 日期
        - `dunnageId` (Int): 器具ID
        - `quantity` (Int): 总数量
        - `emptyQuantity` (Int): 空器具数量
        - `repairQuantity` (Int): 维修中数量
        - `sealedQuantity` (Int): 封存数量
        - `pendingRepairQuantity` (Int): 待维修数量
        - `weldingQuantity` (Int): 焊装数量
- **批量添加/更新**: `POST /fact/dunnage-inventory/batch`
    - **请求体**: `List<DunnageInventoryHistoryDto>`
- **获取最新**: `GET /fact/dunnage-inventory/latest`
- **获取指定日期**: `GET /fact/dunnage-inventory?day=yyyy-MM-dd`
- **获取所有历史**: `GET /fact/dunnage-inventory/all`
- **删除**: `DELETE /fact/dunnage-inventory/{id}`

### 4.4 车身流信息 (CarUsage)
- **添加**: `POST /fact/car-usage`
    - **请求体**: `CarUsageDto`
        - `carId` (Int): 车型ID
        - `day` (LocalDate): 日期
        - `num` (Int): 数量
- **批量添加**: `POST /fact/car-usage/batch`
    - **请求体**: `List<CarUsageDto>`
- **获取所有**: `GET /fact/car-usage/all`
- **删除**: `DELETE /fact/car-usage/{id}`

---

## 5. 性能测试 (BenchmarkController)

### 5.1 运行性能测试
- **URL**: `/benchmark/run`
- **方法**: `GET`
- **描述**: 启动 OptaPlanner 求解器性能测试，测试不同配置下的求解性能（当前代码中逻辑已注释）。
