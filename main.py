from data_models import get_default_data
from core_model import PunchingScheduler

def main():
    # 1. 获取数据
    data = get_default_data()
    
    # 2. 初始化调度器
    scheduler = PunchingScheduler(data)
    
    # 3. 求解
    solver, status, reasons = scheduler.solve()
    
    # 4. 打印结果
    scheduler.print_solution(solver, status)

if __name__ == "__main__":
    main()
