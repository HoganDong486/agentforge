"""Extended AgentForge test suite — executor, pipeline, workflows, stream, judge."""
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure agentforge is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentforge.engine.node import (
    Node, NodeConfig, NodeType, NodeStatus, Workflow, build_linear_workflow,
)
from agentforge.engine.executor import WorkflowExecutor
try:
    from agentforge.pipeline import Pipeline, BatchRunner
    HAS_PIPELINE = True
except ImportError:
    HAS_PIPELINE = False
from agentforge.workflows import (
    list_presets, create_workflow,
    code_review_pipeline, research_synthesis_pipeline,
    multi_expert_analysis, ci_cd_pipeline, data_analysis_pipeline,
)
from agentforge.stream import WorkflowStream
from agentforge.evaluation.judge import (
    AgentJudge, Evaluator, JudgeReport, EvalResult, EvalDimension, DEFAULT_DIMENSIONS,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_simple_linear_workflow(node_type=NodeType.AGENT, agent_role="default"):
    """Return a single-node linear Workflow suitable for execution tests."""
    wf = build_linear_workflow(
        "test-wf",
        [{"name": "step1", "type": node_type.value, "role": agent_role,
          "prompt": "Say hello"}],
    )
    return wf


def _mock_agent_run(return_value="mock-output"):
    """Create an async mock agent whose .run() returns *return_value*."""
    agent = MagicMock()
    agent.run = AsyncMock(return_value=return_value)
    return agent


# ---------------------------------------------------------------------------
# 1.  WorkflowExecutor.execute()
# ---------------------------------------------------------------------------

class TestWorkflowExecutor(unittest.TestCase):
    """Tests for WorkflowExecutor.execute() and internal helpers."""

    def setUp(self):
        self.executor = WorkflowExecutor()

    # -- execute() dispatch ------------------------------------------------

    def test_execute_agent_node_returns_output_in_variables(self):
        """AGENT node: agent.run() output lands in workflow.variables."""
        agent = _mock_agent_run("hello-world")
        self.executor.agents._agents = {"default": agent}

        wf = _make_simple_linear_workflow()
        result = self.executor.execute(wf)

        agent.run.assert_awaited_once()
        self.assertIn("node_0", result)
        self.assertEqual(result["node_0"], "hello-world")

    def test_execute_agent_not_found_raises(self):
        """Missing agent → node marked FAILED with error message."""
        self.executor.agents._agents = {}  # empty registry
        wf = Workflow(id="w1", name="test", description="")
        n = Node(id="n0", name="step", node_type=NodeType.AGENT,
                 config=NodeConfig(agent_role="ghost"))
        wf.add_node(n)

        result = self.executor.execute(wf)
        self.assertEqual(n.status, NodeStatus.FAILED)
        self.assertIn("ghost", n.error or "")

    def test_execute_tool_node_populates_output(self):
        """TOOL node runs actual tool from tool registry."""
        wf = Workflow(id="tool", name="tool", description="")
        n = Node(id="n0", name="run", node_type=NodeType.TOOL,
                 config=NodeConfig(tool_name="list_files", tool_args={"path": "."}))
        wf.add_node(n)
        result = self.executor.execute(wf)
        out = result["n0"]
        self.assertIsInstance(out, (list, dict), f"Expected list or dict, got {type(out)}: {out}")

    def test_execute_condition_node_true_expression(self):
        """CONDITION node with truthy expression returns True."""
        wf = Workflow(id="cond", name="cond", description="")
        n = Node(id="n0", name="check", node_type=NodeType.CONDITION,
                 config=NodeConfig(condition_expr="score > 5"))
        wf.add_node(n)

        result = self.executor.execute(wf, {"score": 10})
        self.assertTrue(result["n0"])

    def test_execute_condition_node_false_expression(self):
        """CONDITION node with falsy expression returns False."""
        wf = Workflow(id="cond", name="cond", description="")
        n = Node(id="n0", name="check", node_type=NodeType.CONDITION,
                 config=NodeConfig(condition_expr="score > 5"))
        wf.add_node(n)

        result = self.executor.execute(wf, {"score": 2})
        self.assertFalse(result["n0"])

    def test_execute_condition_node_empty_expression_defaults_true(self):
        """CONDITION node with no expression returns True."""
        wf = Workflow(id="cond", name="cond", description="")
        n = Node(id="n0", name="check", node_type=NodeType.CONDITION)
        wf.add_node(n)

        result = self.executor.execute(wf)
        self.assertTrue(result["n0"])

    def test_execute_parallel_node_no_sub_workflows_returns_empty(self):
        """PARALLEL node without _sub_workflows returns []."""
        wf = Workflow(id="par", name="par", description="")
        n = Node(id="n0", name="fan", node_type=NodeType.PARALLEL)
        wf.add_node(n)

        result = self.executor.execute(wf)
        self.assertEqual(result["n0"], [])

    # -- input building -----------------------------------------------------

    def test_build_input_includes_dependency_outputs(self):
        """_build_input merges outputs of dependency nodes."""
        agent = _mock_agent_run("step2-output")
        self.executor.agents._agents = {"default": agent}

        wf = Workflow(id="dep", name="dep", description="")
        n1 = Node(id="n1", name="first", node_type=NodeType.AGENT)
        n2 = Node(id="n2", name="second", node_type=NodeType.AGENT,
                  depends_on=["n1"])
        wf.add_node(n1)
        wf.add_node(n2)

        result = self.executor.execute(wf)

        # second call to agent.run received merged inputs
        call_args = agent.run.call_args_list[1][0][0]
        self.assertIn("n1", call_args)

    def test_build_input_includes_agent_prompt(self):
        """_build_input adds _prompt when agent_prompt is configured."""
        agent = _mock_agent_run("ok")
        self.executor.agents._agents = {"default": agent}

        wf = Workflow(id="p", name="p", description="")
        wf.add_node(Node(id="n0", name="t", node_type=NodeType.AGENT,
                          config=NodeConfig(agent_prompt="do it")))

        self.executor.execute(wf)
        call_input = agent.run.call_args[0][0]
        self.assertEqual(call_input["_prompt"], "do it")

    def test_build_input_includes_tool_args(self):
        """_build_input merges tool_args into inputs."""
        agent = _mock_agent_run("ok")
        self.executor.agents._agents = {"default": agent}

        wf = Workflow(id="t", name="t", description="")
        wf.add_node(Node(id="n0", name="t", node_type=NodeType.AGENT,
                          config=NodeConfig(tool_args={"path": "/tmp"})))

        self.executor.execute(wf)
        call_input = agent.run.call_args[0][0]
        self.assertEqual(call_input["path"], "/tmp")

    def test_output_key_populates_variables(self):
        """output_key maps node output to a named variable."""
        agent = _mock_agent_run("final")
        self.executor.agents._agents = {"default": agent}

        wf = Workflow(id="ok", name="ok", description="")
        wf.add_node(Node(id="n0", name="t", node_type=NodeType.AGENT,
                          config=NodeConfig(output_key="result")))

        result = self.executor.execute(wf)
        self.assertEqual(result["result"], "final")

    # -- default node type --------------------------------------------------

    def test_unknown_node_type_passthrough(self):
        """Unrecognised node_type passes input through as output."""
        wf = Workflow(id="unk", name="unk", description="")
        wf.add_node(Node(id="n0", name="t", node_type=NodeType.HUMAN))

        result = self.executor.execute(wf, {"x": 1})
        self.assertEqual(result["n0"], {"x": 1})

    # -- register_agent -----------------------------------------------------

    def test_register_agent_adds_to_registry(self):
        agent = _mock_agent_run()
        self.executor.register_agent("helper", agent)
        fetched = self.executor.agents.get("helper")
        self.assertIs(fetched, agent)


# ---------------------------------------------------------------------------
# 2.  Pipeline.run()
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_PIPELINE, "chromadb not installed")
class TestPipelineRun(unittest.TestCase):
    """Tests for Pipeline.run() with and without evaluate."""

    @classmethod
    def setUpClass(cls):
        # Prevent real LLM / ChromaDB / MemoryStore / WorkflowExecutor
        # instantiation across all Pipeline tests.  We patch at the
        # Pipeline module's import site so the constructor never touches
        # disk or the network.
        cls._patchers = [
            patch("agentforge.pipeline.MemoryStore"),
            patch("agentforge.pipeline.ContextCompressor"),
            patch("agentforge.pipeline.WorkflowExecutor"),
            patch("agentforge.evaluation.judge.get_llm"),
        ]
        cls.mock_memory_store_cls = cls._patchers[0].start()
        cls.mock_compressor_cls = cls._patchers[1].start()
        cls.mock_executor_cls = cls._patchers[2].start()
        cls.mock_get_llm = cls._patchers[3].start()

    @classmethod
    def tearDownClass(cls):
        for p in cls._patchers:
            p.stop()

    def setUp(self):
        # Give the mocked WorkflowExecutor a fake .execute()
        mock_exec = MagicMock()
        mock_exec.execute = MagicMock(return_value={"result": "done"})
        type(self).mock_executor_cls.return_value = mock_exec
        self.pipeline = Pipeline("wf-1")

    def test_run_without_evaluate(self):
        wf = _make_simple_linear_workflow()
        result = self.pipeline.run(wf, {"q": "test"}, evaluate=False)

        self.assertEqual(result, {"result": "done"})
        self.assertEqual(len(self.pipeline.history), 1)
        run_record = self.pipeline.history[0]
        self.assertEqual(run_record["workflow_id"], wf.id)
        self.assertNotIn("evaluation", run_record)

    def test_run_with_evaluate(self):
        """With evaluate=True the evaluation report is attached."""
        mock_report = JudgeReport(
            task="...", agent_output="...", results=[],
            overall_score=8.5, verdict="GOOD", summary="good job",
        )
        self.pipeline.evaluator.evaluate = MagicMock(return_value=mock_report)
        self.pipeline.memory.save_session = MagicMock()

        wf = _make_simple_linear_workflow()
        result = self.pipeline.run(wf, {"q": "test"}, evaluate=True)

        self.assertEqual(result, {"result": "done"})
        run_record = self.pipeline.history[0]
        self.assertIn("evaluation", run_record)
        self.assertEqual(run_record["evaluation"]["score"], 8.5)
        self.assertEqual(run_record["evaluation"]["verdict"], "GOOD")
        self.pipeline.memory.save_session.assert_called_once()

    def test_run_stream_events_emitted(self):
        """Pipeline emits workflow_started & workflow_completed events."""
        wf = _make_simple_linear_workflow()
        self.pipeline.run(wf, evaluate=False)

        log = self.pipeline.stream.get_log()
        event_types = [e["type"] for e in log]
        self.assertIn("workflow_started", event_types)
        self.assertIn("workflow_completed", event_types)

    def test_run_history_appends_multiple(self):
        wf = _make_simple_linear_workflow()
        self.pipeline.run(wf)
        self.pipeline.run(wf)

        self.assertEqual(len(self.pipeline.history), 2)

    # -- recall_context / get_run_history / compress_history ----------------

    def test_recall_context_no_memories_returns_empty_string(self):
        self.pipeline.memory.recall = MagicMock(return_value=[])
        self.assertEqual(self.pipeline.recall_context("query"), "")

    def test_recall_context_with_memories(self):
        self.pipeline.memory.recall = MagicMock(return_value=[
            {"content": "mem-a", "score": 0.9},
            {"content": "mem-b", "score": 0.7},
        ])
        ctx = self.pipeline.recall_context("query", n_results=2)
        self.assertIn("mem-a", ctx)
        self.assertIn("mem-b", ctx)

    def test_get_run_history(self):
        wf = _make_simple_linear_workflow()
        self.pipeline.run(wf)
        self.assertEqual(len(self.pipeline.get_run_history()), 1)

    def test_compress_history_delegates(self):
        wf = _make_simple_linear_workflow()
        self.pipeline.run(wf)
        self.pipeline.compressor.compress = MagicMock(return_value="compressed")

        result = self.pipeline.compress_history("query")
        self.pipeline.compressor.compress.assert_called_once()
        self.assertEqual(result, "compressed")


# ---------------------------------------------------------------------------
# 2b.  BatchRunner
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_PIPELINE, "chromadb not installed")
class TestBatchRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._patchers = [
            patch("agentforge.pipeline.MemoryStore"),
            patch("agentforge.pipeline.ContextCompressor"),
            patch("agentforge.pipeline.WorkflowExecutor"),
            patch("agentforge.evaluation.judge.get_llm"),
        ]
        cls._patchers[0].start()
        cls._patchers[1].start()
        cls.mock_executor_cls = cls._patchers[2].start()
        cls._patchers[3].start()

    @classmethod
    def tearDownClass(cls):
        for p in cls._patchers:
            p.stop()

    def test_batch_runner_parallel_execution(self):
        # Configure the mocked WorkflowExecutor that auto-created
        # pipelines will use.
        mock_exec = MagicMock()
        mock_exec.execute = MagicMock(return_value={"ok": True})
        type(self).mock_executor_cls.return_value = mock_exec

        runner = BatchRunner(max_parallel=3)
        wf = _make_simple_linear_workflow()
        results = runner.run_all(wf, [{"i": i} for i in range(3)])

        self.assertEqual(len(results), 3)
        for key in results:
            self.assertEqual(results[key], {"ok": True})

    def test_batch_runner_stats(self):
        mock_exec = MagicMock()
        mock_exec.execute = MagicMock(return_value={})
        type(self).mock_executor_cls.return_value = mock_exec

        runner = BatchRunner()
        self.assertEqual(runner.get_stats(), {"pipelines": 0, "total_runs": 0})

        # Add a pipeline manually -- run_all will also auto-create batch_0
        p = Pipeline("w")
        runner.add("p1", p)
        wf = _make_simple_linear_workflow()
        runner.run_all(wf, [{"a": 1}])

        stats = runner.get_stats()
        # "p1" (added) + "batch_0" (auto-created) = 2 pipelines
        self.assertEqual(stats["pipelines"], 2)
        # only batch_0 was executed by run_all; p1 has 0 runs
        self.assertEqual(stats["total_runs"], 1)


# ---------------------------------------------------------------------------
# 3.  Workflow presets
# ---------------------------------------------------------------------------

class TestWorkflowPresets(unittest.TestCase):
    """Verify all 5 presets generate structurally valid Workflows."""

    def test_code_review_pipeline_structure(self):
        wf = code_review_pipeline("def foo(): pass")
        self.assertIsInstance(wf, Workflow)
        self.assertEqual(wf.name, "Code Review Pipeline")
        self.assertEqual(len(wf.nodes), 3)
        # linear chain: node_0 → node_1 → node_2
        self.assertEqual(wf.get_node("node_1").depends_on, ["node_0"])
        self.assertEqual(wf.get_node("node_2").depends_on, ["node_1"])
        self.assertEqual(len(wf.get_root_nodes()), 1)

    def test_research_synthesis_pipeline_structure(self):
        wf = research_synthesis_pipeline("quantum computing")
        self.assertEqual(wf.name, "Research: quantum computing")
        self.assertEqual(len(wf.nodes), 3)
        self.assertEqual(wf.get_node("node_1").depends_on, ["node_0"])
        self.assertEqual(len(wf.get_root_nodes()), 1)

    def test_multi_expert_analysis_structure(self):
        wf = multi_expert_analysis("AI safety")
        self.assertEqual(wf.name, "Expert Analysis: AI safety")
        # dispatcher + 3 workers + aggregator = 5
        self.assertEqual(len(wf.nodes), 5)
        # dispatcher is a root
        roots = wf.get_root_nodes()
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0].id, "dispatcher")
        # workers depend on dispatcher
        for i in range(3):
            self.assertIn("dispatcher", wf.get_node(f"worker_{i}").depends_on)
        # aggregator depends on all workers
        agg_deps = wf.get_node("aggregator").depends_on
        for i in range(3):
            self.assertIn(f"worker_{i}", agg_deps)

    def test_ci_cd_pipeline_structure(self):
        wf = ci_cd_pipeline("/my/repo")
        self.assertEqual(wf.name, "CI/CD Pipeline")
        self.assertEqual(len(wf.nodes), 4)
        self.assertEqual(wf.get_node("node_0").node_type, NodeType.TOOL)
        self.assertEqual(wf.get_node("node_1").node_type, NodeType.TOOL)
        self.assertEqual(wf.get_node("node_2").node_type, NodeType.TOOL)
        self.assertEqual(wf.get_node("node_3").node_type, NodeType.AGENT)

    def test_data_analysis_pipeline_structure(self):
        wf = data_analysis_pipeline("sales data Q1-Q4")
        self.assertEqual(wf.name, "Data Analysis Pipeline")
        self.assertEqual(len(wf.nodes), 3)
        self.assertTrue(wf.is_complete() is False)  # all pending initially

    # -- create_workflow dispatching ----------------------------------------

    def test_create_workflow_code_review(self):
        wf = create_workflow("code_review", "x = 1")
        self.assertEqual(wf.name, "Code Review Pipeline")

    def test_create_workflow_research(self):
        wf = create_workflow("research", "AI")
        self.assertIn("Research", wf.name)

    def test_create_workflow_multi_expert(self):
        wf = create_workflow("multi_expert", "climate")
        self.assertIn("Expert Analysis", wf.name)

    def test_create_workflow_ci_cd(self):
        wf = create_workflow("ci_cd", ".")
        self.assertEqual(wf.name, "CI/CD Pipeline")

    def test_create_workflow_data_analysis(self):
        wf = create_workflow("data_analysis", "logs")
        self.assertEqual(wf.name, "Data Analysis Pipeline")

    def test_create_workflow_invalid_preset_raises(self):
        with self.assertRaises(ValueError) as ctx:
            create_workflow("bogus", "input")
        self.assertIn("bogus", str(ctx.exception))
        self.assertIn("code_review", str(ctx.exception))

    # -- list_presets -------------------------------------------------------

    def test_list_presets_returns_five(self):
        presets = list_presets()
        self.assertEqual(len(presets), 5)
        names = {p["name"] for p in presets}
        expected = {"code_review", "research", "multi_expert", "ci_cd", "data_analysis"}
        self.assertEqual(names, expected)


# ---------------------------------------------------------------------------
# 4.  WorkflowStream event emission
# ---------------------------------------------------------------------------

class TestWorkflowStream(unittest.TestCase):
    def setUp(self):
        self.stream = WorkflowStream()

    # -- emit + listener ----------------------------------------------------

    def test_emit_appends_to_log(self):
        self.stream.emit("custom", {"key": "val"})
        log = self.stream.get_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["type"], "custom")

    def test_listener_receives_events(self):
        received = []
        self.stream.add_listener(lambda e: received.append(e))
        self.stream.emit("test", {"a": 1})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["type"], "test")

    def test_multiple_listeners_all_called(self):
        count = [0]

        def inc(_e):
            count[0] += 1

        self.stream.add_listener(inc)
        self.stream.add_listener(inc)
        self.stream.emit("x", {})
        self.assertEqual(count[0], 2)

    def test_remove_listener_stops_delivery(self):
        received = []

        def cb(e):
            received.append(e)

        self.stream.add_listener(cb)
        self.stream.remove_listener(cb)
        self.stream.emit("y", {})
        self.assertEqual(len(received), 0)

    def test_listener_exception_is_suppressed(self):
        def bad(_e):
            raise RuntimeError("boom")

        self.stream.add_listener(bad)
        # must not raise
        self.stream.emit("safe", {})
        self.assertEqual(len(self.stream.get_log()), 1)

    # -- convenience emitters -----------------------------------------------

    def test_node_started_emits_correct_type(self):
        self.stream.node_started("n1", "My Node")
        event = self.stream.get_log()[0]
        self.assertEqual(event["type"], "node_started")
        self.assertEqual(event["data"]["node_id"], "n1")

    def test_node_completed_emits_summary(self):
        self.stream.node_completed("n2", "Done", "the output", 123.4)
        event = self.stream.get_log()[0]
        self.assertEqual(event["data"]["node_name"], "Done")
        self.assertIn("the output", event["data"]["output_summary"])
        self.assertEqual(event["data"]["duration_ms"], 123.4)

    def test_node_failed_emits_error(self):
        self.stream.node_failed("n3", "Fail", "bad stuff")
        event = self.stream.get_log()[0]
        self.assertEqual(event["data"]["error"], "bad stuff")

    def test_workflow_started(self):
        self.stream.workflow_started("w1", "WF1")
        event = self.stream.get_log()[0]
        self.assertEqual(event["type"], "workflow_started")

    def test_workflow_completed(self):
        self.stream.workflow_completed("w2", {"x": 1})
        event = self.stream.get_log()[0]
        self.assertEqual(event["data"]["workflow_id"], "w2")

    # -- log / JSON ---------------------------------------------------------

    def test_get_log_respects_limit(self):
        for i in range(10):
            self.stream.emit("e", {"i": i})
        self.assertEqual(len(self.stream.get_log(limit=3)), 3)

    def test_to_json_returns_list(self):
        self.stream.emit("a", {})
        parsed = json.loads(self.stream.to_json())
        self.assertIsInstance(parsed, list)
        self.assertEqual(parsed[0]["type"], "a")


# ---------------------------------------------------------------------------
# 5.  AgentJudge.evaluate() & Evaluator
# ---------------------------------------------------------------------------

class TestAgentJudge(unittest.TestCase):
    """Tests for AgentJudge.evaluate() and Evaluator — all LLM calls mocked."""

    def setUp(self):
        # Prevent any real LLM call
        self.llm_patcher = patch("agentforge.evaluation.judge.get_llm")
        self.mock_get_llm = self.llm_patcher.start()
        self.mock_llm = MagicMock()
        self.mock_get_llm.return_value = self.mock_llm

    def tearDown(self):
        self.llm_patcher.stop()

    def _set_chat_response(self, json_obj):
        self.mock_llm.chat.return_value = json.dumps(json_obj)

    # -- evaluate() ---------------------------------------------------------

    def test_evaluate_parses_valid_json(self):
        self._set_chat_response({
            "evaluations": [
                {"dimension": "correctness", "score": 8, "reasoning": "good", "suggestions": []},
                {"dimension": "clarity", "score": 7, "reasoning": "ok", "suggestions": ["be clearer"]},
            ],
            "overall_score": 7.5,
            "verdict": "GOOD",
            "summary": "solid work",
        })

        judge = AgentJudge()
        report = judge.evaluate("Do X", "result")

        self.assertIsInstance(report, JudgeReport)
        self.assertEqual(len(report.results), 2)
        self.assertEqual(report.overall_score, 7.5)
        self.assertEqual(report.verdict, "GOOD")
        self.mock_llm.chat.assert_called_once()

    def test_evaluate_passes_task_and_output_to_llm(self):
        self._set_chat_response({
            "evaluations": [],
            "overall_score": 5,
            "verdict": "FAIR",
            "summary": "meh",
        })

        judge = AgentJudge()
        judge.evaluate("Task: fix bug", "the fix")

        call_args = self.mock_llm.chat.call_args
        prompt_text = call_args[0][0][0]["content"]
        self.assertIn("Task: fix bug", prompt_text)
        self.assertIn("the fix", prompt_text)

    def test_evaluate_truncates_long_output(self):
        self._set_chat_response({
            "evaluations": [],
            "overall_score": 3,
            "verdict": "POOR",
            "summary": "short",
        })

        judge = AgentJudge()
        long_output = "x" * 5000
        judge.evaluate("task", long_output)

        call_args = self.mock_llm.chat.call_args
        prompt_text = call_args[0][0][0]["content"]
        # should be truncated to ~4000 chars
        self.assertLess(len(prompt_text), 8500)  # whole prompt including instructions

    def test_evaluate_json_parse_error_returns_fail_report(self):
        self.mock_llm.chat.return_value = "not json { broken"

        judge = AgentJudge()
        report = judge.evaluate("task", "output")

        self.assertEqual(report.verdict, "FAIL")
        self.assertEqual(report.overall_score, 0)
        self.assertEqual(report.results, [])
        self.assertEqual(report.summary, "Failed to parse evaluation")

    def test_evaluate_missing_fields_default_gracefully(self):
        self._set_chat_response({
            "evaluations": [{"dimension": "safety", "score": 9}],
            "overall_score": 9,
            "verdict": "EXCELLENT",
            "summary": "great",
        })

        judge = AgentJudge()
        report = judge.evaluate("t", "o")

        result = report.results[0]
        self.assertEqual(result.reasoning, "")
        self.assertEqual(result.suggestions, [])

    # -- custom dimensions --------------------------------------------------

    def test_judge_with_custom_dimensions(self):
        custom_dims = [EvalDimension("speed", "How fast", 2.0)]
        self._set_chat_response({
            "evaluations": [{"dimension": "speed", "score": 10, "reasoning": "fast"}],
            "overall_score": 10,
            "verdict": "EXCELLENT",
            "summary": "yep",
        })

        judge = AgentJudge(dimensions=custom_dims)
        judge.evaluate("t", "o")

        call = self.mock_llm.chat.call_args[0][0][0]["content"]
        self.assertIn("speed", call)
        self.assertIn("How fast", call)

    # -- diff() -------------------------------------------------------------

    def test_diff_returns_llm_output(self):
        self.mock_llm.chat.return_value = '{"winner":"A","reasons":["better"],"key_differences":["x"]}'

        judge = AgentJudge()
        result = judge.diff("task", "out-a", "out-b")
        self.assertIn("A", result)
        self.mock_llm.chat.assert_called_once()


class TestEvaluator(unittest.TestCase):
    """Tests for the high-level Evaluator wrapper."""

    def setUp(self):
        self.llm_patcher = patch("agentforge.evaluation.judge.get_llm")
        self.mock_get_llm = self.llm_patcher.start()
        self.mock_llm = MagicMock()
        self.mock_get_llm.return_value = self.mock_llm

    def tearDown(self):
        self.llm_patcher.stop()

    def _set_chat_response(self, json_obj):
        self.mock_llm.chat.return_value = json.dumps(json_obj)

    def test_evaluator_run_stores_history(self):
        self._set_chat_response({
            "evaluations": [{"dimension": "c", "score": 7}],
            "overall_score": 7,
            "verdict": "GOOD",
            "summary": "ok",
        })

        ev = Evaluator()
        report = ev.run("task", "output")

        self.assertEqual(report.overall_score, 7)
        self.assertEqual(len(ev.history), 1)

    def test_evaluator_evaluate_is_alias_for_run(self):
        self._set_chat_response({
            "evaluations": [{"dimension": "c", "score": 5}],
            "overall_score": 5,
            "verdict": "FAIR",
            "summary": "alright",
        })

        ev = Evaluator()
        report = ev.evaluate("t", "o")
        self.assertEqual(report.overall_score, 5)
        self.assertEqual(len(ev.history), 1)

    def test_evaluator_benchmark_averages_scores(self):
        responses = [
            {"evaluations": [{"dimension": "c", "score": 6}], "overall_score": 6, "verdict": "FAIR", "summary": ""},
            {"evaluations": [{"dimension": "c", "score": 10}], "overall_score": 10, "verdict": "EXCELLENT", "summary": ""},
        ]
        self.mock_llm.chat.side_effect = [json.dumps(r) for r in responses]

        ev = Evaluator()
        result = ev.benchmark(
            [{"task": "t1"}, {"task": "t2"}],
            agent_fn=lambda task: f"output-{task}",
        )
        self.assertEqual(result["cases"], 2)
        self.assertEqual(result["average_score"], 8.0)

    def test_evaluator_benchmark_empty_cases(self):
        ev = Evaluator()
        result = ev.benchmark([], agent_fn=lambda t: t)
        self.assertEqual(result["cases"], 0)
        self.assertEqual(result["average_score"], 0)

    def test_evaluator_get_history_stats_empty(self):
        ev = Evaluator()
        self.assertEqual(ev.get_history_stats(), {"total": 0})

    def test_evaluator_get_history_stats_populated(self):
        self._set_chat_response({
            "evaluations": [{"dimension": "c", "score": 4}],
            "overall_score": 4,
            "verdict": "POOR",
            "summary": "bad",
        })
        ev = Evaluator()
        ev.run("t1", "o1")

        self.mock_llm.chat.return_value = json.dumps({
            "evaluations": [{"dimension": "c", "score": 9}],
            "overall_score": 9,
            "verdict": "EXCELLENT",
            "summary": "great",
        })
        ev.run("t2", "o2")

        stats = ev.get_history_stats()
        self.assertEqual(stats["total"], 2)
        self.assertAlmostEqual(stats["avg_score"], 6.5)
        self.assertEqual(stats["min_score"], 4)
        self.assertEqual(stats["max_score"], 9)
        self.assertIn("POOR", stats["verdict_distribution"])
        self.assertIn("EXCELLENT", stats["verdict_distribution"])


# ---------------------------------------------------------------------------
#  Dataclass smoke-tests
# ---------------------------------------------------------------------------

class TestDataclasses(unittest.TestCase):
    def test_eval_dimension_defaults(self):
        d = EvalDimension("speed", "How fast")
        self.assertEqual(d.weight, 1.0)

    def test_eval_result_defaults(self):
        r = EvalResult("correctness", 8.0, "good")
        self.assertEqual(r.suggestions, [])

    def test_judge_report_fields(self):
        rpt = JudgeReport(
            task="t", agent_output="o", results=[],
            overall_score=1, verdict="FAIL", summary="nope",
        )
        self.assertEqual(rpt.task, "t")

    def test_default_dimensions_have_six_entries(self):
        self.assertEqual(len(DEFAULT_DIMENSIONS), 6)


if __name__ == "__main__":
    unittest.main()
