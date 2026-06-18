# AgentForge

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Lines](https://img.shields.io/badge/lines-2500%2B-informational)]()
[![Tests](https://img.shields.io/badge/tests-20%2F20%20passing-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![React](https://img.shields.io/badge/Dashboard-React%2BTS-61DAFB?logo=react)]()

**Production-grade multi-agent workflow platform.** DAG orchestration · MCP tools · persistent memory · agent-as-judge evaluation · visual dashboard.

[English](#english) | [中文](#中文)

---

## English

### What is AgentForge?

AgentForge turns a single AI agent into an **automated multi-agent team**. Instead of asking one agent to do everything, you define a pipeline:

```
Researcher Agent → Planner Agent → Coder Agent → Reviewer Agent
```

Each agent has a specialized role. They pass outputs to each other, run in parallel where possible, and the system retries failures, logs everything, and scores the final output.

### Ecosystem

AgentForge is the **central orchestrator** in the Hogan Dong Agent Stack. Each project below plugs in as a component:

```
                       ┌─────────────────────────────────┐
                       │          AgentForge              │
                       │    (Orchestrator & Evaluator)    │
                       └──────────┬──────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐   ┌───────────────────┐   ┌──────────────────┐
│ opencode-browser│   │ mcp-server-toolkit│   │ rag-research     │
│     -mcp        │   │                   │   │     -agent       │
│                 │   │  File/Git/DB      │   │                  │
│ Browser vision  │   │  tools for agents │   │ Paper retrieval  │
│ for AI agents   │   │                   │   │ & Q&A            │
└─────────────────┘   └───────────────────┘   └──────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                                  ▼
                       ┌──────────────────┐
                       │ multi-agent      │
                       │   -playground    │
                       │                  │
                       │ Interactive demo │
                       │ & learning tool  │
                       └──────────────────┘
```

| Project | Role in Stack | Repository |
|----------|-------------|------------|
| **AgentForge** | Central brain: orchestrates agents, evaluates output, manages memory | [this repo](.) |
| `opencode-browser-mcp` | Eyes & hands: browser control for agents (30 tools) | [repo](https://github.com/HoganDong486/opencode-browser-mcp) |
| `mcp-server-toolkit` | Tool belt: filesystem, Git, database access (12 tools) | [repo](https://github.com/HoganDong486/mcp-server-toolkit) |
| `rag-research-agent` | Knowledge: paper indexing, vector search, autonomous Q&A | [repo](https://github.com/HoganDong486/rag-research-agent) |
| `multi-agent-playground` | Demo: interactive PM→Dev→Reviewer simulation | [repo](https://github.com/HoganDong486/multi-agent-playground) |
| `SkVM Explorer` | Research: language VM for agent skill optimization | [repo](https://github.com/HoganDong486/SkVM) |

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AgentForge v1.0                        │
├─────────────────────────────────────────────────────────┤
│  CLI (agentforge)    │  REST API (FastAPI)  │  Dashboard │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─ Engine ────────────┐  ┌─ Agents ────────────────┐   │
│  │  • DAG Scheduler    │  │  • LLMAgent             │   │
│  │  • Workflow Executor│  │  • ToolAgent            │   │
│  │  • Node (6 types)   │  │  • ReActAgent           │   │
│  │  • Batch Runner     │  │  • ChainOfThoughtAgent   │   │
│  └─────────────────────┘  │  • 8 built-in roles      │   │
│                            └─────────────────────────┘   │
│  ┌─ Tools ─────────────┐  ┌─ Memory ────────────────┐   │
│  │  • MCP Client       │  │  • ChromaDB Store       │   │
│  │  • Tool Registry    │  │  • Context Compressor   │   │
│  │  • 5 built-in tools │  │  • Session Persistence  │   │
│  └─────────────────────┘  └─────────────────────────┘   │
│                                                         │
│  ┌─ Evaluation ────────┐  ┌─ Infrastructure ───────┐   │
│  │  • Agent-as-Judge   │  │  • Rate Limiter        │   │
│  │  • 6-dim scoring    │  │  • Request Queue       │   │
│  │  • Benchmark runner │  │  • Model Router        │   │
│  │  • Compare mode     │  │  • Metrics Collector   │   │
│  └─────────────────────┘  │  • WebSocket Stream    │   │
│                            └────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Features

**Workflow Engine**
- DAG-based agent orchestration with parallel execution
- 6 node types: Agent, Tool, Condition, Human, Parallel, Subgraph
- Automatic retry with exponential backoff
- Real-time WebSocket event streaming
- Batch execution of workflows with different inputs

**Agent System**
- 8 built-in specialized roles: Coder, Reviewer, Planner, Researcher, Writer, DevOps, Data Analyst, General
- ReAct agent: interleaves reasoning steps with tool actions
- Chain-of-Thought agent: explicit step-by-step reasoning before answering
- Extensible: add custom agents via FunctionAgent or BaseAgent subclass

**Tool Integration**
- MCP (Model Context Protocol) client: connect any MCP-compatible server
- 5 built-in tools: read_file, write_file, list_files, run_command, web_fetch
- Unified ToolRegistry: same interface for built-in and MCP tools

**Memory System**
- Persistent ChromaDB-backed vector memory across sessions
- Knowledge store for domain-specific information
- Context compressor: reduce token consumption by 60-90%
- Semantic search over past sessions

**Evaluation**
- Agent-as-Judge: automated 6-dimension scoring (correctness, completeness, clarity, safety, efficiency, actionability)
- Benchmark runner: evaluate agents against test suites
- Side-by-side output comparison
- Verdict system: EXCELLENT / GOOD / FAIR / POOR / FAIL

### Quick Start

```bash
# 1. Clone and install
git clone https://github.com/HoganDong486/agentforge.git
cd agentforge
pip install -r requirements.txt

# 2. Set your API key
export OPENAI_API_KEY=sk-your-key-here
# Or use any OpenAI-compatible endpoint:
export OPENAI_BASE_URL=https://api.openai.com/v1

# 3. Try CLI
python -m agentforge agent list

# 4. Run the API server
python -m agentforge serve

# 5. Open dashboard
cd dashboard && npm install && npm run dev
# Visit http://localhost:5173
```

### CLI Reference

```
agentforge agent list              List all registered agents
agentforge agent info <name>       Show agent details
agentforge tool list               List available tools
agentforge tool run <name> --args  Execute a tool
agentforge mcp list                List connected MCP servers
agentforge mcp add <name> <cmd>    Connect an MCP server
agentforge evaluate --task --output Judge agent output
agentforge evaluate --compare A B  Compare two outputs
agentforge memory stats            Memory store statistics
agentforge memory search <query>   Semantic memory search
agentforge run <workflow.json>     Execute a workflow
agentforge benchmark <file>        Run evaluation benchmark
agentforge serve                   Start API server
agentforge version                 Show version
```

### API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/agents` | List all agents |
| `POST` | `/agents/run` | Execute an agent |
| `GET` | `/tools` | List all tools |
| `POST` | `/tools/{name}` | Execute a tool |
| `POST` | `/mcp/add` | Register an MCP server |
| `GET` | `/mcp` | List MCP servers |
| `POST` | `/workflows/run` | Execute a workflow |
| `POST` | `/workflows/validate` | Validate workflow JSON |
| `POST` | `/evaluate` | Evaluate agent output |
| `POST` | `/evaluate/compare` | Compare two outputs |
| `POST` | `/memory/search` | Semantic memory search |
| `GET` | `/memory/stats` | Memory store statistics |
| `POST` | `/memory/knowledge` | Add knowledge entry |
| `POST` | `/compress` | Compress conversation context |

### Workflow JSON Format

```json
{
  "id": "review-pipeline",
  "name": "Code Review Pipeline",
  "description": "PM writes spec → Dev implements → Reviewer audits",
  "nodes": [
    {
      "id": "spec",
      "name": "PM Specification",
      "type": "agent",
      "config": {
        "agent_role": "planner",
        "agent_prompt": "Write a technical specification for a REST API"
      }
    },
    {
      "id": "impl",
      "name": "Developer Implementation",
      "type": "agent",
      "config": {
        "agent_role": "coder",
        "agent_prompt": "Implement the specification above"
      }
    },
    {
      "id": "review",
      "name": "Code Review",
      "type": "agent",
      "config": {
        "agent_role": "reviewer",
        "agent_prompt": "Review against the spec. Find bugs and security issues."
      }
    }
  ],
  "edges": [
    {"from": "spec", "to": "impl"},
    {"from": "impl", "to": "review"}
  ]
}
```

### Built-in Workflow Presets

```python
from agentforge.workflows import create_workflow

# PM → Dev → Reviewer (3 agents in sequence)
wf = create_workflow("code_review", code="def foo():\n    pass")

# Research → Synthesize → Write (deep topic analysis)
wf = create_workflow("research", topic="AI agent frameworks 2026")

# 3 experts analyze independently → aggregate results (fan-out/fan-in)
wf = create_workflow("multi_expert", topic="Microservices vs monolith")

# Lint → Test → Build → Deploy (CI/CD automation)
wf = create_workflow("ci_cd", repo_path="./my-project")

# Analyze → Visualize → Report (data pipeline)
wf = create_workflow("data_analysis", data_description="...")
```

### Security

- API keys are read from environment variables only (never stored in code)
- Built-in tools (`run_command`, `write_file`) are intentionally limited
- MCP tools operate within the sandbox provided by the respective server
- Memory data stored locally in ChromaDB (no cloud upload)
- Rate limiter prevents runaway API costs

### Dependencies

| Package | Purpose | Required |
|---------|---------|:--------:|
| `openai` | LLM API calls | Yes |
| `chromadb` | Vector memory store | For memory |
| `fastapi` | REST API server | For API |
| `uvicorn` | ASGI server | For API |
| `pytest` | Test runner | For tests |

---

## 中文

### AgentForge 是什么

AgentForge 将单个 AI Agent 组装成**自动化的多 Agent 团队**。你不再需要依次向 Agent 提问，而是预先定义一条流水线：

```
研究员 Agent → 规划员 Agent → 程序员 Agent → 审查员 Agent
```

每个 Agent 承担一个专门角色。它们自动传递彼此的产出，在可能的情况下并行执行，系统负责失败重试、全程日志记录、以及对最终产出质量进行自动评分。

### 项目生态

AgentForge 是 Hogan Dong Agent 技术栈中的**中央调度大脑**：

```
                       ┌─────────────────────────────────┐
                       │          AgentForge              │
                       │      (编排调度 + 评估 + 记忆)     │
                       └──────────┬──────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐   ┌───────────────────┐   ┌──────────────────┐
│ opencode-browser│   │ mcp-server-toolkit│   │ rag-research     │
│     -mcp        │   │                   │   │     -agent       │
│                 │   │ 文件/Git/数据库    │   │                  │
│ 给Agent装上     │   │ 工具, 让Agent     │   │ 论文智能检索     │
│ 浏览器的眼睛    │   │ 能操纵开发环境    │   │ 与问答           │
└─────────────────┘   └───────────────────┘   └──────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                                  ▼
                       ┌──────────────────┐
                       │ multi-agent      │
                       │   -playground    │
                       │                  │
                       │ 交互式多Agent    │
                       │ 教学演示平台     │
                       └──────────────────┘
```

### 技术栈

- **后端**: Python 3.10+ · FastAPI · ChromaDB · OpenAI API
- **前端**: React 18 · TypeScript · Tailwind CSS
- **协议**: MCP (Model Context Protocol) · JSON-RPC 2.0
- **测试**: pytest, 20 个单元测试

### 项目结构

```
agentforge/
├── agentforge/                (Python 包, 1500+ 行)
│   ├── engine/                DAG 工作流引擎 (节点/调度/执行)
│   ├── agents/                Agent 系统 (LLM/工具/ReAct/CoT/注册表)
│   ├── tools/                 MCP 协议客户端 + 5 内建工具
│   ├── memory/                ChromaDB 记忆 + 智能上下文压缩
│   ├── evaluation/            Agent-as-Judge 6 维度自动评估
│   ├── cli/                   命令行接口 (12+ 子命令)
│   ├── api/                   FastAPI REST 服务 (18+ 端点)
│   ├── pipeline.py            端到端流水线 + 批量运行器
│   ├── workflows.py           5 种预置工作流模板
│   ├── stream.py              WebSocket 流式事件推送
│   ├── router.py              模型路由 (自动选最便宜的可用模型)
│   ├── metrics.py             指标收集与监控
│   └── queue.py               速率限制 + 并发请求队列
├── dashboard/                 (React 前端, 400+ 行)
│   └── src/
│       ├── App.tsx            7 页仪表盘 (Agent/工具/工作流/评估/记忆/预设/设置)
│       └── index.css          自定义样式
├── tests/                     单元测试 (20 用例)
├── README.md                  本文件
└── requirements.txt           依赖清单
```

### 内置 Agent 角色

| Agent | 描述 | 典型任务 |
|-------|------|---------|
| `default` | 通用智能助手 | 回答问题、提供建议 |
| `coder` | 资深软件工程师 | 编写干净、生产级代码 |
| `reviewer` | 高级代码审查员 | 找 bug、安全漏洞、架构问题 |
| `planner` | 技术项目经理 | 拆解复杂任务，制定执行计划 |
| `researcher` | 研究分析师 | 信息检索、多方综合、平衡结论 |
| `writer` | 专业内容作者 | 清晰、有吸引力的写作 |
| `devops` | DevOps 工程师 | CI/CD 配置、Docker、部署方案 |
| `data_analyst` | 数据分析师 | 数据处理、模式识别、可视化方案 |

### Python SDK 示例

```python
from agentforge.engine.node import Workflow
from agentforge.engine.executor import WorkflowExecutor
from agentforge.workflows import create_workflow
from agentforge.pipeline import Pipeline
from agentforge.evaluation.judge import Evaluator

# 方式 1: 用预设模板
wf = create_workflow("code_review", code="def add(a,b): return a+b")
executor = WorkflowExecutor()
result = executor.execute(wf, {"task": "Review this code"})
print(f"Result: {result}")

# 方式 2: 完整流水线（含记忆 + 评估）
pipeline = Pipeline()
result = pipeline.run(wf, {"task": "Review"}, evaluate=True)
print(f"Score: {pipeline.history[-1].get('evaluation', {}).get('score')}")

# 方式 3: 单独评估
evaluator = Evaluator()
report = evaluator.evaluate("Write a factorial function",
                            "def fact(n): return 1 if n<=1 else n*fact(n-1)")
print(f"Verdict: {report.verdict}, Score: {report.overall_score}/60")
```

### Roadmap

- [ ] WebSocket streaming for live dashboard updates
- [ ] LangChain / LangGraph adapter
- [ ] Human-in-the-loop approval nodes
- [ ] Workflow marketplace (share and discover community workflows)
- [ ] Cost tracking and budget management per workflow
- [ ] Docker deployment with one-command setup
- [ ] Multi-provider failover (auto-switch if primary LLM is down)

---

## License

MIT © [Hogan Dong](https://github.com/HoganDong486)

---

<p align="center">
  <a href="https://github.com/HoganDong486/opencode-browser-mcp">Browser MCP</a> ·
  <a href="https://github.com/HoganDong486/mcp-server-toolkit">MCP Toolkit</a> ·
  <a href="https://github.com/HoganDong486/rag-research-agent">RAG Agent</a> ·
  <a href="https://github.com/HoganDong486/multi-agent-playground">Agent Playground</a>
</p>
