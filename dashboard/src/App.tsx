import { useState, useEffect } from 'react'

const BASE = '/api'

async function api(path: string, opts?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...opts })
  return res.json()
}

function App() {
  const [tab, setTab] = useState<'agents' | 'tools' | 'evaluate' | 'memory' | 'workflows' | 'presets' | 'settings'>('agents')

  return (
    <div className="max-w-6xl mx-auto p-6">
      <header className="flex items-center justify-between mb-6 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AgentForge Dashboard</h1>
          <p className="text-sm text-gray-500">Multi-Agent Workflow Platform</p>
        </div>
        <nav className="flex gap-1 bg-gray-100 rounded-lg p-1 flex-wrap">
          {(
            [
              { id: 'agents', label: 'Agents' },
              { id: 'tools', label: 'Tools' },
              { id: 'workflows', label: 'Workflows' },
              { id: 'presets', label: 'Presets' },
              { id: 'evaluate', label: 'Evaluate' },
              { id: 'memory', label: 'Memory' },
              { id: 'settings', label: 'Settings' },
            ] as const
          ).map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === t.id ? 'bg-white shadow text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {tab === 'agents' && <AgentsTab />}
      {tab === 'tools' && <ToolsTab />}
      {tab === 'evaluate' && <EvaluateTab />}
      {tab === 'memory' && <MemoryTab />}
      {tab === 'workflows' && <WorkflowsTab />}
      {tab === 'presets' && <PresetsTab />}
      {tab === 'settings' && <SettingsTab />}
    </div>
  )
}

function AgentsTab() {
  const [agents, setAgents] = useState<any[]>([])
  const [msg, setMsg] = useState('')
  const [agentName, setAgentName] = useState('default')
  const [response, setResponse] = useState('')

  useEffect(() => { api('/agents').then(d => setAgents(d.agents || [])) }, [])

  const run = async () => {
    setResponse('...')
    const d = await api('/agents/run', { method: 'POST', body: JSON.stringify({ agent_name: agentName, message: msg }) })
    setResponse(d.output || JSON.stringify(d))
  }

  return (
    <div className="grid md:grid-cols-3 gap-6">
      <div className="md:col-span-1 space-y-4">
        <h2 className="font-semibold">Registered Agents</h2>
        {agents.map(a => (
          <button key={a.name} onClick={() => setAgentName(a.name)}
            className={`w-full text-left p-3 rounded-lg border text-sm ${agentName === a.name ? 'border-indigo-300 bg-indigo-50' : 'border-gray-200 hover:border-gray-300'}`}>
            <div className="font-medium">{a.name}</div>
            <div className="text-gray-500 text-xs mt-0.5">{a.description}</div>
          </button>
        ))}
      </div>

      <div className="md:col-span-2 space-y-4">
        <h2 className="font-semibold">Test Agent: <span className="text-indigo-600">{agentName}</span></h2>
        <textarea value={msg} onChange={e => setMsg(e.target.value)}
          placeholder="Enter your message..."
          className="w-full h-32 p-3 border border-gray-200 rounded-lg text-sm resize-y focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        <button onClick={run} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">
          Run Agent
        </button>
        {response && <pre className="bg-gray-50 p-4 rounded-lg text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">{response}</pre>}
      </div>
    </div>
  )
}

function ToolsTab() {
  const [tools, setTools] = useState<any[]>([])
  const [toolName, setToolName] = useState('read_file')
  const [args, setArgs] = useState('{"path": "."}')
  const [result, setResult] = useState('')

  useEffect(() => { api('/tools').then(d => setTools(d.tools || [])) }, [])

  const run = async () => {
    try {
      const parsed = JSON.parse(args)
      const d = await api(`/tools/${toolName}`, { method: 'POST', body: JSON.stringify(parsed) })
      setResult(JSON.stringify(d.result, null, 2))
    } catch (e: any) { setResult(`Error: ${e.message}`) }
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div>
        <h2 className="font-semibold mb-3">Available Tools ({tools.length})</h2>
        <div className="space-y-1 max-h-96 overflow-y-auto">
          {tools.map(t => (
            <button key={t.name} onClick={() => setToolName(t.name)}
              className={`w-full text-left px-3 py-2 rounded text-sm ${toolName === t.name ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50'}`}>
              <span className="font-medium font-mono text-xs">{t.name}</span>
              <span className="text-gray-400 text-xs ml-2">[{t.type || t._server || 'builtin'}]</span>
            </button>
          ))}
        </div>
      </div>
      <div>
        <div className="mb-3">
          <label className="text-xs font-medium text-gray-500">Arguments (JSON)</label>
          <textarea value={args} onChange={e => setArgs(e.target.value)}
            className="w-full h-24 p-3 border border-gray-200 rounded-lg text-sm font-mono resize-y" />
        </div>
        <button onClick={run} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm mb-3">Execute</button>
        <pre className="text-xs bg-gray-50 p-3 rounded-lg max-h-64 overflow-y-auto">{result || 'No result'}</pre>
      </div>
    </div>
  )
}

function EvaluateTab() {
  const [task, setTask] = useState('')
  const [output, setOutput] = useState('')
  const [report, setReport] = useState<any>(null)

  const run = async () => {
    const d = await api('/evaluate', { method: 'POST', body: JSON.stringify({ task, output }) })
    setReport(d)
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div>
        <textarea value={task} onChange={e => setTask(e.target.value)} placeholder="Original task..."
          className="w-full h-24 p-3 border border-gray-200 rounded-lg text-sm resize-y mb-3" />
        <textarea value={output} onChange={e => setOutput(e.target.value)} placeholder="Agent output to evaluate..."
          className="w-full h-32 p-3 border border-gray-200 rounded-lg text-sm resize-y mb-3" />
        <button onClick={run} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Evaluate</button>
      </div>
      <div>
        {report && (
          <div className="space-y-3">
            <div className={`text-lg font-bold px-3 py-1 rounded inline-block text-sm ${report.verdict === 'EXCELLENT' ? 'bg-green-100 text-green-700' : report.verdict === 'GOOD' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
              {report.verdict} — {report.overall_score}/60
            </div>
            <p className="text-sm text-gray-600">{report.summary}</p>
            {report.results?.map((r: any) => (
              <div key={r.dimension} className="bg-gray-50 p-3 rounded-lg text-sm">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium">{r.dimension}</span>
                  <span className="text-xs bg-gray-200 px-2 py-0.5 rounded">{r.score}/10</span>
                </div>
                <p className="text-gray-600 text-xs">{r.reasoning}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function MemoryTab() {
  const [stats, setStats] = useState<any>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])

  useEffect(() => { api('/memory/stats').then(setStats) }, [])

  const search = async () => {
    const d = await api('/memory/search', { method: 'POST', body: JSON.stringify({ query }) })
    setResults(d.results || [])
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div>
        <h2 className="font-semibold mb-3">Memory Stats</h2>
        {stats && <pre className="text-sm bg-gray-50 p-4 rounded-lg">{JSON.stringify(stats, null, 2)}</pre>}
      </div>
      <div>
        <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && search()}
          placeholder="Search memory..." className="w-full p-3 border border-gray-200 rounded-lg text-sm mb-3" />
        <button onClick={search} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm mb-4">Search</button>
        {results.map((r, i) => (
          <div key={i} className="bg-gray-50 p-3 rounded-lg text-xs mb-2">
            <span className="text-gray-400">Score: {r.score?.toFixed(2)}</span>
            <p className="text-gray-700 mt-1">{r.content?.slice(0, 300)}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function WorkflowsTab() {
  const [wfJSON, setWfJSON] = useState(`{"id":"demo","name":"Demo Pipeline","description":"","nodes":[{"id":"n1","name":"Research","type":"agent","config":{"agent_role":"researcher","agent_prompt":"Research AI agent frameworks in 2026"}},{"id":"n2","name":"Report","type":"agent","config":{"agent_role":"writer","agent_prompt":"Write a summary"}}],"edges":[{"from":"n1","to":"n2"}]}`)
  const [result, setResult] = useState('')
  const [valid, setValid] = useState<boolean | null>(null)

  const validate = async () => {
    try {
      const d = await api('/workflows/validate', { method: 'POST', body: JSON.stringify({ workflow: JSON.parse(wfJSON) }) })
      setValid(d.valid)
      setResult(JSON.stringify(d, null, 2))
    } catch (e: any) { setResult(`Invalid JSON: ${e.message}`); setValid(false) }
  }

  const run = async () => {
    setResult('Running...')
    try {
      const d = await api('/workflows/run', { method: 'POST', body: JSON.stringify({ workflow: JSON.parse(wfJSON) }) })
      setResult(JSON.stringify(d.result, null, 2))
    } catch (e: any) { setResult(`Error: ${e.message}`) }
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div>
        <h2 className="font-semibold mb-2">Workflow JSON Editor</h2>
        <textarea value={wfJSON} onChange={e => setWfJSON(e.target.value)}
          className="w-full h-96 p-3 border border-gray-200 rounded-lg text-sm font-mono resize-y" />
        <div className="flex gap-2 mt-3">
          <button onClick={validate} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Validate</button>
          <button onClick={run} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Run Workflow</button>
        </div>
        {valid !== null && (
          <span className={`ml-3 text-sm ${valid ? 'text-green-600' : 'text-red-600'}`}>
            {valid ? 'Valid' : 'Invalid'}
          </span>
        )}
      </div>
      <div>
        <h2 className="font-semibold mb-2">Result</h2>
        <pre className="text-xs bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto whitespace-pre-wrap">{result || 'Run a workflow to see results'}</pre>
      </div>
    </div>
  )
}

function PresetsTab() {
  const presets = [
    { id: 'code_review', name: 'Code Review', desc: 'PM → Dev → Reviewer pipeline for quality assurance', example: 'agentforge workflow code_review --code "def foo(x): return x+1"' },
    { id: 'research', name: 'Research Synthesis', desc: 'Research → Synthesize → Write for deep topic analysis', example: 'agentforge workflow research --topic "AI agents in 2026"' },
    { id: 'multi_expert', name: 'Multi-Expert Analysis', desc: '3 experts analyze independently → aggregated report', example: 'agentforge workflow multi_expert --topic "Microservices vs monolith"' },
    { id: 'ci_cd', name: 'CI/CD Pipeline', desc: 'Lint → Test → Build → Deploy automation', example: 'agentforge workflow ci_cd --repo-path "./my-project"' },
    { id: 'data_analysis', name: 'Data Analysis', desc: 'Analyze → Visualize → Report for data insights', example: 'agentforge workflow data_analysis --data "..."' },
  ]

  return (
    <div className="grid md:grid-cols-3 gap-4">
      {presets.map(p => (
        <div key={p.id} className="border border-gray-200 rounded-xl p-5 hover:border-indigo-200 transition-colors">
          <h3 className="font-semibold text-indigo-600 mb-1">{p.name}</h3>
          <p className="text-sm text-gray-600 mb-3">{p.desc}</p>
          <code className="text-[11px] bg-gray-50 p-2 rounded block text-gray-500 break-all">{p.example}</code>
        </div>
      ))}
    </div>
  )
}

function SettingsTab() {
  const [config, setConfig] = useState({ model: 'gpt-4o-mini', max_parallel: '5', memory_path: './agentforge_memory', temperature: '0.3', max_tokens: '4096' })

  const update = (key: string, value: string) => setConfig(prev => ({ ...prev, [key]: value }))

  return (
    <div className="max-w-lg space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">LLM Model</label>
        <input value={config.model} onChange={e => update('model', e.target.value)}
          className="w-full p-2.5 border border-gray-200 rounded-lg text-sm" />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Max Parallel Agents</label>
        <input type="number" value={config.max_parallel} onChange={e => update('max_parallel', e.target.value)}
          className="w-full p-2.5 border border-gray-200 rounded-lg text-sm" />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Memory Path</label>
        <input value={config.memory_path} onChange={e => update('memory_path', e.target.value)}
          className="w-full p-2.5 border border-gray-200 rounded-lg text-sm" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
          <input type="number" step="0.1" min="0" max="2" value={config.temperature} onChange={e => update('temperature', e.target.value)}
            className="w-full p-2.5 border border-gray-200 rounded-lg text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
          <input type="number" value={config.max_tokens} onChange={e => update('max_tokens', e.target.value)}
            className="w-full p-2.5 border border-gray-200 rounded-lg text-sm" />
        </div>
      </div>
      <div className="bg-gray-50 rounded-xl p-4 mt-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Environment Variables</h3>
        <code className="text-xs text-gray-500 block">
          OPENAI_API_KEY=sk-...<br/>
          OPENAI_BASE_URL=https://api.openai.com/v1<br/>
          AGENTFORGE_MODEL=gpt-4o-mini
        </code>
      </div>
    </div>
  )
}

export default App
