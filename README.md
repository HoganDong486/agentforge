# AgentForge

[![PyPI](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Lines](https://img.shields.io/badge/lines-2500%2B-informational)]()

**Production-grade multi-agent workflow platform.** Build, orchestrate, evaluate, and deploy AI agent pipelines.

[English](#english) | [中文](#中文)

---

## English

AgentForge is a comprehensive platform for building AI agent workflows. It combines DAG-based orchestration, MCP tool integration, persistent memory, context compression, and built-in agent-as-judge evaluation into a single system.

### Architecture

```
┌─────────────────────────────────────────────────┐
│                 AgentForge                       │
├─────────────────────────────────────────────────┤
│  CLI (agentforge)  │  API (FastAPI)  │  Dashboard│
├─────────────────────────────────────────────────┤
│  Engine           │  Agents         │  Tools     │
│  ├── DAG Scheduler│  ├── LLMAgent   │  ├── MCP   │
│  ├── Executor     │  ├── ToolAgent  │  ├── Builtins│
│  └── Workflows    │  └── Registry   │  └── Registry│
├─────────────────────────────────────────────────┤
│  Memory           │  Evaluation     │  Stream    │
│  ├── ChromaDB     │  ├── AgentJudge │  ├── WS    │
│  └── Compressor   │  └── Benchmark  │  └── Log   │
└─────────────────────────────────────────────────┘
```

### Features

| Category | Feature | Detail |
|----------|---------|--------|
| **Engine** | DAG Workflow | Build complex agent pipelines with parallel execution |
| | Auto-retry | Failed nodes retry with configurable backoff |
| | Streaming | Real-time workflow event streaming |
| **Agents** | 8 built-in roles | Coder, reviewer, planner, researcher, writer, DevOps, data analyst, general |
| | Custom agents | Extend with FunctionAgent or custom BaseAgent |
| | ToolAgent | Agents that execute external tools |
| **Tools** | MCP Protocol | Connect any MCP-compatible tool server |
| | Built-in tools | read_file, write_file, list_files, run_command, web_fetch |
| | Tool registry | Unified interface for all tools |
| **Memory** | Session memory | Persistent ChromaDB-backed memory across sessions |
| | Knowledge store | Store and retrieve domain knowledge |
| | Context compressor | Reduce token usage by 60-90% |
| **Evaluation** | Agent-as-Judge | 6-dimension automated evaluation |
| | Benchmarking | Run test suites and compare agent outputs |
| | Compare mode | Side-by-side output comparison |
| **Interface** | CLI | Full-featured command-line interface |
| | REST API | FastAPI with 15+ endpoints |
| | Dashboard | React web UI for visual workflow management |

### Quick Start

```bash
# Install
pip install -r requirements.txt

# Start the API server
python -m agentforge serve

# Open dashboard
cd dashboard && npm install && npm run dev
```

### CLI Usage

```bash
# List available agents
agentforge agent list

# Run an agent
agentforge agent info coder

# List tools
agentforge tool list

# Execute a tool
agentforge tool run read_file --args '{"path": "README.md"}'

# Evaluate an agent output
agentforge evaluate --task "Write a function" --output "def foo(): pass"

# Run a workflow from JSON
agentforge run workflow.json

# Start API server
agentforge serve

# Connect an MCP server
agentforge mcp add browser python browser_mcp.py
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/agents` | List registered agents |
| POST | `/agents/run` | Execute an agent |
| GET | `/tools` | List available tools |
| POST | `/tools/{name}` | Execute a tool |
| POST | `/mcp/add` | Register an MCP server |
| POST | `/workflows/run` | Execute a DAG workflow |
| POST | `/workflows/validate` | Validate workflow JSON |
| POST | `/evaluate` | Judge agent output quality |
| POST | `/evaluate/compare` | Compare two outputs |
| POST | `/memory/search` | Semantic memory search |
| POST | `/compress` | Compress conversation context |

### Workflow Example

```json
{
  "id": "review-pipeline",
  "name": "Code Review Pipeline",
  "nodes": [
    {"id": "spec", "name": "PM Spec", "type": "agent",
     "config": {"agent_role": "planner", "agent_prompt": "Write a spec for a REST API"}},
    {"id": "impl", "name": "Implement", "type": "agent",
     "config": {"agent_role": "coder", "agent_prompt": "Implement based on spec"}},
    {"id": "review", "name": "Review", "type": "agent",
     "config": {"agent_role": "reviewer", "agent_prompt": "Review the implementation"}}
  ],
  "edges": [{"from": "spec", "to": "impl"}, {"from": "impl", "to": "review"}]
}
```

### Built-in Workflow Presets

```python
from agentforge.workflows import create_workflow

# PM → Dev → Reviewer
wf = create_workflow("code_review", code="def foo():\n    pass")

# Research → Synthesize → Write
wf = create_workflow("research", topic="AI agent frameworks in 2026")

# 3 experts analyze independently → aggregate
wf = create_workflow("multi_expert", topic="Should we use microservices?")

# Lint → Test → Build → Deploy
wf = create_workflow("ci_cd", repo_path="./my-project")

# Analyze → Visualize → Report
wf = create_workflow("data_analysis", data_description="...")
```

---

## 中文

AgentForge 是一个生产级的多 Agent 工作流平台。它整合了 DAG 编排、MCP 工具集成、持久记忆、上下文压缩和 Agent-as-Judge 评估功能。

### 技术栈

- **后端**: Python · FastAPI · ChromaDB · OpenAI API
- **前端**: React · TypeScript · Tailwind CSS
- **协议**: MCP (Model Context Protocol) · JSON-RPC 2.0

### 内置 Agent 角色

| Agent | 描述 |
|-------|------|
| `default` | 通用助手 |
| `coder` | 软件工程师——写干净代码 |
| `reviewer` | 代码审查员——找 bug、安全问题 |
| `planner` | 任务规划员——拆解复杂任务 |
| `researcher` | 研究分析师——信息检索与综合 |
| `writer` | 内容作者——清晰专业的写作 |
| `devops` | DevOps 工程师——CI/CD、部署 |
| `data_analyst` | 数据分析师——数据分析与可视化 |

### 项目结构

```
agentforge/
├── agentforge/            (Python 包 ~ 1500+ 行)
│   ├── engine/            DAG 工作流引擎
│   ├── agents/            Agent 系统和注册表
│   ├── tools/             MCP 工具集成
│   ├── memory/            ChromaDB 记忆 + 上下文压缩
│   ├── evaluation/        Agent-as-Judge 评估
│   ├── cli/               CLI 命令行
│   ├── api/               FastAPI REST 服务
│   ├── stream.py          WebSocket 流式监控
│   └── workflows.py       5 种预置工作流模板
├── dashboard/             (React 前端 ~ 400 行)
└── README.md
```

## License

MIT © [Hogan Dong](https://github.com/HoganDong486)
