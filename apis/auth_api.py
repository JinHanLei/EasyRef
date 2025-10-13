from flask import Blueprint, jsonify, request
import logging

from db.paper_operations import PaperOperations
from db.supabase_client import SupabaseInitializer

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 初始化Supabase客户端
supabase_client = SupabaseInitializer().supabase

def get_authenticated_client():
    """
    获取已认证的Supabase客户端

    Returns:
        tuple: (认证状态, 用户ID, Supabase客户端实例, PaperOperations实例)
    """
    # 获取Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None, None

    try:
        token = auth_header.replace('Bearer ', '')
        if not token:
            return None, None

        supabase_init = SupabaseInitializer()
        supabase_client = supabase_init.supabase

        user_response = supabase_client.auth.get_user(token)
        if not user_response or not hasattr(user_response, 'user') or not user_response.user:
            return None, None

        user_id = str(user_response.user.id)

        supabase_client.options.headers.update({
            "Authorization": f"Bearer {token}"
        })

        return user_id, supabase_client
    except Exception as e:
        logger.warning(f"用户认证失败: {e}")
        return None, None


@auth_bp.route('/health', methods=['GET'])
def check_health():
    """认证模块健康检查"""
    try:
        # 这里可以添加认证服务的具体检查逻辑
        return jsonify({
            'module': 'auth',
            'status': 'healthy',
            'message': '认证模块运行正常'
        })
    except Exception as e:
        logger.error(f"认证模块健康检查失败: {e}")
        return jsonify({
            'module': 'auth',
            'status': 'error',
            'message': str(e)
        }), 500

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """用户注册"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'status': 'error',
                'message': '邮箱和密码不能为空'
            }), 400
            
        # 使用Supabase注册用户
        response = supabase_client.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response:
            return jsonify({
                'status': 'success',
                'message': '注册成功，请检查邮箱确认邮件',
                'user': {
                    'id': response.user.id,
                    'email': response.user.email
                }
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': '注册失败'
            }), 500
            
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'status': 'error',
                'message': '邮箱和密码不能为空'
            }), 400
            
        # 使用Supabase登录
        response = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response:
            return jsonify({
                'status': 'success',
                'message': '登录成功',
                'user': {
                    'id': response.user.id,
                    'email': response.user.email
                },
                'session': {
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token
                }
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': '登录失败'
            }), 401
            
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        return jsonify({
            'status': 'error',
            'message': '登录失败，用户名或密码错误'
        }), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户注销"""
    try:
        # 直接调用sign_out方法注销当前会话
        supabase_client.auth.sign_out()
            
        return jsonify({
            'status': 'success',
            'message': '注销成功'
        }), 200
        
    except Exception as e:
        logger.error(f"用户注销失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@auth_bp.route('/user', methods=['GET'])
def get_user():
    """获取当前用户信息"""
    try:
        # 获取当前用户
        user = supabase_client.auth.get_user()
        
        if user:
            return jsonify({
                'status': 'success',
                'user': {
                    'id': user.user.id,
                    'email': user.user.email,
                    'created_at': user.user.created_at
                }
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': '用户未登录'
            }), 401
            
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return jsonify({
            'status': 'error',
            'message': '用户未登录或会话已过期'
        }), 401


@auth_bp.route('/delete', methods=['DELETE'])
def delete_user():
    """删除当前用户账户"""
    try:
        # 获取当前用户
        user_response = supabase_client.auth.get_user()
        
        if not user_response:
            return jsonify({
                'status': 'error',
                'message': '用户未登录'
            }), 401
        
        user = user_response.user
        user_id = user.id
        
        # 删除用户账户
        response = supabase_client.auth.admin.delete_user(user_id)
        
        if response:
            return jsonify({
                'status': 'success',
                'message': '账户删除成功'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': '账户删除失败'
            }), 500
            
    except Exception as e:
        logger.error(f"删除用户账户失败: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
