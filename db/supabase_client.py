import os
from supabase import create_client, Client
from config import SUPABASE_CONFIG
import logging

logger = logging.getLogger(__name__)

class SupabaseInitializer:
    def __init__(self, supabase_url=None, ANON_KEY=None, SERVICE_ROLE_KEY=None):
        # 读取配置
        self.supabase_url = supabase_url if supabase_url else SUPABASE_CONFIG.get('url')
        self.ANON_KEY = ANON_KEY if ANON_KEY else SUPABASE_CONFIG.get('key')
        self.SERVICE_ROLE_KEY = SERVICE_ROLE_KEY if SERVICE_ROLE_KEY else SUPABASE_CONFIG.get('service_key')

        # 创建客户端
        # 用户登录：ANON_KEY
        # 管理员操作（文件存储等）：SERVICE_ROLE_KEY
        self.supabase: Client = create_client(self.supabase_url, self.ANON_KEY)
        self.supabase_admin: Client = create_client(self.supabase_url, self.SERVICE_ROLE_KEY)
        logger.info(f"Supabase client initialized with URL: {self.supabase_url}")