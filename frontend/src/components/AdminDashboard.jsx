import { useEffect, useState } from "react";

const AdminDashboard = () => {
  const [metrics, setMetrics] = useState({
    active_sessions: 0,
    total_messages: 0,
    escalations_count: 0,
    recent_activity: [],
  });
  const [queue, setQueue] = useState([]);
  const [analytics, setAnalytics] = useState({
    escalation_rate: 0,
    total_sessions: 0,
    intent_breakdown: {},
    priority_breakdown: {},
  });
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [queueSearch, setQueueSearch] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("ALL");

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const [metricsRes, queueRes, analyticsRes] = await Promise.all([
          fetch("http://localhost:8000/api/admin/metrics"),
          fetch("http://localhost:8000/api/admin/queue"),
          fetch("http://localhost:8000/api/admin/analytics"),
        ]);

        const [metricsData, queueData, analyticsData] = await Promise.all([
          metricsRes.json(),
          queueRes.json(),
          analyticsRes.json(),
        ]);

        setMetrics(metricsData);
        setQueue(Array.isArray(queueData) ? queueData : []);
        setAnalytics(analyticsData || {});
      } catch (e) {
        console.error("Failed to fetch metrics", e);
      }
    };

    fetchDashboard();
    const interval = setInterval(fetchDashboard, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleUploadKb = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", file);
      formData.append("category", "uploaded");
      const res = await fetch("http://localhost:8000/api/admin/kb/upload", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        throw new Error("KB upload failed");
      }
      event.target.value = "";
    } catch (e) {
      console.error(e);
    } finally {
      setUploading(false);
    }
  };

  const priorityColor = (priority) => {
    switch ((priority || "").toUpperCase()) {
      case "P1":
        return "text-red-700 bg-red-50 border-red-200";
      case "P2":
        return "text-orange-700 bg-orange-50 border-orange-200";
      case "P3":
        return "text-yellow-700 bg-yellow-50 border-yellow-200";
      default:
        return "text-emerald-700 bg-emerald-50 border-emerald-200";
    }
  };

  const filteredQueue = queue.filter((item) => {
    const priority = String(item.priority || "").toUpperCase();
    if (priorityFilter !== "ALL" && priority !== priorityFilter) return false;

    const q = queueSearch.trim().toLowerCase();
    if (!q) return true;
    const haystack = [
      item.session_id,
      item.intent,
      item.bundle,
      item.last_active,
      item.priority,
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(q);
  });

  return (
    <div className="w-full h-full flex flex-col bg-white font-sans overflow-hidden">
      {/* Header Section */}
      <div className="px-6 py-6 sm:px-10 border-b border-[#ececec] flex justify-between items-center bg-[#FDFDFD]">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight">
            ShopEasy Admin Portal
          </h1>
          <p className="text-[13px] text-gray-500 mt-1">
            System Health & Live Intelligence
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-100">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[12px] font-medium text-emerald-700">Live</span>
        </div>
      </div>

      <div className="px-6 pt-4 sm:px-10 flex items-center justify-between gap-3 bg-[#FDFDFD]">
        <div className="text-[13px] text-gray-600">
          Escalation Rate:{" "}
          <span className="font-semibold text-gray-900">
            {analytics.escalation_rate || 0}%
          </span>
        </div>
        <label className="text-[12px] px-3 py-2 rounded-lg border border-zinc-300 bg-white cursor-pointer hover:bg-zinc-50">
          {uploading ? "Uploading KB..." : "Upload KB File"}
          <input
            type="file"
            accept=".txt"
            className="hidden"
            onChange={handleUploadKb}
            disabled={uploading}
          />
        </label>
      </div>

      <div className="px-6 sm:px-10 pt-4 bg-[#FDFDFD] flex items-center gap-2 flex-wrap">
        {[
          { id: "overview", label: "Overview" },
          { id: "queue", label: "Escalation Queue" },
          { id: "analytics", label: "Analytics" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`text-[13px] px-3 py-1.5 rounded-lg border transition-colors ${
              activeTab === tab.id
                ? "bg-zinc-900 text-white border-zinc-900"
                : "bg-white text-zinc-600 border-zinc-300 hover:bg-zinc-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 px-6 py-6 sm:px-10 border-b border-[#ececec]">
        <div className="flex-col gap-1 pr-6 border-r border-[#ececec] hidden md:flex">
          <p className="text-[13px] font-medium text-gray-500">
            Active Sessions
          </p>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold text-gray-900">
              {metrics.active_sessions}
            </span>
            <span className="text-[13px] text-emerald-600">+2%</span>
          </div>
        </div>
        <div className="flex flex-col gap-1 pr-6 md:border-r border-[#ececec]">
          <p className="text-[13px] font-medium text-gray-500">
            Messages Processed
          </p>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold text-gray-900">
              {metrics.total_messages}
            </span>
            <span className="text-[13px] text-gray-400">Total</span>
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-[13px] font-medium text-gray-500">Escalations</p>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold text-red-600">
              {metrics.escalations_count}
            </span>
            <span className="text-[13px] text-red-500">Attention Req.</span>
          </div>
        </div>
      </div>

      {/* Activity + Queue */}
      <div className="flex-1 px-6 pb-6 sm:px-10 py-6 overflow-hidden grid grid-cols-1 xl:grid-cols-2 gap-4 bg-[#FDFDFD]">
        {(activeTab === "overview" || activeTab === "queue") && (
          <div className="xl:col-span-2 bg-white border border-zinc-200 rounded-xl p-3 md:p-4 flex flex-col md:flex-row md:items-center gap-3">
            <input
              type="text"
              value={queueSearch}
              onChange={(e) => setQueueSearch(e.target.value)}
              placeholder="Search queue by session, intent, or issue"
              className="w-full md:flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm"
            />
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="rounded-lg border border-zinc-300 px-3 py-2 text-sm"
            >
              <option value="ALL">All Priorities</option>
              <option value="P1">P1</option>
              <option value="P2">P2</option>
              <option value="P3">P3</option>
            </select>
            <div className="text-xs text-zinc-500">
              Showing {filteredQueue.length} of {queue.length}
            </div>
          </div>
        )}

        {activeTab !== "analytics" && (
          <div className="overflow-hidden flex flex-col">
            <h3 className="text-[15px] font-semibold text-gray-900 mb-4">
              Critical Incident Feed
            </h3>
            <div className="flex-1 overflow-y-auto pr-2 space-y-3 custom-scrollbar">
              {metrics.recent_activity.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 border border-dashed border-gray-200 rounded-xl bg-gray-50/50">
                  <p className="text-[14px] text-gray-500">
                    System operating within normal parameters.
                  </p>
                </div>
              ) : (
                <div className="grid gap-3">
                  {metrics.recent_activity.map((act, i) => (
                    <div
                      key={i}
                      className="bg-white border border-gray-200 p-4 rounded-xl shadow-sm hover:border-gray-300 transition-colors"
                    >
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-[12px] font-mono text-gray-500 bg-gray-50 px-2 py-1 rounded">
                          ID: {act.session_id}
                        </span>
                        <span
                          className={`text-[11px] font-semibold px-2 py-1 rounded border uppercase tracking-wide ${priorityColor(act.priority)}`}
                        >
                          {act.priority || "P3"}
                        </span>
                      </div>
                      <p className="text-[14px] text-gray-700 leading-relaxed">
                        {act.bundle}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab !== "analytics" && (
          <div className="overflow-hidden flex flex-col">
            <h3 className="text-[15px] font-semibold text-gray-900 mb-4">
              Live Escalation Queue
            </h3>
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-3">
              {filteredQueue.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 border border-dashed border-gray-200 rounded-xl bg-gray-50/50">
                  <p className="text-[14px] text-gray-500">
                    No escalated sessions for current filters.
                  </p>
                </div>
              ) : (
                filteredQueue.map((item) => (
                  <div
                    key={item.session_id}
                    className="bg-white border border-gray-200 p-4 rounded-xl shadow-sm"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[12px] font-mono text-gray-600">
                        {item.session_id}
                      </span>
                      <span
                        className={`text-[11px] font-semibold px-2 py-1 rounded border ${priorityColor(item.priority)}`}
                      >
                        {item.priority}
                      </span>
                    </div>
                    <p className="text-[12px] text-zinc-500 mt-1">
                      Intent: {item.intent || "general"}
                    </p>
                    <p className="text-[12px] text-zinc-500 mb-2">
                      Last active: {item.last_active}
                    </p>
                    <p className="text-[13px] text-zinc-700 leading-relaxed">
                      {item.bundle}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab !== "queue" && (
          <div className="xl:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <h4 className="text-[14px] font-semibold mb-2 text-gray-900">
                Intent Breakdown
              </h4>
              <div className="space-y-1 text-[13px] text-gray-700">
                {Object.entries(analytics.intent_breakdown || {}).length ===
                0 ? (
                  <p className="text-gray-500">No data yet</p>
                ) : (
                  Object.entries(analytics.intent_breakdown || {}).map(
                    ([intent, count]) => (
                      <div key={intent} className="flex justify-between">
                        <span>{intent}</span>
                        <span className="font-semibold">{count}</span>
                      </div>
                    ),
                  )
                )}
              </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <h4 className="text-[14px] font-semibold mb-2 text-gray-900">
                Priority Breakdown
              </h4>
              <div className="space-y-1 text-[13px] text-gray-700">
                {Object.entries(analytics.priority_breakdown || {}).length ===
                0 ? (
                  <p className="text-gray-500">No data yet</p>
                ) : (
                  Object.entries(analytics.priority_breakdown || {}).map(
                    ([priority, count]) => (
                      <div key={priority} className="flex justify-between">
                        <span>{priority}</span>
                        <span className="font-semibold">{count}</span>
                      </div>
                    ),
                  )
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
