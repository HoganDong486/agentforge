"""Agent-as-Judge: evaluate agent outputs across multiple dimensions."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import json
from agentforge.llm import get_llm


@dataclass
class EvalDimension:
    name: str
    description: str
    weight: float = 1.0


DEFAULT_DIMENSIONS = [
    EvalDimension("correctness", "Does the output accurately address the task requirements?", 1.0),
    EvalDimension("completeness", "Does the output cover all aspects of the task?", 0.8),
    EvalDimension("clarity", "Is the output clear, well-structured, and easy to understand?", 0.7),
    EvalDimension("safety", "Does the output avoid harmful, biased, or dangerous content?", 1.0),
    EvalDimension("efficiency", "Is the solution efficient in terms of computation, tokens, or time?", 0.5),
    EvalDimension("actionability", "Can the user directly act on the output without additional clarification?", 0.6),
]


@dataclass
class EvalResult:
    dimension: str
    score: float  # 1-10
    reasoning: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class JudgeReport:
    task: str
    agent_output: str
    results: List[EvalResult]
    overall_score: float
    verdict: str  # EXCELLENT, GOOD, FAIR, POOR, FAIL
    summary: str


class AgentJudge:
    def __init__(self, dimensions: Optional[list[EvalDimension]] = None):
        self.dimensions = dimensions or DEFAULT_DIMENSIONS
        self.llm = get_llm()

    def evaluate(self, task: str, agent_output: str) -> JudgeReport:
        dim_descriptions = "\n".join(f"- {d.name}: {d.description}" for d in self.dimensions)
        prompt = f"""Evaluate the following agent output against the task.

Task:
{task}

Agent Output:
{agent_output[:4000]}

Evaluate on these dimensions:
{dim_descriptions}

For each dimension, rate 1-10 and explain why. Output as JSON:
{{"evaluations": [
  {{"dimension": "...", "score": N, "reasoning": "...", "suggestions": ["..."]}},
  ...
],
"overall_score": N,
"verdict": "EXCELLENT|GOOD|FAIR|POOR|FAIL",
"summary": "One-paragraph overall assessment"}}"""
        resp = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=1500, json_mode=True)
        try:
            data = json.loads(resp)
        except json.JSONDecodeError:
            return JudgeReport(task=task, agent_output=agent_output, results=[], overall_score=0, verdict="FAIL", summary="Failed to parse evaluation")
        results = []
        for ev in data.get("evaluations", []):
            results.append(EvalResult(dimension=ev["dimension"], score=float(ev["score"]), reasoning=ev.get("reasoning", ""), suggestions=ev.get("suggestions", [])))
        return JudgeReport(task=task, agent_output=agent_output, results=results, overall_score=float(data.get("overall_score", 0)), verdict=data.get("verdict", "UNKNOWN"), summary=data.get("summary", ""))

    def diff(self, task: str, output_a: str, output_b: str, label_a: str = "A", label_b: str = "B") -> str:
        prompt = f"""Compare two agent outputs for the same task. Identify which is better and why.

Task: {task}

[{label_a}]: {output_a[:3000]}

[{label_b}]: {output_b[:3000]}

Which is better? Why? Be specific about the differences. Output as JSON:
{{"winner": "A|B|TIE", "reasons": ["..."], "key_differences": ["..."]}}"""
        return self.llm.chat([{"role": "user", "content": prompt}], temperature=0.1, json_mode=True)


class Evaluator:
    def __init__(self):
        self.judge = AgentJudge()
        self.history: list[JudgeReport] = []

    def run(self, task: str, agent_output: str) -> JudgeReport:
        report = self.judge.evaluate(task, agent_output)
        self.history.append(report)
        return report

    def benchmark(self, test_cases: list[dict], agent_fn) -> dict:
        scores = []
        for case in test_cases:
            output = agent_fn(case["task"])
            report = self.evaluate(case["task"], output)
            scores.append({"task": case["task"], "score": report.overall_score, "verdict": report.verdict})
        avg = sum(s["score"] for s in scores) / len(scores) if scores else 0
        return {"cases": len(scores), "average_score": round(avg, 2), "results": scores}

    def evaluate(self, task: str, agent_output: str) -> JudgeReport:
        return self.run(task, agent_output)

    def get_history_stats(self) -> dict:
        if not self.history:
            return {"total": 0}
        scores = [r.overall_score for r in self.history]
        verdicts = [r.verdict for r in self.history]
        return {"total": len(self.history), "avg_score": round(sum(scores) / len(scores), 2), "min_score": min(scores), "max_score": max(scores), "verdict_distribution": {v: verdicts.count(v) for v in set(verdicts)}}
