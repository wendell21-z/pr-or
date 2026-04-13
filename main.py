from data_models import get_default_data
from core_model import PunchingScheduler

def main():
    # 1. 获取数据
    data = get_default_data()
    
    # 2. 初始化调度器
    scheduler = PunchingScheduler(data)
    
    # 3. 求解
    try:
        result_tasks = scheduler.solve()
        print('Solver returned', len(result_tasks), 'active tasks')
        # Print simplified result
        for t in result_tasks:
            print(t)
    except Exception as e:
        print('Solve failed:', e)
        if hasattr(e, 'reasons'):
            for r in e.reasons:
                print(' -', r)

if __name__ == "__main__":
    main()
