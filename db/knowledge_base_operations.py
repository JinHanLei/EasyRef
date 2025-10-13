from typing import List, Dict, Optional, Any
import logging
from .supabase_client import SupabaseInitializer

logger = logging.getLogger(__name__)

class KnowledgeBaseOperations:
    """知识库数据库操作类"""
    
    def __init__(self):
        self.db_init = SupabaseInitializer()
        self.supabase = self.db_init.supabase
    
    def create_knowledge_base(self, user_id: str, name: str, description: str = None, is_public: bool = False) -> Optional[str]:
        """新建知识库
        
        Args:
            user_id: 用户ID
            name: 知识库名称
            description: 知识库描述（可选）
            is_public: 是否公开
            
        Returns:
            str: 创建成功返回知识库ID，失败返回None
        """
        try:
            kb_data = {
                "user_id": user_id,
                "name": name,
                "description": description,
                "is_public": is_public,
                "paper_count": 0,
                "total_size": 0
            }
            
            result = self.supabase.table('knowledge_bases').insert(kb_data).execute()
            if result.data:
                kb_id = result.data[0]['id']
                
                # 自动将创建者添加为admin成员
                member_data = {
                    "knowledge_base_id": kb_id,
                    "user_id": user_id,
                    "permission_level": "admin",
                    "invited_by": user_id  # 自己邀请自己
                }
                self.supabase.table('knowledge_base_members').insert(member_data).execute()
                
                logger.info(f"知识库创建成功: {kb_id}")
                return kb_id
            return None
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
            return None

    def update_knowledge_base(self, kb_id: str, user_id: str, name: str = None, description: str = None,
                              is_public: bool = None) -> bool:
        """修改知识库信息

        Args:
            kb_id: 知识库ID
            user_id: 用户ID（用于权限验证）
            name: 知识库名称（可选）
            description: 知识库描述（可选）
            is_public: 是否公开（可选）

        Returns:
            bool: 修改是否成功
        """
        try:
            # 构建更新数据
            update_data = {"updated_at": "NOW()"}

            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if is_public is not None:
                update_data["is_public"] = is_public

            # 只有数据有变化才执行更新
            if len(update_data) == 1:  # 只有updated_at
                return True
            result = self.supabase.table('knowledge_bases').update(update_data).eq('id', kb_id).eq('user_id',
                                                                                                   user_id).execute()
            if result.data:
                return True
        except Exception as e:
            logger.error(f"修改知识库失败: {kb_id}, {e}")
            return False

    def batch_add_papers_to_knowledge_base(self, kb_id: str, paper_ids: List[str], user_id: str) -> int:
        """关联论文到知识库
        
        Args:
            kb_id: 知识库ID
            paper_ids: 论文ID列表
            user_id: 用户ID
            
        Returns:
            int: 成功关联的论文数量
        """
        try:
            relations_data = [
                {
                    "knowledge_base_id": kb_id,
                    "paper_id": paper_id,
                    "added_by": user_id
                }
                for paper_id in paper_ids
            ]
            
            result = self.supabase.table('knowledge_base_papers').insert(relations_data).execute()
            success_count = len(result.data) if result.data else 0
            if success_count > 0:
                self._update_knowledge_base_stats(kb_id)
            return success_count
        except Exception as e:
            logger.error(f"批量关联论文失败: {e}")
            return 0

    def batch_remove_papers_from_knowledge_base(self, kb_id: str, paper_ids: List[str], user_id: str, soft_delete: bool = True) -> int:
        """从知识库中删除论文（支持软删除）
        
        Args:
            kb_id: 知识库ID
            paper_ids: 论文ID列表
            user_id: 用户ID
            soft_delete: 是否软删除（放入回收站）
            
        Returns:
            int: 成功删除的论文数量
        """
        try:
            if soft_delete:
                # 批量获取论文信息用于回收站
                papers_result = self.supabase.table('papers').select('id, title').in_('id', paper_ids).execute()
                papers_dict = {paper['id']: paper['title'] for paper in papers_result.data} if papers_result.data else {}
                
                # 批量添加到回收站
                recycle_data = [
                    {
                        "paper_id": paper_id,
                        "knowledge_base_id": kb_id,
                        "user_id": user_id,
                        "original_title": papers_dict.get(paper_id, "Unknown"),
                        "deleted_by": user_id
                    }
                    for paper_id in paper_ids if paper_id in papers_dict
                ]
                
                if recycle_data:
                    self.supabase.table('paper_recycle_bin').insert(recycle_data).execute()
            
            # 批量删除关联关系
            result = self.supabase.table('knowledge_base_papers').delete().eq('knowledge_base_id', kb_id).in_('paper_id', paper_ids).execute()
            success_count = len(paper_ids)
            
            if success_count > 0:
                # 更新知识库统计
                self._update_knowledge_base_stats(kb_id)
            return success_count
            
        except Exception as e:
            logger.error(f"批量删除论文失败: {e}")
            return 0

    def get_recycle_bin_papers(self, user_id: str, kb_id: str = None) -> List[Dict[str, Any]]:
        """获取回收站中的论文
        
        Args:
            user_id: 用户ID
            kb_id: 知识库ID（可选，不指定则获取所有）
            
        Returns:
            List[Dict]: 回收站论文列表
        """
        try:
            query = self.supabase.table('paper_recycle_bin').select('*').eq('user_id', user_id)
            
            if kb_id:
                query = query.eq('knowledge_base_id', kb_id)
            result = query.order('deleted_at', desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"获取回收站失败: {e}")
            return []
    
    def restore_paper_from_recycle_bin(self, recycle_id: str, user_id: str) -> bool:
        """从回收站恢复论文
        
        Args:
            recycle_id: 回收站记录ID
            user_id: 用户ID
            
        Returns:
            bool: 恢复是否成功
        """
        try:
            # 获取回收站记录
            recycle_result = self.supabase.table('paper_recycle_bin').select('*').eq('id', recycle_id).eq('user_id', user_id).execute()
            
            if not recycle_result.data:
                return False
            
            recycle_item = recycle_result.data[0]
            
            # 恢复关联关系
            relation_data = {
                "knowledge_base_id": recycle_item['knowledge_base_id'],
                "paper_id": recycle_item['paper_id'],
                "added_by": user_id
            }
            
            self.supabase.table('knowledge_base_papers').insert(relation_data).execute()
            
            # 删除回收站记录
            self.supabase.table('paper_recycle_bin').delete().eq('id', recycle_id).execute()
            
            # 更新知识库统计
            self._update_knowledge_base_stats(recycle_item['knowledge_base_id'])
            return True
            
        except Exception as e:
            logger.error(f"恢复论文失败: {e}")
            return False
    
    def permanently_delete_from_recycle_bin(self, recycle_id: str, user_id: str) -> bool:
        """从回收站永久删除论文记录
        
        Args:
            recycle_id: 回收站记录ID
            user_id: 用户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            result = self.supabase.table('paper_recycle_bin').delete().eq('id', recycle_id).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"永久删除论文失败: {e}")
            return False
    
    def get_knowledge_base_papers(self, kb_id: str) -> List[Dict[str, Any]]:
        """获取知识库中的所有论文"""
        try:
            result = self.supabase.table('knowledge_base_papers').select(
                '*, papers(*)'
            ).eq('knowledge_base_id', kb_id).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"获取知识库论文失败: {e}")
            return []
    
    def _update_knowledge_base_stats(self, kb_id: str):
        """更新知识库统计信息"""
        try:
            # 获取论文数量
            count_result = self.supabase.table('knowledge_base_papers').select('id', count='exact').eq('knowledge_base_id', kb_id).execute()
            paper_count = count_result.count or 0
            
            # 更新统计
            self.supabase.table('knowledge_bases').update({
                'paper_count': paper_count,
                'updated_at': 'NOW()'
            }).eq('id', kb_id).execute()
            
        except Exception as e:
            logger.error(f"更新知识库统计失败: {e}")

    def invite_user_to_knowledge_base(self, kb_id: str, inviter_id: str, invitee_email: str, permission_level: str = 'view') -> bool:
        """邀请用户加入知识库

        Args:
            kb_id: 知识库ID
            inviter_id: 邀请人ID
            invitee_email: 被邀请人邮箱
            permission_level: 权限级别

        Returns:
            bool: 邀请是否成功
        """
        try:
            import uuid
            invitation_token = str(uuid.uuid4())

            invitation_data = {
                "knowledge_base_id": kb_id,
                "inviter_id": inviter_id,
                "invitee_email": invitee_email,
                "permission_level": permission_level,
                "invitation_token": invitation_token,
                "status": "pending"
            }

            result = self.supabase.table('knowledge_base_invitations').insert(invitation_data).execute()
            if result.data:
                return True
            return False
        except Exception as e:
            logger.error(f"发送知识库邀请失败: {e}")
            return False

    def accept_knowledge_base_invitation(self, invitation_token: str, user_id: str) -> bool:
        """接受知识库邀请
    
        Args:
            invitation_token: 邀请令牌
            user_id: 接受邀请的用户ID
        
        Returns:
            bool: 接受是否成功
        """
        try:
            # 获取邀请信息
            invitation_result = self.supabase.table('knowledge_base_invitations').select('*').eq('invitation_token', invitation_token).eq('status', 'pending').execute()
        
            if not invitation_result.data:
                logger.error("邀请不存在或已过期")
                return False
        
            invitation = invitation_result.data[0]
        
            # 检查邀请是否过期
            from datetime import datetime
            if datetime.now() > datetime.fromisoformat(invitation['expires_at'].replace('Z', '+00:00')):
                # 更新邀请状态为过期
                self.supabase.table('knowledge_base_invitations').update({'status': 'expired'}).eq('id', invitation['id']).execute()
                return False
        
            # 添加到成员表
            member_data = {
                "knowledge_base_id": invitation['knowledge_base_id'],
                "user_id": user_id,
                "permission_level": invitation['permission_level'],
                "invited_by": invitation['inviter_id']
            }
        
            member_result = self.supabase.table('knowledge_base_members').insert(member_data).execute()
        
            if member_result.data:
                # 更新邀请状态为已接受
                self.supabase.table('knowledge_base_invitations').update({
                    'status': 'accepted',
                    'accepted_at': 'NOW()'
                }).eq('id', invitation['id']).execute()
                return True
        
            return False
        
        except Exception as e:
            logger.error(f"接受知识库邀请失败: {e}")
            return False

    def update_member_permission(self, kb_id: str, member_user_id: str, new_permission_level: str, operator_user_id: str) -> bool:
        """修改成员权限
    
        Args:
            kb_id: 知识库ID
            member_user_id: 被修改权限的用户ID
            new_permission_level: 新的权限级别 ('view', 'edit', 'admin')
            operator_user_id: 操作者用户ID（需要是知识库所有者或管理员）
        
        Returns:
            bool: 修改是否成功
        """
        try:
            # 验证操作者权限（必须是知识库所有者或管理员）
            kb_result = self.supabase.table('knowledge_bases').select('user_id').eq('id', kb_id).execute()
            if not kb_result.data:
                return False
        
            is_owner = kb_result.data[0]['user_id'] == operator_user_id
            is_admin = False
        
            if not is_owner:
                # 检查是否是管理员
                admin_result = self.supabase.table('knowledge_base_members').select('permission_level').eq('knowledge_base_id', kb_id).eq('user_id', operator_user_id).execute()
                is_admin = admin_result.data and admin_result.data[0]['permission_level'] == 'admin'
        
            if not (is_owner or is_admin):
                logger.error("无权限修改成员权限")
                return False
        
            # 更新成员权限
            result = self.supabase.table('knowledge_base_members').update({
                'permission_level': new_permission_level
            }).eq('knowledge_base_id', kb_id).eq('user_id', member_user_id).execute()
        
            if result.data:
                return True
            return False
        
        except Exception as e:
            logger.error(f"修改成员权限失败: {e}")
            return False

    def remove_knowledge_base_member(self, kb_id: str, member_user_id: str, operator_user_id: str) -> bool:
        """移除知识库成员
    
        Args:
            kb_id: 知识库ID
            member_user_id: 被移除的用户ID
            operator_user_id: 操作者用户ID
        
        Returns:
            bool: 移除是否成功
        """
        try:
            # 验证操作者权限
            kb_result = self.supabase.table('knowledge_bases').select('user_id').eq('id', kb_id).execute()
            if not kb_result.data:
                return False
        
            is_owner = kb_result.data[0]['user_id'] == operator_user_id
            is_admin = False
        
            if not is_owner:
                admin_result = self.supabase.table('knowledge_base_members').select('permission_level').eq('knowledge_base_id', kb_id).eq('user_id', operator_user_id).execute()
                is_admin = admin_result.data and admin_result.data[0]['permission_level'] == 'admin'
        
            if not (is_owner or is_admin):
                return False
        
            result = self.supabase.table('knowledge_base_members').delete().eq('knowledge_base_id', kb_id).eq('user_id', member_user_id).execute()
            return True
        
        except Exception as e:
            logger.error(f"移除知识库成员失败: {e}")
            return False

    def transfer_ownership(self, kb_id: str, current_owner_id: str, new_owner_id: str) -> bool:
        """转让知识库所有权
    
        Args:
            kb_id: 知识库ID
            current_owner_id: 当前所有者ID
            new_owner_id: 新所有者ID
        
        Returns:
            bool: 转让是否成功
        """
        try:
            # 验证当前用户是所有者
            kb_result = self.supabase.table('knowledge_bases').select('user_id').eq('id', kb_id).eq('user_id', current_owner_id).execute()
            if not kb_result.data:
                logger.error("无权限转让知识库")
                return False
            
            # 检查新所有者是否已经是成员
            member_result = self.supabase.table('knowledge_base_members').select('*').eq('knowledge_base_id', kb_id).eq('user_id', new_owner_id).execute()

            if member_result.data:
                # 如果新所有者已经是成员，更新其权限为admin
                self.supabase.table('knowledge_base_members').update({
                    'permission_level': 'admin',
                    'updated_at': 'NOW()'
                }).eq('knowledge_base_id', kb_id).eq('user_id', new_owner_id).execute()

            # 将原所有者权限降为edit
            self.supabase.table('knowledge_base_members').update({
                'permission_level': 'edit'
            }).eq('knowledge_base_id', kb_id).eq('user_id', current_owner_id).execute()
            return True
            
        except Exception as e:
            logger.error(f"转让知识库所有权失败: {e}")
            return False

