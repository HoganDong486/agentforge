"""Pipeline runner: end-to-end agent workflow execution with memory and evaluation."""
from __future__ import annotations
from typing import Any, Optional
from agentforge.engine.node import Workflow
from agentforge.engine.executor import WorkflowExecutor
from agentforge.evaluation.judge import Evaluator
from agentforge.memory.store import MemoryStore
from agentforge.memory.compressor import ContextCompressor
from agentforge.stream import WorkflowStream


class Pipeline:
    def __init__(self, workflow_id: Optional[str] = None):
        self.workflow_id = workflow_id or "pipeline"
        self.executor = WorkflowExecutor()
        self.evaluator = Evaluator()
        self.memory = MemoryStore()
        self.compressor = ContextCompressor()
        self.stream = WorkflowStream()
        self.history: list[dict] = []

    def run(self, workflow: Workflow, inputs: Optional[dict] = None, evaluate: bool = False) -> dict:
        self.stream.workflow_started(workflow.id, workflow.name)
        result = self.executor.execute(workflow, inputs)
        run_record = {
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "inputs": str(inputs)[:500],
            "result": str(result)[:2000],
            "nodes": {n.id: n.status.value for n in workflow.nodes},
        }
        self.history.append(run_record)
        self.stream.workflow_completed(workflow.id, result)

        if evaluate:
            report = self.evaluator.evaluate(str(inputs)[:500], str(result)[:2000])
            run_record["evaluation"] = {"score": report.overall_score, "verdict": report.verdict}

        self.memory.save_session(workflow.id, run_record)
        return result

    def recall_context(self, query: str, n_results: int = 3) -> str:
        memories = self.memory.recall(query, n_results)
        if not memories:
            return ""
        return "\n\n".join(f"[Memory {i+1} score={m['score']:.2f}]: {m['content'][:500]}" for i, m in enumerate(memories))

    def get_run_history(self) -> list[dict]:
        return self.history

    def compress_history(self, query: str) -> list[dict]:
        msgs = []
        for h in self.history[-5:]:
            msgs.append({"role": "assistant", "content": f"Workflow '{h['workflow_name']}': {str(h.get('result', ''))[:300]}"})
        return self.compressor.compress(msgs, query)


class BatchRunner:
    def __init__(self, max_parallel: int = 3):
        self.pipelines: dict[str, Pipeline] = {}
        self.max_parallel = max_parallel

    def add(self, name: str, pipeline: Pipeline):
        self.pipelines[name] = pipeline

    def run_all(self, workflow: Workflow, inputs_list: list[dict]) -> dict[str, dict]:
        import asyncio
        async def _run_all():
            sem = asyncio.Semaphore(self.max_parallel)
            async def _run_one(name, inputs):
                async with sem:
                    pipeline = self.pipelines[name]
                    return pipeline.run(workflow, inputs)
            tasks = []
            for i, inputs in enumerate(inputs_list):
                name = f"batch_{i}"
                if name not in self.pipelines:
                    self.add(name, Pipeline(f"{workflow.id}_{i}"))
                tasks.append(_run_one(name, inputs))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return {f"batch_{i}": r for i, r in enumerate(results)}
        return asyncio.run(_run_all())

    def get_stats(self) -> dict:
        return {
            "pipelines": len(self.pipelines),
            "total_runs": sum(len(p.history) for p in self.pipelines.values()),
        }
