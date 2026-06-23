"""
PyInstaller 启动脚本：处理 --onefile 模式下程序崩溃时保持窗口打开。
当程序因异常（如数据库连接失败）退出时，显示错误信息并保持窗口。
"""
import sys
import os
import traceback


def main():
    try:
        # 导入并运行主应用
        from app import create_app
        import os

        config_name = os.environ.get('FLASK_CONFIG', 'production')
        app = create_app(config_name)
        is_debug = app.config.get('DEBUG', False)
        app.run(debug=is_debug, host='0.0.0.0', port=8080)
    except ImportError as e:
        print(f"\n[ERROR] 缺少依赖模块: {e}")
        print("\n请确保已安装所有依赖:")
        print("  pip install -r requirements.txt")
        print("\nTraceback:")
        traceback.print_exc()
        input("\nPress Enter to exit...")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nTraceback:")
        traceback.print_exc()
        input("\nPress Enter to exit...")


if __name__ == '__main__':
    main()
