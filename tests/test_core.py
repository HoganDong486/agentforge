"""AgentForge test suite."""
import json
import unittest
from agentforge.engine.node import Node, NodeConfig, NodeType, Workflow
from agentforge.engine.executor import WorkflowExecutor
from agentforge.agents.registry import AgentRegistry
from agentforge.agents.base import AgentConfig
from agentforge.tools.mcp_client import ToolRegistry
from agentforge.memory.compressor import ContextCompressor
from agentforge.workflows import list_presets, create_workflow


class TestNode(unittest.TestCase):
    def test_node_creation(self):
        n = Node(id="n1", name="Test", node_type=NodeType.AGENT)
        self.assertEqual(n.status.value, "pending")
        self.assertIsNone(n.output)

    def test_node_status_lifecycle(self):
        n = Node(id="n1", name="Test", node_type=NodeType.AGENT)
        n.status = NodeStatus.__members__["RUNNING"]
        self.assertEqual(n.status.value, "running")
        n.status = NodeStatus.__members__["SUCCESS"]
        n.output = "done"
        self.assertEqual(n.status.value, "success")

    def test_node_reset(self):
        n = Node(id="n1", name="Test", node_type=NodeType.AGENT, output="old")
        n.reset()
        self.assertIsNone(n.output)


class TestWorkflow(unittest.TestCase):
    def test_empty_workflow(self):
        wf = Workflow(id="w1", name="Test", description="")
        self.assertEqual(len(wf.nodes), 0)

    def test_add_node_and_edge(self):
        wf = Workflow(id="w1", name="Test", description="")
        n1 = Node(id="n1", name="Step 1", node_type=NodeType.AGENT)
        n2 = Node(id="n2", name="Step 2", node_type=NodeType.AGENT)
        wf.add_node(n1)
        wf.add_node(n2)
        wf.add_edge("n1", "n2")
        self.assertEqual(len(wf.nodes), 2)
        self.assertEqual(wf.get_node("n2").depends_on, ["n1"])

    def test_root_nodes(self):
        wf = Workflow(id="w1", name="Test", description="")
        wf.add_node(Node(id="n1", name="Root", node_type=NodeType.AGENT))
        wf.add_node(Node(id="n2", name="Child", node_type=NodeType.AGENT))
        wf.add_edge("n1", "n2")
        roots = wf.get_root_nodes()
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0].id, "n1")

    def test_completion_detection(self):
        wf = Workflow(id="w1", name="Test", description="")
        n = Node(id="n1", name="Solo", node_type=NodeType.AGENT)
        wf.add_node(n)
        n.status = NodeStatus.__members__["SUCCESS"]
        self.assertTrue(wf.is_complete())


class TestRegistry(unittest.TestCase):
    def test_default_agents_registered(self):
        reg = AgentRegistry()
        agents = reg.list_agents()
        self.assertGreater(len(agents), 0)

    def test_get_agent(self):
        reg = AgentRegistry()
        agent = reg.get("default")
        self.assertIsNotNone(agent)

    def test_agent_not_found(self):
        reg = AgentRegistry()
        agent = reg.get("nonexistent")
        self.assertIsNone(agent)


class TestBuiltinTools(unittest.TestCase):
    def setUp(self):
        import os
        self.test_path = os.path.join(os.path.dirname(__file__), "_test_temp_file.txt")

    def test_read_file(self):
        from agentforge.tools.builtin_tools import read_file, write_file
        write_file({"path": self.test_path, "content": "hello world"})
        content = read_file({"path": self.test_path})
        self.assertIn("hello", content)

    def test_list_files(self):
        from agentforge.tools.builtin_tools import list_files
        entries = list_files({"path": "."})
        self.assertGreater(len(entries), 0)


class TestToolRegistry(unittest.TestCase):
    def test_register_and_list(self):
        tr = ToolRegistry()
        tr.register_function("echo", lambda args: args.get("text", ""))
        tools = tr.list_all()
        self.assertTrue(any(t["name"] == "echo" for t in tools))


class TestCompressor(unittest.TestCase):
    def test_compressor_creation(self):
        c = ContextCompressor()
        self.assertEqual(c.target_tokens, 2000)

    def test_skip_small_content(self):
        c = ContextCompressor()
        msgs = [{"role": "user", "content": "Hi"}]
        result = c.compress(msgs, "test")
        self.assertEqual(len(result), len(msgs))


class TestWorkflowPresets(unittest.TestCase):
    def test_list_presets(self):
        presets = list_presets()
        self.assertEqual(len(presets), 5)

    def test_create_code_review(self):
        code = "def foo(x):\n    return x + 1"
        result = create_workflow("code_review", code)
        self.assertEqual(result.name, "Code Review Pipeline")


class TestWorkflowJSON(unittest.TestCase):
    def test_serialize_deserialize(self):
        code = "def add(a, b): return a + b"
        wf = create_workflow("code_review", code)
        data = wf.to_dict()
        wf2 = Workflow.from_dict(data)
        self.assertEqual(len(wf2.nodes), len(wf.nodes))
        self.assertEqual(wf2.name, wf.name)

    def test_linear_workflow_json(self):
        code = "def foo(): pass"
        wf = create_workflow("code_review", code)
        json_str = wf.to_json()
        self.assertIn("Code Review Pipeline", json_str)
        parsed = json.loads(json_str)
        self.assertEqual(len(parsed["nodes"]), 3)


class TestModelRouter(unittest.TestCase):
    def test_router_list_models(self):
        from agentforge.router import ModelRouter
        router = ModelRouter()
        models = router.list_models()
        self.assertGreater(len(models), 0)


if __name__ == "__main__":
    unittest.main()
