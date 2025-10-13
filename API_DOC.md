# EasyRef API接口文档

本文档详细介绍了EasyRef系统的各个API接口，包括认证、爬虫、知识库、大模型等相关功能。

## 文档说明

本文档将持续更新，包含系统所有模块的API接口说明。当前版本主要包含以下模块：
- 爬虫模块 (Crawler Module)

## 基础信息

- **基础URL**: 根据部署环境确定
- **数据格式**: JSON
- **认证方式**: 基于Supabase Auth的JWT Token

## 模块列表

### 1. 爬虫模块 (Crawler Module)

负责学术论文的搜索和获取功能。

#### 1.1 健康检查

检查爬虫模块的运行状态。

- **URL**: `/api/crawler/health`
- **方法**: `GET`
- **请求参数**: 无
- **响应示例**:
``json
{
  "module": "crawler",
  "status": "healthy",
  "message": "爬虫模块运行正常",
  "scholar_available": true
}
```

#### 1.2 搜索论文

搜索Google Scholar上的学术论文。

- **URL**: `/api/crawler/scholar`
- **方法**: `POST`
- **请求参数**:
```json
{
  "keyword": "summarization",           // 搜索关键词 (必需)
  "year_low": 2023,              // 起始年份 (可选)
  "year_high": 2025,             // 结束年份 (可选)
  "limit_num": 50,               // 最大返回结果数 (可选，默认50)
  "fetch_abstract": true,        // 是否获取摘要 (可选，默认false)
  "fetch_pdf": true              // 是否下载PDF (可选，默认false)
}
```

- **响应示例**:
```json
{
  "success": true,
  "message": "成功获取 10 篇论文",
  "total": 10,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "papers": [
    {
      "title": "论文标题",
      "authors": "作者列表",
      "pub_year": 2024,
      "pub_url": "https://example.com/paper",
      "abstract": "论文摘要内容",
      "pdf_url": "存储路径",
      "file_size": 123456
    }
  ]
}
```

#### 1.3 上传PDF文件

用户上传本地PDF文件到系统。

- **URL**: `/api/crawler/upload-pdf`
- **方法**: `POST`
- **请求参数**:
  - `file`: PDF文件 (必需)
  - `title`: 论文标题 (可选，默认使用文件名)
  - `authors`: 作者信息 (可选)
  - `pub_year`: 发表年份 (可选)
  - `pub_url`: 论文链接 (可选)

- **响应示例**:
```json
{
  "success": true,
  "message": "PDF文件上传成功",
  "paper_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_size": 123456,
  "deduplicated": false
}
```

#### 1.4 将任务移到后台

将在前台运行的任务移动到后台执行。

- **URL**: `/api/crawler/move-to-background`
- **方法**: `POST`
- **请求参数**:
```json
{
  "session_id": "uuid-string"    // 会话ID (必需)
}
```

- **响应示例**:
```json
{
  "success": true,
  "message": "任务已移动到后台执行",
  "session_id": "uuid-string"
}
```

#### 1.5 取消搜索任务

取消正在进行的搜索任务。

- **URL**: `/api/crawler/cancel-search`
- **方法**: `POST`
- **请求参数**:
```json
{
  "session_id": "uuid-string"    // 会话ID (必需)
}
```

- **响应示例**:
```json
{
  "success": true,
  "message": "搜索任务已标记为取消",
  "task_status": { /* 任务状态信息 */ }
}
```

#### 1.6 查询搜索任务状态

查询搜索任务的当前状态。

- **URL**: `/api/crawler/search-status`
- **方法**: `GET`
- **请求参数**:
```
?session_id=uuid-string          // 会话ID (必需)
```

- **响应示例**:
```json
{
  "success": true,
  "status": {
    "session_id": "uuid-string",
    "status": "running",           // 状态: pending, running, completed, cancelled, error
    "progress": 15,
    "total": 20,
    "message": "已处理 15/20 篇论文",
    "created_at": 1234567890,
    "updated_at": 1234567890,
    "is_background": false         // 是否在后台运行
  }
}
```

#### 1.7 获取搜索结果

分页获取搜索到的论文列表。

- **URL**: `/api/crawler/papers`
- **方法**: `GET`
- **请求参数**:
```
?session_id=uuid-string          // 会话ID (必需)
&page=1                          // 页码 (可选，默认1)
&per_page=20                     // 每页数量 (可选，默认20，最大100)
```

- **响应示例**:
```json
{
  "success": true,
  "data": [ /* 论文列表 */ ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  }
}
```

## 任务状态说明

搜索任务可能处于以下状态之一：

- `pending`: 任务已创建但尚未开始
- `running`: 任务正在执行中
- `completed`: 任务已完成
- `cancelled`: 任务已被取消
- `error`: 任务执行出错

## 使用流程

### 前台搜索流程

1. 前端调用 `/api/crawler/scholar` 发起搜索请求
2. 通过SSE流式接收进度更新
3. 用户可随时调用 `/api/crawler/move-to-background` 将任务移到后台
4. 任务完成后，通过 `/api/crawler/papers` 分页获取结果

### 后台任务管理流程

1. 前端调用 `/api/crawler/scholar` 发起搜索请求
2. 立即调用 `/api/crawler/move-to-background` 将任务移到后台
3. 通过 `/api/crawler/search-status` 定期查询任务状态
4. 任务完成后，通过 `/api/crawler/papers` 分页获取结果

## 错误处理

所有接口都遵循统一的错误响应格式:

```json
{
  "success": false,
  "message": "错误描述"
}
```

HTTP状态码:
- `200`: 请求成功
- `400`: 请求参数错误
- `404`: 资源未找到
- `500`: 服务器内部错误

## 注意事项

1. **会话管理**: 每次搜索都会生成一个唯一的`session_id`，用于关联搜索结果和任务状态
2. **数据存储**: 搜索结果会存储在`user_search_results`表中，与用户会话关联
3. **重复处理**: 系统会自动检测并避免重复存储相同的论文
4. **后台执行**: 任务切换到后台后，即使前端断开连接也会继续执行
5. **资源清理**: 已完成或取消的任务信息会定期清理