# 数据库修改
1. car_usage 表去掉id字段，将car_id 和 day_id 作为复合主键
2. part_inventory 表去掉id字段，删除day字段，新增day_id字段，并将这两个字段作为复合主键
3. 零件库存 删除，将路由修改为 /part-inventory/<int:part_id>/<path:day_id>
4. 