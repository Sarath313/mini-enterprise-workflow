import { useEffect, useState } from "react";
import api from "../api/axios";

function AIInsights() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const response = await api.get("/dashboard/ai-summary");
        setData(response.data);
      } catch (error) {
        console.error("AI insights error:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchInsights();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm">
        Loading AI insights...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm">
        Unable to load insights.
      </div>
    );
  }

  const metrics = [
    ["Total Tasks", data.metrics.total_tasks],
    ["To Do", data.metrics.todo],
    ["In Progress", data.metrics.in_progress],
    ["Review", data.metrics.review],
    ["Completed", data.metrics.done],
    ["High Priority", data.metrics.high_priority],
    ["Pending Approvals", data.metrics.pending_approvals],
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          AI Insights
        </h1>

        <p className="mt-1 text-sm text-slate-500">
          Intelligent workload analysis based on current workflow data.
        </p>
      </div>

      <div className="rounded-xl border border-blue-100 bg-blue-50 p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
          AI Summary
        </p>

        <p className="mt-2 text-lg font-semibold text-slate-900">
          {data.summary}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map(([label, value]) => (
          <div
            key={label}
            className="rounded-xl bg-white p-5 shadow-sm"
          >
            <p className="text-sm text-slate-500">
              {label}
            </p>

            <p className="mt-2 text-3xl font-bold text-slate-900">
              {value}
            </p>
          </div>
        ))}
      </div>

      <div className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">
          Key Insights
        </h2>

        <div className="mt-4 space-y-3">
          {data.insights?.length ? (
            data.insights.map((insight, index) => (
              <div
                key={index}
                className="rounded-lg bg-slate-50 p-4 text-sm text-slate-700"
              >
                • {insight}
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-500">
              No additional insights available.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default AIInsights;