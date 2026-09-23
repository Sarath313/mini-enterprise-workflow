import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

function Approvals() {
  const { user } = useAuth();

  const [approvals, setApprovals] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);

  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [comment, setComment] = useState("");

  const fetchApprovals = async () => {
    try {
      setLoading(true);

      const response = await api.get("/approvals/history");
      setApprovals(response.data || []);
    } catch (error) {
      console.error("Approvals error:", error);
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await api.get("/tasks/");
      setTasks(response.data || []);
    } catch (error) {
      console.error("Tasks error:", error);
      setTasks([]);
    }
  };

  useEffect(() => {
    fetchApprovals();
    fetchTasks();
  }, []);

  const createApproval = async () => {
    if (!selectedTaskId) {
      alert("Please select a task.");
      return;
    }

    try {
      setProcessingId("create");

      await api.post(`/approvals/${selectedTaskId}/approvals`, {
        comment: comment || null,
      });

      setSelectedTaskId("");
      setComment("");

      await fetchApprovals();

      alert("Approval request created successfully.");
    } catch (error) {
      console.error("Create approval error:", error);

      const message =
        error.response?.data?.detail ||
        "Unable to create approval request.";

      alert(message);
    } finally {
      setProcessingId(null);
    }
  };

  const processApproval = async (approvalId, taskId, status) => {
    try {
      setProcessingId(approvalId);

      await api.patch(
        `/approvals/${taskId}/approvals/${approvalId}`,
        {
          status,
          comment: comment || null,
        }
      );

      setComment("");

      await fetchApprovals();

      alert(
        status === "approved"
          ? "Approval processed successfully."
          : "Approval rejected."
      );
    } catch (error) {
      console.error("Process approval error:", error);

      const message =
        error.response?.data?.detail ||
        "Unable to process approval.";

      alert(message);
    } finally {
      setProcessingId(null);
    }
  };

  const getStatusClass = (status) => {
    switch (status) {
      case "approved":
        return "bg-green-100 text-green-700";

      case "rejected":
        return "bg-red-100 text-red-700";

      case "pending":
        return "bg-yellow-100 text-yellow-700";

      case "escalated":
        return "bg-purple-100 text-purple-700";

      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  const getTaskTitle = (taskId) => {
    const task = tasks.find((item) => item.id === taskId);
    return task?.title || `Task #${taskId}`;
  };

  const formatDate = (date) => {
    if (!date) return "-";

    return new Date(date).toLocaleString();
  };

  const canProcessApprovals =
    user?.role === "admin" || user?.role === "manager";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Approvals
        </h1>

        <p className="mt-1 text-sm text-slate-500">
          Manage task approval requests and review their history.
        </p>
      </div>

      {/* Create Approval */}
      {canProcessApprovals && (
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            Request Approval
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Select a task to send it through the approval workflow.
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Task
              </label>

              <select
                value={selectedTaskId}
                onChange={(e) => setSelectedTaskId(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                <option value="">Select a task</option>

                {tasks.map((task) => (
                  <option key={task.id} value={task.id}>
                    #{task.id} - {task.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Comment
              </label>

              <input
                type="text"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Optional comment"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>
          </div>

          <button
            onClick={createApproval}
            disabled={processingId === "create"}
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {processingId === "create"
              ? "Creating..."
              : "Request Approval"}
          </button>
        </div>
      )}

      {/* Approval History */}
      <div className="rounded-xl bg-white shadow-sm">
        <div className="border-b border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-900">
            Approval History
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Track pending, approved, rejected, and escalated requests.
          </p>
        </div>

        {loading ? (
          <div className="p-6 text-sm text-slate-500">
            Loading approvals...
          </div>
        ) : approvals.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-500">
              No approval requests found.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-200">
            {approvals.map((approval) => (
              <div
                key={approval.id}
                className="p-6 transition hover:bg-slate-50"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  {/* Approval Information */}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="font-semibold text-slate-900">
                        {getTaskTitle(approval.task_id)}
                      </h3>

                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${getStatusClass(
                          approval.status
                        )}`}
                      >
                        {approval.status}
                      </span>
                    </div>

                    <div className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
                      <p>
                        <span className="font-medium text-slate-700">
                          Approval ID:
                        </span>{" "}
                        #{approval.id}
                      </p>

                      <p>
                        <span className="font-medium text-slate-700">
                          Task ID:
                        </span>{" "}
                        #{approval.task_id}
                      </p>

                      {approval.requested_by && (
                        <p>
                          <span className="font-medium text-slate-700">
                            Requested By:
                          </span>{" "}
                          {approval.requested_by}
                        </p>
                      )}

                      {approval.approver_id && (
                        <p>
                          <span className="font-medium text-slate-700">
                            Approver:
                          </span>{" "}
                          {approval.approver_id}
                        </p>
                      )}

                      <p>
                        <span className="font-medium text-slate-700">
                          Created:
                        </span>{" "}
                        {formatDate(approval.created_at)}
                      </p>

                      {approval.processed_at && (
                        <p>
                          <span className="font-medium text-slate-700">
                            Processed:
                          </span>{" "}
                          {formatDate(approval.processed_at)}
                        </p>
                      )}
                    </div>

                    {approval.comment && (
                      <div className="mt-4 rounded-lg bg-slate-50 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Comment
                        </p>

                        <p className="mt-1 text-sm text-slate-700">
                          {approval.comment}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  {canProcessApprovals &&
                    approval.status === "pending" && (
                      <div className="flex shrink-0 flex-wrap gap-2">
                        <button
                          onClick={() =>
                            processApproval(
                              approval.id,
                              approval.task_id,
                              "approved"
                            )
                          }
                          disabled={processingId === approval.id}
                          className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {processingId === approval.id
                            ? "Processing..."
                            : "Approve"}
                        </button>

                        <button
                          onClick={() =>
                            processApproval(
                              approval.id,
                              approval.task_id,
                              "rejected"
                            )
                          }
                          disabled={processingId === approval.id}
                          className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Approvals;