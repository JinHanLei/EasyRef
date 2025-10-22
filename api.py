from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import logging
from config import FLASK_CONFIG

# 配置日志
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 创建Flask应用
app = Flask(__name__)
CORS(app)

from apis.auth_api import auth_bp
from apis.scholar_api import scholar

app.register_blueprint(auth_bp)
app.register_blueprint(scholar)

logger = logging.getLogger(__name__)

@app.route('/api/health', methods=['GET'])
def health_check():
    """基础健康检查"""
    return jsonify({
        'status': 'healthy',
        'message': 'Welcome to EasyRef API',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    app.run(port=FLASK_CONFIG.get('port'), debug=True)