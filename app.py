import os
import sys
import json
import logging
from flask import Flask, jsonify, request
from models import db
from scheduler import ProductionScheduler
from fact_api import fact_bp

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'app_config.json')

def _get_config_path():
    """获取配置文件路径，兼容 PyInstaller 打包后的环境。"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，配置文件与 exe 同级
        return os.path.join(os.path.dirname(sys.executable), 'app_config.json')
    else:
        return CONFIG_FILE

def load_config():
    path = _get_config_path()
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def _build_db_uri(cfg):
    """从拆分配置构建 SQLAlchemy 数据库连接 URI。"""
    return (
        f"mysql+pymysql://{cfg['db_user']}:{cfg['db_password']}"
        f"@{cfg['db_host']}:{cfg['db_port']}/{cfg['db_name']}"
    )

def create_app(config_input=None):
    cfg = load_config()
    mode = config_input if config_input else 'production'
    mode_cfg = cfg.get(mode, cfg.get('production', {}))

    app = Flask(__name__)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = _build_db_uri(cfg)
    app.config['DEBUG'] = mode_cfg.get('debug', False)
    if not app.config['DEBUG']:
        app.config['LOG_LEVEL'] = mode_cfg.get('log_level', 'INFO')
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = mode_cfg.get(
            'sqlalchemy_engine_options', {}
        )

    # 日志配置
    if not app.debug:
        log_level = app.config.get('LOG_LEVEL', 'INFO')
        logging.basicConfig(level=getattr(logging, log_level))
        app.logger.setLevel(getattr(logging, log_level))

    db.init_app(app)
    app.register_blueprint(fact_bp)

    @app.route('/', methods=['GET'])
    def health():
        """测试数据库连接。"""
        try:
            db.session.execute(db.text('SELECT 1'))
            return jsonify({"status": "ok", "message": "Database connection successful"})
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": "Database connection failed",
            }), 500

    @app.route('/solve/start', methods=['POST'])
    def schedule():
        # 前端发送 JSON，字段为 `lineId` 和 `begin`
        data = request.get_json(silent=True) or {}
        line_id = data.get('lineId') or data.get('line_id')
        start_date = data.get('begin') or data.get('start_date')

        # 尝试将 line_id 转为 int
        try:
            if line_id is not None:
                line_id = int(line_id)
        except Exception:
            pass

        if not line_id or not start_date:
            return jsonify({"status": "error", "message": "Missing lineId or begin"}), 400
            
        try:
            scheduler = ProductionScheduler(line_id, start_date)

            scheduler.fetch_data()
            results = scheduler.solve()
            
            if results is None:
                return jsonify({"status": "error", "message": "No feasible schedule found"}), 400
                
            return jsonify({
                "status": "success",
                "data": results
            })
        except Exception as e:
            response = {"status": "error", "message": str(e)}
            if app.debug:
                import traceback
                response["trace"] = traceback.format_exc()
            return jsonify(response), 500


    return app

if __name__ == '__main__':
    try:
        app = create_app('production')
        is_debug = app.config.get('DEBUG', False)
        app.run(debug=is_debug, host='0.0.0.0', port=8080)
    except Exception as e:
        print(f"[ERROR] Failed to start Flask app: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
