import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { Activity, Key, Settings, BarChart3, Zap, Clock, Shield, Database } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
console.log("Backend URL:", BACKEND_URL);

const API = `${BACKEND_URL}/api`;
console.log("API URL:", API);
// Dashboard Component
const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [recentLogs, setRecentLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 2000); // Refresh every 2 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, statusRes, logsRes] = await Promise.all([
        axios.get(`${API}/analytics/summary`),
        axios.get(`${API}/system-status`),
        axios.get(`${API}/analytics/recent-logs?limit=10`)
      ]);
      setStats(statsRes.data);
      setSystemStatus(statusRes.data);
      setRecentLogs(logsRes.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2" data-testid="dashboard-title">Rate Limiter Dashboard</h1>
          <p className="text-purple-200">Real-time monitoring of API rate limiting system</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Requests"
            value={stats?.total_requests || 0}
            icon={<Activity className="w-6 h-6" />}
            color="blue"
            testId="total-requests-stat"
          />
          <StatCard
            title="Allowed"
            value={stats?.allowed_requests || 0}
            icon={<Shield className="w-6 h-6" />}
            color="green"
            testId="allowed-requests-stat"
          />
          <StatCard
            title="Blocked"
            value={stats?.blocked_requests || 0}
            icon={<Clock className="w-6 h-6" />}
            color="red"
            testId="blocked-requests-stat"
          />
          <StatCard
            title="Success Rate"
            value={`${stats?.success_rate || 0}%`}
            icon={<BarChart3 className="w-6 h-6" />}
            color="purple"
            testId="success-rate-stat"
          />
        </div>

        {/* Algorithm Performance */}
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 mb-8 border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-4" data-testid="algorithm-performance-title">Algorithm Performance</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {stats?.algorithm_stats && Object.entries(stats.algorithm_stats).map(([algo, data]) => (
              <AlgorithmCard key={algo} algorithm={algo} data={data} />
            ))}
          </div>
        </div>

        {/* System Status */}
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 mb-8 border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-4" data-testid="system-status-title">System Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatusItem label="Active API Keys" value={systemStatus?.active_api_keys || 0} />
            <StatusItem label="Active Configs" value={systemStatus?.active_configs || 0} />
            <StatusItem label="Total Logs" value={systemStatus?.total_requests_logged || 0} />
            <StatusItem label="Status" value={systemStatus?.status || 'N/A'} isStatus />
          </div>
        </div>

        {/* Recent Logs */}
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-4" data-testid="recent-logs-title">Recent Request Logs</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left" data-testid="recent-logs-table">
              <thead>
                <tr className="border-b border-white/20">
                  <th className="pb-3 text-purple-200 font-semibold">Timestamp</th>
                  <th className="pb-3 text-purple-200 font-semibold">API Key</th>
                  <th className="pb-3 text-purple-200 font-semibold">Algorithm</th>
                  <th className="pb-3 text-purple-200 font-semibold">Status</th>
                  <th className="pb-3 text-purple-200 font-semibold">Remaining</th>
                </tr>
              </thead>
              <tbody>
                {recentLogs.map((log, idx) => (
                  <tr key={log.id} className="border-b border-white/10" data-testid={`log-row-${idx}`}>
                    <td className="py-3 text-white text-sm">{new Date(log.timestamp).toLocaleTimeString()}</td>
                    <td className="py-3 text-white text-sm font-mono">{log.api_key.substring(0, 20)}...</td>
                    <td className="py-3 text-white text-sm">{log.algorithm.replace('_', ' ')}</td>
                    <td className="py-3">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        log.allowed ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'
                      }`}>
                        {log.allowed ? 'Allowed' : 'Blocked'}
                      </span>
                    </td>
                    <td className="py-3 text-white text-sm">{log.remaining_quota}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, icon, color, testId }) => {
  const colorClasses = {
    blue: 'from-blue-500 to-blue-600',
    green: 'from-green-500 to-green-600',
    red: 'from-red-500 to-red-600',
    purple: 'from-purple-500 to-purple-600'
  };

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} rounded-xl p-6 shadow-lg`} data-testid={testId}>
      <div className="flex items-center justify-between mb-4">
        <div className="text-white/80">{icon}</div>
      </div>
      <div className="text-3xl font-bold text-white mb-1">{value}</div>
      <div className="text-white/80 text-sm">{title}</div>
    </div>
  );
};

const AlgorithmCard = ({ algorithm, data }) => {
  const algoNames = {
    token_bucket: 'Token Bucket',
    leaky_bucket: 'Leaky Bucket',
    fixed_window: 'Fixed Window',
    sliding_window: 'Sliding Window'
  };

  return (
    <div className="bg-white/5 rounded-lg p-4 border border-white/10" data-testid={`algo-card-${algorithm}`}>
      <h3 className="text-white font-semibold mb-2">{algoNames[algorithm]}</h3>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between text-purple-200">
          <span>Total:</span>
          <span className="font-semibold">{data.total}</span>
        </div>
        <div className="flex justify-between text-green-300">
          <span>Allowed:</span>
          <span className="font-semibold">{data.allowed}</span>
        </div>
        <div className="flex justify-between text-red-300">
          <span>Blocked:</span>
          <span className="font-semibold">{data.blocked}</span>
        </div>
        <div className="flex justify-between text-blue-300">
          <span>Success:</span>
          <span className="font-semibold">{data.success_rate}%</span>
        </div>
      </div>
    </div>
  );
};

const StatusItem = ({ label, value, isStatus }) => (
  <div className="text-center">
    <div className="text-2xl font-bold text-white mb-1">
      {isStatus ? (
        <span className="px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-sm uppercase">
          {value}
        </span>
      ) : value}
    </div>
    <div className="text-purple-200 text-sm">{label}</div>
  </div>
);

// Admin Panel Component
const AdminPanel = () => {
  const [apiKeys, setApiKeys] = useState([]);
  const [configs, setConfigs] = useState([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [selectedKey, setSelectedKey] = useState("");
  const [algorithm, setAlgorithm] = useState("token_bucket");
  const [maxRequests, setMaxRequests] = useState(100);
  const [windowSeconds, setWindowSeconds] = useState(60);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      const [keysRes, configsRes] = await Promise.all([
        axios.get(`${API}/api-keys`),
        axios.get(`${API}/rate-limit-configs`)
      ]);
      setApiKeys(keysRes.data);
      setConfigs(configsRes.data);
    } catch (error) {
      console.error("Error fetching admin data:", error);
    }
  };

  const createAPIKey = async () => {
    if (!newKeyName.trim()) return;
    try {
      await axios.post(`${API}/api-keys`, { name: newKeyName });
      setNewKeyName("");
      fetchAdminData();
    } catch (error) {
      console.error("Error creating API key:", error);
    }
  };

  const createRateLimitConfig = async () => {
    if (!selectedKey) return;
    try {
      await axios.post(`${API}/rate-limit-configs`, {
        api_key: selectedKey,
        algorithm,
        max_requests: parseInt(maxRequests),
        window_seconds: parseInt(windowSeconds)
      });
      fetchAdminData();
    } catch (error) {
      console.error("Error creating rate limit config:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2" data-testid="admin-panel-title">Admin Panel</h1>
          <p className="text-purple-200">Manage API keys and rate limit configurations</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Create API Key */}
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
            <h2 className="text-2xl font-bold text-white mb-4" data-testid="create-api-key-section">Create API Key</h2>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="API Key Name"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-500"
                data-testid="api-key-name-input"
              />
              <button
                onClick={createAPIKey}
                className="w-full px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-semibold rounded-lg hover:from-purple-600 hover:to-pink-600 transition-all"
                data-testid="create-api-key-button"
              >
                Create API Key
              </button>
            </div>

            <div className="mt-6">
              <h3 className="text-white font-semibold mb-3">Existing API Keys ({apiKeys.length})</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto" data-testid="api-keys-list">
                {apiKeys.map((key) => (
                  <div key={key.id} className="bg-white/5 p-3 rounded-lg border border-white/10">
                    <div className="text-white font-semibold">{key.name}</div>
                    <div className="text-purple-200 text-sm font-mono break-all">{key.api_key}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Configure Rate Limit */}
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20">
            <h2 className="text-2xl font-bold text-white mb-4" data-testid="configure-rate-limit-section">Configure Rate Limit</h2>
            <div className="space-y-4">
              <select
                value={selectedKey}
                onChange={(e) => setSelectedKey(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                data-testid="select-api-key"
              >
                <option value="">Select API Key</option>
                {apiKeys.map((key) => (
                  <option key={key.id} value={key.api_key}>
                    {key.name} ({key.api_key.substring(0, 15)}...)
                  </option>
                ))}
              </select>

              <select
                value={algorithm}
                onChange={(e) => setAlgorithm(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                data-testid="select-algorithm"
              >
                <option value="token_bucket">Token Bucket</option>
                <option value="leaky_bucket">Leaky Bucket</option>
                <option value="fixed_window">Fixed Window</option>
                <option value="sliding_window">Sliding Window</option>
              </select>

              <input
                type="number"
                placeholder="Max Requests"
                value={maxRequests}
                onChange={(e) => setMaxRequests(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-500"
                data-testid="max-requests-input"
              />

              <input
                type="number"
                placeholder="Window (seconds)"
                value={windowSeconds}
                onChange={(e) => setWindowSeconds(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-500"
                data-testid="window-seconds-input"
              />

              <button
                onClick={createRateLimitConfig}
                className="w-full px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-cyan-600 transition-all"
                data-testid="configure-rate-limit-button"
              >
                Configure Rate Limit
              </button>
            </div>

            <div className="mt-6">
              <h3 className="text-white font-semibold mb-3">Active Configurations ({configs.length})</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto" data-testid="rate-limit-configs-list">
                {configs.map((config) => (
                  <div key={config.id} className="bg-white/5 p-3 rounded-lg border border-white/10">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="text-white font-semibold">{config.algorithm.replace('_', ' ')}</div>
                        <div className="text-purple-200 text-sm">{config.max_requests} requests / {config.window_seconds}s</div>
                      </div>
                      <div className="text-purple-300 text-xs">
                        {config.api_key.substring(0, 15)}...
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Load Test Component
const LoadTest = () => {
  const [apiKeys, setApiKeys] = useState([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [rps, setRps] = useState(10);
  const [duration, setDuration] = useState(10);
  const [testResults, setTestResults] = useState(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    fetchAPIKeys();
  }, []);

  const fetchAPIKeys = async () => {
    try {
      const res = await axios.get(`${API}/api-keys`);
      setApiKeys(res.data);
    } catch (error) {
      console.error("Error fetching API keys:", error);
    }
  };

  const runLoadTest = async () => {
    if (!selectedKey) return;
    setTesting(true);
    setTestResults(null);

    try {
      const res = await axios.post(`${API}/load-test`, {
        api_key: selectedKey,
        requests_per_second: parseInt(rps),
        duration_seconds: parseInt(duration),
        endpoint: "/api/protected/test"
      });
      setTestResults(res.data);
    } catch (error) {
      console.error("Error running load test:", error);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2" data-testid="load-test-title">Load Testing</h1>
          <p className="text-purple-200">Test rate limiter performance under load</p>
        </div>

        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 mb-8 border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-4">Configure Test</h2>
          <div className="space-y-4">
            <select
              value={selectedKey}
              onChange={(e) => setSelectedKey(e.target.value)}
              className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              data-testid="load-test-api-key-select"
            >
              <option value="">Select API Key</option>
              {apiKeys.map((key) => (
                <option key={key.id} value={key.api_key}>
                  {key.name} ({key.api_key.substring(0, 15)}...)
                </option>
              ))}
            </select>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-purple-200 mb-2">Requests per Second</label>
                <input
                  type="number"
                  value={rps}
                  onChange={(e) => setRps(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  data-testid="rps-input"
                />
              </div>
              <div>
                <label className="block text-purple-200 mb-2">Duration (seconds)</label>
                <input
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  data-testid="duration-input"
                />
              </div>
            </div>

            <button
              onClick={runLoadTest}
              disabled={testing || !selectedKey}
              className="w-full px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-semibold rounded-lg hover:from-green-600 hover:to-emerald-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="run-load-test-button"
            >
              {testing ? 'Running Test...' : 'Run Load Test'}
            </button>
          </div>
        </div>

        {testResults && (
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20" data-testid="load-test-results">
            <h2 className="text-2xl font-bold text-white mb-4">Test Results</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <ResultCard label="Total Requests" value={testResults.total_requests} />
              <ResultCard label="Allowed" value={testResults.allowed} color="green" />
              <ResultCard label="Blocked" value={testResults.blocked} color="red" />
              <ResultCard label="Success Rate" value={`${testResults.success_rate}%`} color="blue" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white/5 p-4 rounded-lg">
                <div className="text-purple-200 text-sm mb-1">Actual Duration</div>
                <div className="text-white text-xl font-bold">{testResults.actual_duration.toFixed(2)}s</div>
              </div>
              <div className="bg-white/5 p-4 rounded-lg">
                <div className="text-purple-200 text-sm mb-1">Requests/Second</div>
                <div className="text-white text-xl font-bold">{testResults.requests_per_second}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const ResultCard = ({ label, value, color = 'white' }) => {
  const colorClasses = {
    white: 'text-white',
    green: 'text-green-300',
    red: 'text-red-300',
    blue: 'text-blue-300'
  };

  return (
    <div className="bg-white/5 p-4 rounded-lg">
      <div className="text-purple-200 text-sm mb-1">{label}</div>
      <div className={`${colorClasses[color]} text-2xl font-bold`}>{value}</div>
    </div>
  );
};

// Navigation Component
const Navigation = () => {
  const navigate = useNavigate();

  return (
    <div className="fixed top-0 left-0 right-0 bg-slate-900/95 backdrop-blur-lg border-b border-white/10 z-50">
      <div className="max-w-7xl mx-auto px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Shield className="w-8 h-8 text-purple-400" />
            <span className="text-white text-xl font-bold">RateLimiter</span>
          </div>
          <nav className="flex space-x-6">
            <NavLink to="/" icon={<Activity className="w-5 h-5" />} label="Dashboard" />
            <NavLink to="/admin" icon={<Settings className="w-5 h-5" />} label="Admin" />
            <NavLink to="/load-test" icon={<Zap className="w-5 h-5" />} label="Load Test" />
          </nav>
        </div>
      </div>
    </div>
  );
};

const NavLink = ({ to, icon, label }) => (
  <Link
    to={to}
    className="flex items-center space-x-2 px-4 py-2 rounded-lg text-purple-200 hover:bg-white/10 hover:text-white transition-all"
    data-testid={`nav-${label.toLowerCase().replace(' ', '-')}`}
  >
    {icon}
    <span>{label}</span>
  </Link>
);

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Navigation />
        <div className="pt-20">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/load-test" element={<LoadTest />} />
          </Routes>
        </div>
      </BrowserRouter>
    </div>
  );
}

export default App;