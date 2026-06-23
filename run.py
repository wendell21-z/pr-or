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

        config_name = os.environ.get('FLASK_CONFIG', 'production')
        app = create_app(config_name)
        is_debug = app.config.get('DEBUG', False)
        app.run(debug=is_debug, host='0.0.0.0', port=8080)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\nTraceback:")
        traceback.print_exc()
        print("\nPress Enter to exit...")
        sys.stdin.read()


if __name__ == '__main__':
    main()
