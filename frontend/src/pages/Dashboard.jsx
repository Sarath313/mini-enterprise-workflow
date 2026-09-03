import { useEffect, useState } from "react";

import api from "../api/axios";

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await api.get("/dashboard/");

        setStats(response.data);
      } catch (error) {
        console.error("Dashboard error:", error);

        const detail = error.response?.data?.detail;

        setError(
          typeof detail === "string"
            ? detail
            : "Unable to load dashboard data."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />

          <p className="text-sm font-medium text-slate-500">
            Loading dashboard...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <h2 className="font-semibold text-red-800">
            Dashboard unavailable
          </h2>

          <p className="mt-1 text-sm text-red-600">
            {error}
          </p>
        </div>
      </div>
    );
  }

  const overviewCards = [
    {
      title: "Total Tasks",
      value: stats.total_tasks,
      description: "All tasks in the system",
      style: "bg-blue-50 text-blue-700",
    },
    {
      title: "To Do",
      value: stats.todo_tasks,
      description: "Tasks waiting to start",
      style: "bg-slate-100 text-slate-700",
    },
    {
      title: "In Progress",
      value: stats.in_progress_tasks,
      description: "Currently being worked on",
      style: "bg-purple-50 text-purple-700",
    },
    {
      title: "Completed",
      value: stats.done_tasks,
      description: "Successfully completed",
      style: "bg-green-50 text-green-700",
    },
  ];

  const priorityCards = [
    {
      title: "Low Priority",
      value: stats.low_priority_tasks,
      style: "bg-slate-100 text-slate-700",
    },
    {
      title: "Medium Priority",
      value: stats.medium_priority_tasks,
      style: "bg-yellow-50 text-yellow-700",
    },
    {
      title: "High Priority",
      value: stats.high_priority_tasks,
      style: "bg-red-50 text-red-700",
    },
  ];

  const assignmentCards = [
    {
      title: "Assigned Tasks",
      value: stats.assigned_tasks,
      style: "bg-blue-50 text-blue-700",
    },
    {
      title: "Unassigned Tasks",
      value: stats.unassigned_tasks,
      style: "bg-slate-100 text-slate-700",
    },
    {
      title: "Overdue Tasks",
      value: stats.overdue_tasks,
      style: "bg-red-50 text-red-700",
    },
  ];

  const renderCard = (card) => (
    <div
      key={card.title}
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">
            {card.title}
          </p>

          <p className="mt-2 text-3xl font-bold text-slate-900">
            {card.value}
          </p>
        </div>

        <span
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${card.style}`}
        >
          {card.title}
        </span>
      </div>

      {card.description && (
        <p className="mt-3 text-xs text-slate-400">
          {card.description}
        </p>
      )}
    </div>
  );

  return (
    <div className="p-6">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">
          Dashboard
        </h1>

        <p className="mt-2 text-sm text-slate-500">
          Overview of your enterprise workflow and task activity.
        </p>
      </div>

      {/* Overview */}
      <section className="mb-8">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-slate-900">
            Task Overview
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Current status of tasks across the workflow.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {overviewCards.map(renderCard)}
        </div>
      </section>

      {/* Priority */}
      <section className="mb-8">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-slate-900">
            Priority Breakdown
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Tasks grouped by their current priority.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {priorityCards.map(renderCard)}
        </div>
      </section>

      {/* Assignment */}
      <section>
        <div className="mb-4">
          <h2 className="text-lg font-bold text-slate-900">
            Assignment & Attention
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Assignment status and tasks requiring attention.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {assignmentCards.map(renderCard)}
        </div>
      </section>
    </div>
  );
}

export default Dashboard;