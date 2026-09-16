import { useEffect, useState } from "react";

import api from "../api/axios";

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [approvalStats, setApprovalStats] = useState({
    pending: 0,
    approved: 0,
    rejected: 0,
    onHold: 0,
  });

  const [workflowStats, setWorkflowStats] = useState({
    review: 0,
    todo: 0,
    inProgress: 0,
    done: 0,
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoading(true);
        setError("");

        const [dashboardResponse, tasksResponse] =
          await Promise.all([
            api.get("/dashboard/"),
            api.get("/tasks/", {
              params: {
                limit: 100,
              },
            }),
          ]);

        setStats(dashboardResponse.data);

        const tasks = tasksResponse.data || [];

        const workflow = {
          review: 0,
          todo: 0,
          inProgress: 0,
          done: 0,
        };

        tasks.forEach((task) => {
          if (task.status === "todo") {
            workflow.todo += 1;
          } else if (task.status === "in_progress") {
            workflow.inProgress += 1;
          } else if (task.status === "review") {
            workflow.review += 1;
          } else if (task.status === "done") {
            workflow.done += 1;
          }
        });

        setWorkflowStats(workflow);

        const approvalResponses = await Promise.all(
          tasks.map(async (task) => {
            try {
              const response = await api.get(
                `/tasks/${task.id}/approvals`
              );

              return response.data || [];
            } catch (approvalError) {
              console.error(
                `Unable to load approvals for task ${task.id}:`,
                approvalError
              );

              return [];
            }
          })
        );

        const allApprovals = approvalResponses.flat();

        const approvalSummary = {
          pending: 0,
          approved: 0,
          rejected: 0,
          onHold: 0,
        };

        allApprovals.forEach((approval) => {
          if (approval.status === "pending") {
            approvalSummary.pending += 1;
          } else if (approval.status === "approved") {
            approvalSummary.approved += 1;
          } else if (approval.status === "rejected") {
            approvalSummary.rejected += 1;
          } else if (approval.status === "hold") {
            approvalSummary.onHold += 1;
          }
        });

        setApprovalStats(approvalSummary);
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

  const workflowCards = [
    {
      title: "To Do",
      value: workflowStats.todo,
      description: "Tasks waiting to begin",
      style: "bg-slate-100 text-slate-700",
    },
    {
      title: "In Progress",
      value: workflowStats.inProgress,
      description: "Tasks currently being worked on",
      style: "bg-purple-50 text-purple-700",
    },
    {
      title: "In Review",
      value: workflowStats.review,
      description: "Tasks waiting for approval",
      style: "bg-indigo-50 text-indigo-700",
    },
    {
      title: "Done",
      value: workflowStats.done,
      description: "Tasks that completed the workflow",
      style: "bg-green-50 text-green-700",
    },
  ];

  const approvalCards = [
    {
      title: "Pending Approval",
      value: approvalStats.pending,
      description: "Awaiting manager or admin action",
      style: "bg-amber-50 text-amber-700",
    },
    {
      title: "On Hold",
      value: approvalStats.onHold,
      description: "Approval requests temporarily held",
      style: "bg-blue-50 text-blue-700",
    },
    {
      title: "Approved",
      value: approvalStats.approved,
      description: "Approval records completed successfully",
      style: "bg-green-50 text-green-700",
    },
    {
      title: "Rejected",
      value: approvalStats.rejected,
      description: "Requests returned for changes",
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
          Overview of your enterprise workflow, tasks and
          approvals.
        </p>
      </div>

      {/* Task Overview */}
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

      {/* Workflow */}
      <section className="mb-8">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-slate-900">
            Workflow Progress
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Distribution of tasks across the workflow lifecycle.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {workflowCards.map(renderCard)}
        </div>
      </section>

      {/* Approval Insights */}
      <section className="mb-8">
        <div className="mb-4">
          <h2 className="text-lg font-bold text-slate-900">
            Approval Insights
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Current approval activity across accessible tasks.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {approvalCards.map(renderCard)}
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