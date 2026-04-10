# Hermes Telemetry

OpenTelemetry 可观测性插件，为 [Hermes Agent](https://github.com/nousresearch/hermes-agent) 提供全链路 Trace 追踪和 Metrics 指标采集能力。

## 特性

- **6 个 Hook 采集点**：覆盖 Session、LLM、Tool 三层生命周期（on_session_start/end, pre/post_llm_call, pre/post_tool_call）
- **统一 Trace 关联**：同一 Session 内所有 Span 共享 trace_id，支持完整链路追踪
- **双通道输出**：控制台实时打印 + NDJSON 文件持久化，无需外部依赖
- **OpenTelemetry 标准**：Trace 和 Metrics 遵循 OpenTelemetry 语义规范
- **细粒度控制**：可独立开关每个 Hook 点，可选择性捕获输入/输出内容
- **线程安全**：支持并发工具调用场景，LIFO 栈管理嵌套工具 Span
- **零侵入**：所有 Hook 错误隔离，不影响 Agent 正常运行

## Span 层级

```
hermes.session (root)
└── hermes.llm.call
    ├── hermes.tool.web_search
    ├── hermes.tool.read_file
    └── hermes.tool.execute_code
```

## 快速开始

### 1. 安装依赖

```bash
pip install opentelemetry-api opentelemetry-sdk
```

### 2. 部署插件

```bash
cp -r hermes_telemetry ~/.hermes/plugins/hermes_telemetry
```

### 3. 配置（可选）

编辑 `~/.hermes/plugins/hermes_telemetry/config/observability.json`：

```json
{
  "enabled": true,
  "service_name": "hermes-agent",
  "console_export_enabled": true,
  "ndjson_export_enabled": true,
  "ndjson_export_path": "."
}
```

### 4. 运行

正常启动 Hermes Agent，插件会自动加载并开始采集数据：

```bash
hermes
```

控制台将输出类似：

```
[hermes_telemetry] Initialized (service=hermes-agent)
[hermes_telemetry] Console export: enabled
[hermes_telemetry] NDJSON export: ./hermes-otel-spans.jsonl
[hermes_telemetry] Hooks registered: session, llm, tool
[hermes_telemetry] Plugin registered successfully.
```

### 5. 查看数据

```bash
# 查看 NDJSON 文件
cat hermes-otel-spans.jsonl | jq .

# 按 trace_id 过滤
cat hermes-otel-spans.jsonl | jq 'select(.trace_id == "YOUR_TRACE_ID")'
```

## 项目结构

```
hermes_telemetry/
├── plugin.yaml                      # Hermes 插件清单
├── __init__.py                      # 插件入口 register(ctx)
├── config/
│   └── observability.json           # 默认配置
├── hermes_otel/
│   ├── config.py                    # 配置加载与解析
│   ├── tracer.py                    # GlobalTracer 单例
│   ├── state.py                     # Session 状态管理
│   ├── attributes.py                # 属性截断工具
│   ├── metrics.py                   # Metrics 定义
│   ├── exporters/
│   │   └── jsonl_file_exporter.py   # NDJSON 文件导出器
│   └── hooks/
│       ├── __init__.py              # Hook 注册编排
│       ├── session.py               # Session 生命周期 Hook
│       ├── llm.py                   # LLM 调用 Hook
│       └── tool.py                  # Tool 调用 Hook
├── docs/
│   └── USAGE.md                     # 详细使用文档
├── pyproject.toml                   # Python 打包配置
└── requirements.txt                 # 依赖清单
```

## 详细文档

完整的使用和配置指南请参见 [docs/USAGE.md](docs/USAGE.md)。

## 参考项目

- [openclaw_telemetry](https://github.com/jizb880/openclaw_telemetry) - OpenClaw Agent 的 OpenTelemetry 插件（TypeScript 实现）
- [Hermes Agent](https://github.com/nousresearch/hermes-agent) - Nous Research 的自进化 AI Agent
- [Hermes Agent Hooks 文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks)

## License

MIT
