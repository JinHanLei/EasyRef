# 配置文件
import os
from dotenv import load_dotenv

env_path = os.path.join('db', 'er_supabase', '.env')
load_dotenv(env_path)

SUPABASE_CONFIG = {
    'url': os.getenv('SUPABASE_PUBLIC_URL'),
    'key': os.getenv('ANON_KEY'),
    'service_key': os.getenv('SERVICE_ROLE_KEY'),
    'papers_bucket_name': 'papers',
}

# MYSQL_CONFIG = {
#     'host': os.getenv('MYSQL_HOST', 'localhost'),
#     'port': os.getenv('MYSQL_PORT', 3306),
#     'user': os.getenv('MYSQL_USER', 'root'),
#     'password': os.getenv('MYSQL_ROOT_PASSWORD', 'P@ssw0rd'),
#     'database': os.getenv('MYSQL_NAME', 'easyref'),
#     'charset': 'utf8mb4'
# }

# OSS配置
# OSS_CONFIG = {
#     'endpoint': os.getenv('OSS_ENDPOINT', 'http://127.0.0.1:9000'),
#     'access_key': os.getenv('RUSTFS_ACCESS_KEY', 'errustfs'),
#     'secret_key': os.getenv('RUSTFS_SECRET_KEY', 'errustfs'),
#     'bucket_name': os.getenv('OSS_BUCKET_NAME', 'easyref'),
#     'volume': os.getenv('OSS_VOLUME', "/e/rustfs/data:/data")
# }

# OpenAI配置
OPENAI_CONFIG = {
    'api_key': os.getenv('OPENAI_API_KEY', 'none'),
    'base_url': os.getenv('OPENAI_BASE_URL', 'your-base-url'),
    'model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
}

# Flask配置
FLASK_CONFIG = {
    'host': os.getenv('FLASK_HOST', '0.0.0.0'),
    'port': int(os.getenv('FLASK_PORT', 5000)),
    'debug': os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
}

# 代理配置（可选）
PROXY_CONFIG = {
    'enabled': False,
    'http': os.getenv('PROXY_HTTP', '127.0.0.1:7890'),
    'https': os.getenv('PROXY_HTTPS', 'http://127.0.0.1:7890')
}
