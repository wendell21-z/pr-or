import os
import logging
from flask import Flask, jsonify, request
from config import config
from models import db
from scheduler import ProductionScheduler
from fact_api import fact_bp

def create_app(config_input=None):
    if config_input is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
        config_obj = config[config_name]
    elif isinstance(config_input, str):
        config_obj = config[config_input]
    else:
        config_obj = config_input

    app = Flask(__name__)
    app.config.from_object(config_obj)

    # 日志配置
    if not app.debug:
        log_level = app.config.get('LOG_LEVEL', 'INFO')
        logging.basicConfig(level=getattr(logging, log_level))
        app.logger.setLevel(getattr(logging, log_level))

    db.init_app(app)
    app.register_blueprint(fact_bp)

    @app.route('/')
    def index():
        return jsonify({"message": "Flask project with DB entities created successfully!"})

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
    config_name = os.environ.get('FLASK_CONFIG', 'production')
    app = create_app(config_name)
    is_debug = app.config.get('DEBUG', False)
    app.run(debug=is_debug, host='0.0.0.0', port=8080)
