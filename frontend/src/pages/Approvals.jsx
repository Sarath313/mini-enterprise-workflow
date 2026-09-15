import { useEffect, useState } from "react";

import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

function Approvals() {
  const { user } = useAuth();

  const [tasks, setTasks] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [selectedApproval, setSelectedApproval] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);

  const [action, setAction] = useState("");
  const [comment, setComment] = useState("");

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [showActionModal, setShowActionModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);

  const isManager = user?.role === "manager";
  const isAdmin = user?.role === "admin";
  const canProcessApprovals = isManager || isAdmin;

  const loadApprovals = async () => {
    try {
      setLoading(true);
      setError("");

      const tasksResponse = await api.get("/tasks/", {
        params: {
          limit: 100,
        },
      });

      const taskList = tasksResponse.data || [];

      setTasks(taskList);

      const approvalResults = await Promise.all(
        taskList.map(async (task) => {
          try {
            const response = await api.get(
              `/tasks/${task.id}/approvals`
            );

            return (response.data || []).map((approval) => ({
              ...approval,
              task,
            }));
          } catch (err) {
            console.error(
              `Failed to load approvals for task ${task.id}`,
              err
            );

            return [];
          }
        })
      );

      const flattenedApprovals = approvalResults.flat();

      setApprovals(flattenedApprovals);
    } catch (err) {
      console.error(err);

      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : "Unable to load approval information."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const clearMessages = () => {
    setError("");
    setSuccess("");
  };

  const openActionModal = (approval, task, selectedAction) => {
    clearMessages();

    setSelectedApproval(approval);
    setSelectedTask(task);
    setAction(selectedAction);
    setComment("");

    setShowActionModal(true);
  };

  const closeActionModal = () => {
    if (actionLoading) {
      return;
    }

    setShowActionModal(false);
    setSelectedApproval(null);
    setSelectedTask(null);
    setAction("");
    setComment("");
  };

  const processApproval = async () => {
    if (!selectedApproval || !selectedTask || !action) {
      return;
    }

    if (action === "rejected" && !comment.trim()) {
      setError("A comment is required when rejecting an approval.");
      return;
    }

    try {
      setActionLoading(true);
      clearMessages();

      await api.patch(
        `/tasks/${selectedTask.id}/approvals/${selectedApproval.id}`,
        {
          action,
          comment: comment.trim() || null,
        }
      );

      setSuccess(
        `Approval ${
          action === "approved"
            ? "approved"
            : action === "rejected"
              ? "rejected"
              : "placed on hold"
        } successfully.`
      );

      closeActionModal();

      await loadApprovals();
    } catch (err) {
      console.error(err);

      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : "Unable to process the approval."
      );
    } finally {
      setActionLoading(false);
    }
  };

  const submitTaskForApproval = async (task) => {
    try {
      clearMessages();

      await api.post(`/tasks/${task.id}/approvals`);

      setSuccess(
        `Task "${task.title}" was submitted for manager approval.`
      );

      await loadApprovals();
    } catch (err) {
      console.error(err);

      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : "Unable to submit the task for approval."
      );
    }
  };

  const openHistory = async (approval, task) => {
    try {
      setSelectedApproval(approval);
      setSelectedTask(task);
      setHistory([]);
      setShowHistoryModal(true);
      setHistoryLoading(true);

      const response = await api.get(
        `/tasks/${task.id}/approvals/history`
      );

      setHistory(response.data || []);
    } catch (err) {
      console.error(err);

      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : "Unable to load approval history."
      );

      setShowHistoryModal(false);
    } finally {
      setHistoryLoading(false);
    }
  };

  const closeHistory = () => {
    setShowHistoryModal(false);
    setSelectedApproval(null);
    setSelectedTask(null);
    setHistory([]);
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case "pending":
        return "Pending";

      case "approved":
        return "Approved";

      case "rejected":
        return "Rejected";

      case "hold":
        return "On Hold";

      default:
        return status || "Unknown";
    }
  };

  const getStatusClasses = (status) => {
    switch (status) {
      case "pending":
        return "bg-amber-100 text-amber-800";

      case "approved":
        return "bg-emerald-100 text-emerald-800";

      case "rejected":
        return "bg-red-100 text-red-800";

      case "hold":
        return "bg-blue-100 text-blue-800";

      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  const getLevelLabel = (level) => {
    if (level === "manager") {
      return "Manager Approval";
    }

    if (level === "admin") {
      return "Admin Approval";
    }

    return level || "Approval";
  };

  const formatDate = (value) => {
    if (!value) {
      return "—";
    }

    return new Date(value).toLocaleString();
  };

  const pendingApprovals = approvals.filter(
    (approval) =>
      approval.status === "pending" ||
      approval.status === "hold"
  );

  const approvedApprovals = approvals.filter(
    (approval) => approval.status === "approved"
  );

  const rejectedApprovals = approvals.filter(
    (approval) => approval.status === "rejected"
  );

  const reviewTasks = tasks.filter(
    (task) => task.status === "review"
  );

  const pendingApprovalTaskIds = new Set(
    approvals
      .filter((approval) => approval.status === "pending")
      .map((approval) => approval.task_id)
  );

  if (loading) {
    return (
      <div className="min-h-full bg-slate-100 p-6">
        <div className="flex min-h-[400px] items-center justify-center">
          <p className="text-sm font-medium text-slate-500">
            Loading approvals...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-slate-100 p-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">
              Approval Workflow
            </h1>

            <p className="mt-2 text-slate-500">
              Submit, review and track task approval requests.
            </p>
          </div>

          <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            <span className="font-semibold">
              Workflow:
            </span>{" "}
            Employee → Manager → Admin
          </div>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm font-medium text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm font-medium text-emerald-700">
            {success}
          </div>
        )}

        {/* Summary Cards */}
        <div className="mb-8 grid gap-5 md:grid-cols-3">
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
            <p className="text-sm font-semibold text-amber-700">
              Pending / On Hold
            </p>

            <p className="mt-3 text-3xl font-bold text-amber-900">
              {pendingApprovals.length}
            </p>

            <p className="mt-2 text-sm text-amber-700">
              Awaiting approval action
            </p>
          </div>

          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 shadow-sm">
            <p className="text-sm font-semibold text-emerald-700">
              Approved
            </p>

            <p className="mt-3 text-3xl font-bold text-emerald-900">
              {approvedApprovals.length}
            </p>

            <p className="mt-2 text-sm text-emerald-700">
              Successfully approved
            </p>
          </div>

          <div className="rounded-2xl border border-red-200 bg-red-50 p-6 shadow-sm">
            <p className="text-sm font-semibold text-red-700">
              Rejected
            </p>

            <p className="mt-3 text-3xl font-bold text-red-900">
              {rejectedApprovals.length}
            </p>

            <p className="mt-2 text-sm text-red-700">
              Returned for changes
            </p>
          </div>
        </div>

        {/* Tasks Ready for Approval */}
        <div className="mb-8 rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-6 py-5">
            <h2 className="text-xl font-bold text-slate-900">
              Tasks in Review
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Tasks in the Review stage can be submitted for approval.
            </p>
          </div>

          {reviewTasks.length === 0 ? (
            <div className="px-6 py-10 text-center">
              <p className="text-sm text-slate-500">
                No tasks are currently in Review.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {reviewTasks.map((task) => {
                const hasPendingApproval =
                  pendingApprovalTaskIds.has(task.id);

                return (
                  <div
                    key={task.id}
                    className="flex flex-col gap-4 px-6 py-5 lg:flex-row lg:items-center lg:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="font-semibold text-slate-900">
                          {task.title}
                        </h3>

                        <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-700">
                          REVIEW
                        </span>

                        {hasPendingApproval && (
                          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                            Approval Pending
                          </span>
                        )}
                      </div>

                      <p className="mt-2 text-sm text-slate-500">
                        Task #{task.id}
                        {task.assigned_to
                          ? ` • Assigned to user ${task.assigned_to}`
                          : " • Unassigned"}
                      </p>
                    </div>

                    {!hasPendingApproval && (
                      <button
                        type="button"
                        onClick={() =>
                          submitTaskForApproval(task)
                        }
                        className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
                      >
                        Submit for Approval
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Approval Records */}
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-6 py-5">
            <h2 className="text-xl font-bold text-slate-900">
              Approval Records
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Complete approval activity for tasks you can access.
            </p>
          </div>

          {approvals.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-slate-500">
                No approval records found.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {approvals.map((approval) => {
                const task = approval.task;

                const canAct =
                  canProcessApprovals &&
                  approval.status === "pending" &&
                  approval.approver_id === user?.id;

                return (
                  <div
                    key={approval.id}
                    className="px-6 py-6"
                  >
                    <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-3">
                          <h3 className="text-lg font-semibold text-slate-900">
                            {task?.title ||
                              `Task #${approval.task_id}`}
                          </h3>

                          <span
                            className={`rounded-full px-3 py-1 text-xs font-semibold ${getStatusClasses(
                              approval.status
                            )}`}
                          >
                            {getStatusLabel(
                              approval.status
                            )}
                          </span>

                          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                            {getLevelLabel(
                              approval.level
                            )}
                          </span>
                        </div>

                        <div className="mt-3 grid gap-2 text-sm text-slate-500 sm:grid-cols-2 lg:grid-cols-4">
                          <p>
                            <span className="font-semibold text-slate-700">
                              Approval:
                            </span>{" "}
                            #{approval.id}
                          </p>

                          <p>
                            <span className="font-semibold text-slate-700">
                              Task:
                            </span>{" "}
                            #{approval.task_id}
                          </p>

                          <p>
                            <span className="font-semibold text-slate-700">
                              Requested by:
                            </span>{" "}
                            User #{approval.requested_by}
                          </p>

                          <p>
                            <span className="font-semibold text-slate-700">
                              Approver:
                            </span>{" "}
                            User #{approval.approver_id}
                          </p>
                        </div>

                        {approval.comment && (
                          <div className="mt-4 rounded-lg bg-slate-50 px-4 py-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                              Comment
                            </p>

                            <p className="mt-1 text-sm text-slate-700">
                              {approval.comment}
                            </p>
                          </div>
                        )}

                        <p className="mt-3 text-xs text-slate-400">
                          Created{" "}
                          {formatDate(
                            approval.created_at
                          )}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {canAct && (
                          <>
                            <button
                              type="button"
                              onClick={() =>
                                openActionModal(
                                  approval,
                                  task,
                                  "approved"
                                )
                              }
                              className="rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700"
                            >
                              Approve
                            </button>

                            <button
                              type="button"
                              onClick={() =>
                                openActionModal(
                                  approval,
                                  task,
                                  "hold"
                                )
                              }
                              className="rounded-lg bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-amber-600"
                            >
                              Hold
                            </button>

                            <button
                              type="button"
                              onClick={() =>
                                openActionModal(
                                  approval,
                                  task,
                                  "rejected"
                                )
                              }
                              className="rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-700"
                            >
                              Reject
                            </button>
                          </>
                        )}

                        <button
                          type="button"
                          onClick={() =>
                            openHistory(approval, task)
                          }
                          className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                        >
                          History
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Action Modal */}
      {showActionModal && selectedApproval && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl">
            <div className="border-b border-slate-200 px-6 py-5">
              <h2 className="text-xl font-bold text-slate-900">
                {action === "approved"
                  ? "Approve Request"
                  : action === "rejected"
                    ? "Reject Request"
                    : "Put Request on Hold"}
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Task #
                {selectedApproval.task_id}
              </p>
            </div>

            <div className="space-y-5 px-6 py-6">
              <div>
                <label
                  htmlFor="approval-comment"
                  className="mb-2 block text-sm font-semibold text-slate-700"
                >
                  Comment{" "}
                  {action === "rejected" && (
                    <span className="text-red-600">
                      *
                    </span>
                  )}
                </label>

                <textarea
                  id="approval-comment"
                  rows="5"
                  value={comment}
                  onChange={(event) =>
                    setComment(event.target.value)
                  }
                  placeholder={
                    action === "rejected"
                      ? "Explain why the approval is being rejected..."
                      : "Add an optional comment..."
                  }
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>

              {action === "rejected" && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  A meaningful rejection comment is required.
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 border-t border-slate-200 px-6 py-5">
              <button
                type="button"
                onClick={closeActionModal}
                disabled={actionLoading}
                className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={processApproval}
                disabled={actionLoading}
                className={`rounded-lg px-5 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 ${
                  action === "approved"
                    ? "bg-emerald-600 hover:bg-emerald-700"
                    : action === "rejected"
                      ? "bg-red-600 hover:bg-red-700"
                      : "bg-amber-500 hover:bg-amber-600"
                }`}
              >
                {actionLoading
                  ? "Processing..."
                  : action === "approved"
                    ? "Approve"
                    : action === "rejected"
                      ? "Reject"
                      : "Put on Hold"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Modal */}
      {showHistoryModal && selectedApproval && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
          <div className="max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
              <div>
                <h2 className="text-xl font-bold text-slate-900">
                  Approval History
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  Task #{selectedApproval.task_id} • Approval #
                  {selectedApproval.id}
                </p>
              </div>

              <button
                type="button"
                onClick={closeHistory}
                className="rounded-lg px-3 py-2 text-xl text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              >
                ×
              </button>
            </div>

            <div className="max-h-[65vh] overflow-y-auto px-6 py-6">
              {historyLoading ? (
                <div className="py-10 text-center">
                  <p className="text-sm text-slate-500">
                    Loading history...
                  </p>
                </div>
              ) : history.length === 0 ? (
                <div className="py-10 text-center">
                  <p className="text-sm text-slate-500">
                    No history found.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {history.map((item) => (
                    <div
                      key={item.id}
                      className="relative rounded-xl border border-slate-200 bg-slate-50 p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="font-semibold capitalize text-slate-900">
                            {item.action}
                          </p>

                          <p className="mt-1 text-xs text-slate-500">
                            User #{item.action_by}
                          </p>
                        </div>

                        <p className="text-xs text-slate-400">
                          {formatDate(item.created_at)}
                        </p>
                      </div>

                      {item.comment && (
                        <div className="mt-3 rounded-lg bg-white px-3 py-2">
                          <p className="text-sm text-slate-700">
                            {item.comment}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="border-t border-slate-200 px-6 py-5 text-right">
              <button
                type="button"
                onClick={closeHistory}
                className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Approvals;