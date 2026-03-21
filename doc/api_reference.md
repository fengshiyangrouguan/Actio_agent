# API 参考文档

## 1. 概述

Actio Agent 后端提供 RESTful API 和 Server-Sent Events (SSE) 流式接口，用于前端与智能体系统的交互。所有 API 遵循 JSON 格式，基础路径为 `/api`。

### 1.1 基础信息

- **基础 URL**: `http://localhost:8000`
- **API 版本**: v1
- **响应格式**: JSON
- **事件流格式**: text/event-stream

## 2. 健康检查

### 2.1 GET /health

检查服务运行状态。

**请求示例**:
```bash
curl http://localhost:8000/health
```

**响应示例**:
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 3. 机器人身份管理

### 3.1 GET /api/profile

获取当前机器人身份信息和运行模式。

**请求示例**:
```bash
curl http://localhost:8000/api/profile
```

**响应示例**:
```json
{
  "mode": "main",
  "bot_profile": {
    "bot_name": "小智",
    "bot_personality": "热情、乐于助人的机器人助手"
  }
}
```

**模式说明**:
- `setup`: 初始化模式，需要用户设置机器人名称和人格
- `main`: 正常运行模式

### 3.2 POST /api/profile

更新机器人身份信息（仅限 setup 模式）。

**请求体**:
```json
{
  "bot_name": "小智",
  "bot_personality": "热情、乐于助人的机器人助手"
}
```

**响应示例**:
```json
{
  "status": "success",
  "mode": "main",
  "bot_profile": {
    "bot_name": "小智",
    "bot_personality": "热情、乐于助人的机器人助手"
  }
}
```

## 4. 聊天任务管理

### 4.1 POST /api/chat

提交新的聊天任务。

**请求体**:
```json
{
  "message": "帮我抓取 cube_001",
  "session_id": "optional-session-id"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户输入的消息 |
| session_id | string | 否 | 会话 ID，不提供时自动生成 |

**响应示例**:
```json
{
  "task_id": "abc123-def456-ghi789",
  "session_id": "session-uuid-1234",
  "status": "pending",
  "message": "任务已创建，可通过 /api/chat/{task_id}/events 订阅事件流"
}
```

**错误响应** (422):
```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 4.2 GET /api/chat/{task_id}

查询任务状态。

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务唯一标识符 |

**请求示例**:
```bash
curl http://localhost:8000/api/chat/abc123-def456-ghi789
```

**响应示例**:
```json
{
  "task_id": "abc123-def456-ghi789",
  "session_id": "session-uuid-1234",
  "status": "running",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:05Z",
  "result": null
}
```

**状态说明**:
- `pending`: 等待处理
- `running`: 正在处理
- `done`: 处理完成
- `error`: 处理失败

### 4.3 GET /api/chat/{task_id}/events

订阅任务的事件流（SSE）。

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务唯一标识符 |

**请求示例**:
```javascript
const eventSource = new EventSource('/api/chat/abc123-def456-ghi789/events');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('收到事件:', data);
};
```

**事件格式**:
```
event: <event_type>
data: {"type":"<event_type>","data":{...},"timestamp":"..."}
```

### 4.4 GET /api/sessions/{session_id}

获取会话的历史记忆。

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话唯一标识符 |

**请求示例**:
```bash
curl http://localhost:8000/api/sessions/session-uuid-1234
```

**响应示例**:
```json
{
  "session_id": "session-uuid-1234",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "messages": [
    {
      "role": "user",
      "content": "你好，我叫小明",
      "timestamp": "2024-01-15T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "你好小明！很高兴认识你，我是小智，有什么可以帮你的吗？",
      "timestamp": "2024-01-15T10:00:05Z"
    },
    {
      "role": "user",
      "content": "帮我抓取 cube_001",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

## 5. 事件类型详解

SSE 流支持以下事件类型：

### 5.1 ack 事件

任务确认事件，在任务创建后立即发送。

```json
{
  "type": "ack",
  "data": {
    "task_id": "abc123-def456-ghi789",
    "message": "任务已接收，开始处理"
  },
  "timestamp": "2024-01-15T10:30:01Z"
}
```

### 5.2 plan 事件

规划器生成的执行计划。

```json
{
  "type": "plan",
  "data": {
    "thought": "用户想要抓取 cube_001，我需要调用 pick_up 工具",
    "actions": [
      {
        "tool": "pick_up",
        "arguments": {
          "target_id": "cube_001"
        },
        "order": 1
      },
      {
        "tool": "send_message",
        "arguments": {
          "content": "正在为您抓取 cube_001..."
        },
        "order": 2
      }
    ]
  },
  "timestamp": "2024-01-15T10:30:02Z"
}
```

### 5.3 tool 事件

工具执行状态更新。

```json
{
  "type": "tool",
  "data": {
    "tool_name": "pick_up",
    "status": "running",
    "arguments": {
      "target_id": "cube_001"
    },
    "message": "正在连接相机..."
  },
  "timestamp": "2024-01-15T10:30:03Z"
}
```

工具执行完成时的更新：
```json
{
  "type": "tool",
  "data": {
    "tool_name": "pick_up",
    "status": "completed",
    "result": {
      "success": true,
      "message": "成功抓取 cube_001",
      "duration_ms": 2345
    }
  },
  "timestamp": "2024-01-15T10:30:05Z"
}
```

工具执行失败时的更新：
```json
{
  "type": "tool",
  "data": {
    "tool_name": "pick_up",
    "status": "failed",
    "error": "模型文件不存在: cube_001.ckpt"
  },
  "timestamp": "2024-01-15T10:30:04Z"
}
```

### 5.4 done 事件

任务完成事件。

```json
{
  "type": "done",
  "data": {
    "final_response": "已成功抓取 cube_001，请查收！",
    "tool_results": [
      {
        "tool": "pick_up",
        "success": true
      },
      {
        "tool": "send_message",
        "success": true
      }
    ]
  },
  "timestamp": "2024-01-15T10:30:06Z"
}
```

### 5.5 error 事件

任务执行错误事件。

```json
{
  "type": "error",
  "data": {
    "error_code": "TOOL_EXECUTION_FAILED",
    "message": "机械臂连接失败，请检查串口配置",
    "details": {
      "tool": "pick_up",
      "exception": "ConnectionTimeoutError"
    }
  },
  "timestamp": "2024-01-15T10:30:04Z"
}
```

## 6. 工具 API 接口

以下接口是智能体内部调用的工具接口，也可以通过 API 直接调用（主要用于调试）。

### 6.1 POST /api/tools/send_message

发送机器人回复消息。

**请求体**:
```json
{
  "content": "你好，我是小智！",
  "session_id": "session-uuid-1234"
}
```

**响应示例**:
```json
{
  "status": "success",
  "message_id": "msg-12345"
}
```

### 6.2 POST /api/tools/pick_up

执行抓取操作。

**请求体**:
```json
{
  "target_id": "cube_001",
  "arm": "left"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| target_id | string | 是 | 目标物体标识 |
| arm | string | 否 | 使用的机械臂，默认 left |

**响应示例**:
```json
{
  "status": "success",
  "target_id": "cube_001",
  "grasp_success": true,
  "confidence": 0.95,
  "duration_ms": 2345
}
```

### 6.3 POST /api/tools/extract_bot_profile

从用户输入中提取机器人名称和人格。

**请求体**:
```json
{
  "user_input": "给你起个名字叫小智，性格是热情开朗"
}
```

**响应示例**:
```json
{
  "bot_name": "小智",
  "bot_personality": "热情开朗",
  "confidence": 0.98
}
```

### 6.4 POST /api/tools/save_bot_profile

保存机器人身份信息。

**请求体**:
```json
{
  "bot_name": "小智",
  "bot_personality": "热情、乐于助人的机器人助手"
}
```

**响应示例**:
```json
{
  "status": "success",
  "message": "配置已保存到 configs/bot_config.toml"
}
```

## 7. 安全性

### 7.1 CORS 配置

默认允许来自 `http://localhost:8080` 的跨域请求。生产环境建议配置严格的 CORS 策略。

### 7.2 认证

当前版本未实现认证机制，生产环境部署时建议添加：

- API Key 认证
- JWT Token 认证
- IP 白名单

### 7.3 输入验证

所有 API 端点都使用 Pydantic 模型进行输入验证，防止注入攻击。

---

*本文档详细描述了 Actio Agent 后端 API 的所有端点、请求格式、响应格式和事件类型。API 可能在未来版本中更新，请关注版本变更说明。*