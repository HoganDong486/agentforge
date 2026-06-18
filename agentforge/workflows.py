"""Pre-built workflow templates for common agent patterns."""
from agentforge.engine.node import Node, NodeConfig, NodeType, Workflow, build_linear_workflow, build_fan_out_workflow
import uuid


def code_review_pipeline(code: str, language: str = "python") -> Workflow:
    """PM writes spec → Dev implements → Reviewer audits."""
    wf = build_linear_workflow(
        "Code Review Pipeline",
        [
            {"name": "PM Specification", "type": "agent", "role": "planner", "prompt": f"Write a technical specification for implementing:\n{code[:2000]}"},
            {"name": "Developer Implementation", "type": "agent", "role": "coder", "prompt": f"Implement based on the specification above. Code in {language}."},
            {"name": "Code Reviewer", "type": "agent", "role": "reviewer", "prompt": "Review the code against the specification. Report bugs, security issues, and suggestions."},
        ],
    )
    return wf


def research_synthesis_pipeline(topic: str) -> Workflow:
    """Research → Synthesize → Write."""
    wf = build_linear_workflow(
        f"Research: {topic[:50]}",
        [
            {"name": "Research Phase", "type": "agent", "role": "researcher", "prompt": f"Research the topic thoroughly: {topic}. Find key facts, competing perspectives, and recent developments."},
            {"name": "Synthesis Phase", "type": "agent", "role": "planner", "prompt": "Synthesize the research findings into a coherent structure with key themes and conclusions."},
            {"name": "Write Report", "type": "agent", "role": "writer", "prompt": "Write a comprehensive report based on the synthesis. Include citations where possible."},
        ],
    )
    return wf


def multi_expert_analysis(topic: str) -> Workflow:
    """Multiple experts analyze independently → Aggregate results."""
    wf = build_fan_out_workflow(
        f"Expert Analysis: {topic[:50]}",
        dispatcher={"name": "Task Dispatcher", "type": "agent", "role": "planner", "prompt": f"Break down this analysis task into 3 specialized sub-tasks: {topic}"},
        workers=[
            {"name": "Technical Expert", "type": "agent", "role": "coder", "prompt": f"Analyze from a technical/engineering perspective:\n{topic}"},
            {"name": "Business Expert", "type": "agent", "role": "data_analyst", "prompt": f"Analyze from a business/market perspective:\n{topic}"},
            {"name": "Ethics Expert", "type": "agent", "role": "default", "prompt": f"Analyze from an ethical/societal perspective:\n{topic}"},
        ],
        aggregator={"name": "Aggregator", "type": "agent", "role": "researcher", "prompt": "Synthesize the three expert analyses into a unified report. Highlight agreements and disagreements."},
    )
    return wf


def ci_cd_pipeline(repo_path: str) -> Workflow:
    """Lint → Test → Build → Deploy."""
    wf = build_linear_workflow(
        "CI/CD Pipeline",
        [
            {"name": "Lint Check", "type": "tool", "tool": "run_command", "prompt": f"cd {repo_path} && ruff check ."},
            {"name": "Unit Tests", "type": "tool", "tool": "run_command", "prompt": f"cd {repo_path} && pytest --tb=short"},
            {"name": "Build", "type": "tool", "tool": "run_command", "prompt": f"cd {repo_path} && pip install -e ."},
            {"name": "Deploy Check", "type": "agent", "role": "devops", "prompt": "Verify the build is ready for deployment. Check for any security issues or missing configurations."},
        ],
    )
    return wf


def data_analysis_pipeline(data_description: str) -> Workflow:
    """Analyze → Visualize → Report."""
    wf = build_linear_workflow(
        "Data Analysis Pipeline",
        [
            {"name": "Data Processing", "type": "agent", "role": "data_analyst", "prompt": f"Analyze the following data and identify patterns:\n{data_description[:3000]}"},
            {"name": "Visualization Plan", "type": "agent", "role": "coder", "prompt": "Propose Python code (matplotlib/seaborn) to visualize the key findings from the analysis."},
            {"name": "Final Report", "type": "agent", "role": "writer", "prompt": "Write an executive summary report combining the analysis and visualization recommendations."},
        ],
    )
    return wf


PRESETS = {
    "code_review": code_review_pipeline,
    "research": research_synthesis_pipeline,
    "multi_expert": multi_expert_analysis,
    "ci_cd": ci_cd_pipeline,
    "data_analysis": data_analysis_pipeline,
}


def list_presets() -> list[dict]:
    return [
        {"name": "code_review", "description": "PM → Dev → Reviewer pipeline for code quality"},
        {"name": "research", "description": "Research → Synthesize → Write for deep topic analysis"},
        {"name": "multi_expert", "description": "3 experts analyze independently → aggregate results"},
        {"name": "ci_cd", "description": "Lint → Test → Build → Deploy automation"},
        {"name": "data_analysis", "description": "Analyze → Visualize → Report for data insights"},
    ]


def create_workflow(preset_name: str, *args, **kwargs) -> Workflow:
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    return PRESETS[preset_name](*args, **kwargs)
