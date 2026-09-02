import { useEffect, useState } from "react";
import api from "../api/axios";

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const response = await api.get("/dashboard/");
        setStats(response.data);
      } catch (error) {
        console.error("Dashboard error:", error);
        setError("Unable to load dashboard data.");
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
        <p className="text-lg text-slate-500">
          Loading dashboard...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="m-6 rounded-lg bg-red-50 p-4 text-red-700">
        {error}
      </div>
    );
  }

  const cards = [
    {
      title: "Total Tasks",
      value: stats.total_tasks,
    },
    {
      title: "To Do",
      value: stats.todo_tasks,
    },
    {
      title: "In Progress",
      value: stats.in_progress_tasks,
    },
    {
      title: "Completed",
      value: stats.done_tasks,
    },
    {
      title: "Low Priority",
      value: stats.low_priority_tasks,
    },
    {
      title: "Medium Priority",
      value: stats.medium_priority_tasks,
    },
    {
      title: "High Priority",
      value: stats.high_priority_tasks,
    },
    {
      title: "Assigned Tasks",
      value: stats.assigned_tasks,
    },
    {
      title: "Unassigned Tasks",
      value: stats.unassigned_tasks,
    },
    {
      title: "Overdue Tasks",
      value: stats.overdue_tasks,
    },
  ];

  return (
    <div className="p-6">
      {/* Page heading */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">
          Dashboard
        </h1>

        <p className="mt-2 text-slate-500">
          Overview of your enterprise workflow
        </p>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card) => (
          <div
            key={card.title}
            className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md"
          >
            <p className="text-sm font-medium text-slate-500">
              {card.title}
            </p>

            <p className="mt-3 text-3xl font-bold text-slate-900">
              {card.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;