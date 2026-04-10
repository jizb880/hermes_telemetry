# Hermes Telemetry 使用与配置指南

## 概述

Hermes Telemetry 是一个面向 [Hermes Agent](https://github.com/nousresearch/hermes-agent) 的 OpenTelemetry 可观测性插件。它通过 Hermes 提供的 Hook 机制，在 Agent 生命周期的关键节点采集 Trace 和 Metrics 数据，帮助开发者理解 Agent 的运行行为、诊断性能瓶颈和排查问题。

## 安装

### 方式一：目录安装（推荐）

将项目复制或软链接到 Hermes 插件目录：

```bash
# 克隆项目
git clone https://github.com/jizb880/hermes_telemetry.git

# 复制到 Hermes 插件目录
cp -r hermes_telemetry ~/.hermes/plugins/hermes_telemetry

# 或使用软链接
ln -s $(pwd)/hermes_telemetry ~/.hermes/plugins/hermes_telemetry
```

### 方式二：pip 安装

```bash
pip install -e .
```

### 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

配置文件为 JSON 格式，加载优先级如下：

1. `HERMES_TELEMETRY_CONFIG` 环境变量指定的路径
2. 插件目录下的 `config/observability.json`
3. `~/.hermes/plugins/hermes_telemetry/config/observability.json`
4. 内置默认值（全部启用）

### 配置文件示例

```json
{
  "enabled": true,
  "service_name": "hermes-agent",
  "console_export_enabled": true,
  "ndjson_export_enabled": true,
  "ndjson_export_path": ".",
  "capture_session": true,
  "capture_llm": true,
  "capture_tool": true,
  "capture_llm_input": true,
  "capture_llm_output": true,
  "capture_tool_input": true,
  "capture_tool_output": true
}
```

### 配置字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `true` | 主开关，设为 `false` 则完全禁用插件 |
| `service_name` | string | `"hermes-agent"` | OpenTelemetry 服务名称标识 |
| `console_export_enabled` | bool | `true` | 是否将 Span 数据打印到控制台 |
| `ndjson_export_enabled` | bool | `true` | 是否将 Span 数据写入 NDJSON 文件 |
| `ndjson_export_path` | string | `"."` | NDJSON 文件输出路径（目录或 `.jsonl` 文件） |
| `capture_session` | bool | `true` | 是否采集 Session 生命周期数据 |
| `capture_llm` | bool | `true` | 是否采集 LLM 调用数据 |
| `capture_tool` | bool | `true` | 是否采集 Tool 调用数据 |
| `capture_llm_input` | bool | `true` | 是否记录用户输入消息 |
| `capture_llm_output` | bool | `true` | 是否记录助手响应内容 |
| `capture_tool_input` | bool | `true` | 是否记录工具调用参数 |
| `capture_tool_output` | bool | `true` | 是否记录工具返回结果 |

### 环境变量

| 变量 | 说明 |
|------|------|
| `HERMES_TELEMETRY_CONFIG` | 指定配置文件的绝对路径 |

## Hook 采集点

插件在以下 6 个 Hook 点进行数据采集：

### on_session_start

- **触发时机**：新 Session 初始化时
- **采集内容**：创建根 Span `hermes.session`，记录 session_id、model、platform
- **接收参数**：`session_id`, `model`, `platform`

### on_session_end

- **触发时机**：`run_conversation()` 调用结束时
- **采集内容**：结束根 Span，记录 duration、turn_count、completed、interrupted
- **接收参数**：`session_id`, `completed`, `interrupted`, `model`, `platform`

### pre_llm_call

- **触发时机**：每轮 LLM 调用开始前
- **采集内容**：创建子 Span `hermes.llm.call`，记录 model、用户消息（可选）
- **接收参数**：`session_id`, `user_message`, `conversation_history`, `is_first_turn`, `model`, `platform`

### post_llm_call

- **触发时机**：LLM 调用完成后
- **采集内容**：结束 LLM Span，记录助手响应（可选）、响应长度
- **接收参数**：`session_id`, `user_message`, `assistant_response`, `conversation_history`, `model`, `platform`

### pre_tool_call

- **触发时机**：工具执行前
- **采集内容**：创建子 Span `hermes.tool.<tool_name>`，记录工具名、参数（可选）
- **接收参数**：`tool_name`, `args`, `task_id`

### post_tool_call

- **触发时机**：工具执行后
- **采集内容**：结束工具 Span，记录 duration、result（可选）、错误状态
- **接收参数**：`tool_name`, `args`, `result`, `task_id`

## Span 层级结构

所有 Span 通过统一的 `trace_id` 关联：

```
hermes.session (root, SERVER)
├── hermes.llm.call (CLIENT)
│   ├── hermes.tool.web_search (INTERNAL)
│   ├── hermes.tool.read_file (INTERNAL)
│   └── hermes.tool.execute_code (INTERNAL)
└── hermes.llm.call (CLIENT)        # 第二轮对话
    └── hermes.tool.terminal (INTERNAL)
```

## Metrics 指标

### Counters（计数器）

| 指标名 | 标签 | 说明 |
|--------|------|------|
| `hermes.session.count` | `model`, `platform` | Session 启动次数 |
| `hermes.llm.call.count` | `model`, `is_first_turn` | LLM 调用次数 |
| `hermes.tool.call.count` | `tool_name` | 工具调用次数 |
| `hermes.tool.error.count` | `tool_name` | 工具错误次数 |

### Histograms（直方图）

| 指标名 | 标签 | 说明 |
|--------|------|------|
| `hermes.session.duration_ms` | `completed`, `interrupted` | Session 持续时间 |
| `hermes.llm.call.duration_ms` | `model` | LLM 调用耗时 |
| `hermes.tool.call.duration_ms` | `tool_name` | 工具调用耗时 |

## 数据输出

### 控制台输出

设置 `console_export_enabled: true` 后，每个 Span 完成时会以 OpenTelemetry 标准格式打印到控制台，同时关键事件会打印简洁的日志行：

```
[hermes_telemetry] Session started: abc123 (model=gpt-4, platform=cli)
[hermes_telemetry] LLM call started: session=abc123, turn=1
[hermes_telemetry] Tool call started: web_search (task=abc123)
[hermes_telemetry] Tool call ended: web_search (duration=1234ms, error=False)
[hermes_telemetry] LLM call ended: session=abc123, response_len=256
[hermes_telemetry] Session ended: abc123 (duration=5678ms, turns=1, completed=True, interrupted=False)
```

### NDJSON 文件

设置 `ndjson_export_enabled: true` 后，Span 数据会以 NDJSON（每行一个 JSON）格式写入文件，便于离线分析：

```bash
# 默认输出到当前目录的 hermes-otel-spans.jsonl
cat hermes-otel-spans.jsonl | jq .

# 查看某个 trace 的所有 span
cat hermes-otel-spans.jsonl | jq 'select(.trace_id == "xxx")'

# 统计工具调用次数
cat hermes-otel-spans.jsonl | jq 'select(.name | startswith("hermes.tool."))' | jq -s 'group_by(.attributes["hermes.tool.name"]) | map({tool: .[0].attributes["hermes.tool.name"], count: length})'
```

NDJSON 文件中每行包含：

```json
{
  "name": "hermes.tool.web_search",
  "kind": "INTERNAL",
  "trace_id": "0af7651916cd43dd8448eb211c80319c",
  "span_id": "b7ad6b7169203331",
  "parent_span_id": "00f067aa0ba902b7",
  "start_time_unix_nano": 1712345678000000000,
  "end_time_unix_nano": 1712345679234000000,
  "attributes": {
    "hermes.tool.name": "web_search",
    "hermes.tool.input": "{\"query\": \"OpenTelemetry Python\"}",
    "hermes.tool.duration_ms": 1234.5
  },
  "status": {"status_code": "OK", "description": null},
  "events": [],
  "resource": {"attributes": {"service.name": "hermes-agent"}},
  "instrumentation_scope": {"name": "hermes_telemetry"}
}
```

## 隐私与安全

- 通过 `capture_llm_input`/`capture_llm_output` 控制是否记录对话内容
- 通过 `capture_tool_input`/`capture_tool_output` 控制是否记录工具参数和结果
- 所有属性值自动截断至 8000 字符，防止内存溢出
- 插件中所有 Hook 都包裹在 try/except 中，不会影响 Agent 正常运行

## 故障排除

### 插件未加载

确认插件目录结构正确：
```
~/.hermes/plugins/hermes_telemetry/
├── plugin.yaml
├── __init__.py
├── config/
│   └── observability.json
└── hermes_otel/
    └── ...
```

### 没有控制台输出

检查配置文件中 `enabled` 和 `console_export_enabled` 是否为 `true`。

### NDJSON 文件未生成

检查 `ndjson_export_path` 指向的目录是否存在且有写入权限。
