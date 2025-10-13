# EasyRef 数据库设计文档

## 数据库概述

EasyRef 使用本地部署的 [Supabase](https://supabase.com/) 作为主要数据存储。

Supabase 基于 PostgreSQL，提供：
- 内置用户认证系统（GoTrue）
- RESTful API 自动生成
- 实时订阅功能（Realtime）
- 行级安全策略（RLS）
- 文件存储服务（Storage）
- 向量数据库支持（pgvector）

## 认证配置

- **认证服务地址**: `http://localhost:8000/`

## 数据库配置
```bash
docker compose pull
docker compose up -d
```

## 文件存储配置

### Storage Buckets
```sql
-- PDF文件存储桶
INSERT INTO storage.buckets (id, name, public)
VALUES ('papers', 'papers', false);

-- 用户头像存储桶
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true);
```

## 表关系说明

- `auth.users` ← `user_profiles` (一对一)
- `auth.users` ← `user_quotas` (一对一)
- `auth.users` ← `knowledge_bases` (一对多)
- `knowledge_bases` ← `knowledge_base_papers` → `papers` (多对多)
- `auth.users` ← `conversations` ← `conversation_messages` (一对多对多)
- `papers` ← `paper_files` (一对多，按用户)
- `papers` ← `paper_embeddings` (一对多)

## 索引和性能优化

### 主要索引
- 论文相关: 全文搜索、向量搜索、时间索引
- 用户相关: 用户ID、时间戳索引
- 知识库: 用户ID、名称、创建时间
- 对话: 会话ID、用户ID、时间索引
- 使用记录: 用户ID、操作类型、时间索引

### 性能优化策略
- 使用PostgreSQL GIN索引优化全文搜索
- 使用pgvector的IVFFlat索引优化向量搜索
- 适当的外键约束保证数据一致性
- 行级安全策略确保数据隔离
- 实时订阅优化用户体验

### 初始化脚本
- 使用Supabase Migration系统管理数据库版本
- 支持增量更新和回滚
- 自动化部署和环境同步

### 备份策略
- 利用Supabase的自动备份功能
- 定期导出用户数据和知识库
- Storage文件的独立备份策略
