import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

function Activity() {
  const { user } = useAuth();

  const [tasks, setTasks] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [activities, setActivities] = useState([]);

  const [loadingTasks, setLoadingTasks] = useState(true);
  const [loadingActivities, setLoadingActivities] = useState(false);

  const [error, setError] = useState("");

  useEffect(() => {
    fetchTasks();
  }, []);

  useEffect(() => {
    if (!selectedTaskId) {
      setActivities([]);
      return;
    }

    fetchActivities(selectedTaskId);
  }, [selectedTaskId]);

  const fetchTasks = async () => {
    try {
      setLoadingTasks(true);
      setError("");

      const response = await api.get("/tasks/", {
        params: {
          limit: 100,
        },
      });

      const taskList = response.data;

      setTasks(taskList);

      if (taskList.length > 0) {
        setSelectedTaskId(String(taskList[0].id));
      }
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        typeof detail === "string"
          ? detail
          : "Failed to load tasks."
      );
    } finally {
      setLoadingTasks(false);
    }
  };

  const fetchActivities = async (taskId) => {
    try {
      setLoadingActivities(true);
      setError("");

      const response = await api.get(
        `/tasks/${taskId}/activities`
      );

      setActivities(response.data);
    } catch (err) {
      const detail = err.response?.data?.detail;

      setActivities([]);

      setError(
        typeof detail === "string"
          ? detail
          : "Failed to load activity history."
      );
    } finally {
      setLoadingActivities(false);
    }
  };

  const formatAction = (action) => {
    switch (action) {
      case "created":
        return "Task Created";

      case "assigned":
        return "Task Assigned";

      case "status_changed":
        return "Status Changed";

      case "updated":
        return "Task Updated";

      case "deleted":
        return "Task Deleted";

      default:
        return action
          .replaceAll("_", " ")
          .replace(/\b\w/g, (letter) =>
            letter.toUpperCase()
          );
    }
  };

  const getActionStyle = (action) => {
    switch (action) {
      case "created":
        return "bg-green-100 text-green-700";

      case "assigned":
        return "bg-blue-100 text-blue-700";

      case "status_changed":
        return "bg-purple-100 text-purple-700";

      case "updated":
        return "bg-yellow-100 text-yellow-700";

      case "deleted":
        return "bg-red-100 text-red-700";

      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) {
      return "-";
    }

    return new Date(dateString).toLocaleString();
  };

  const selectedTask = tasks.find(
    (task) => String(task.id) === String(selectedTaskId)
  );

  return (
    <div className="p-6">
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
          Activity
        </h1>

        <p className="mt-1 text-sm text-slate-500">
          View the audit history of your tasks.
        </p>
      </div>

      {/* User Information */}
      {user && (
        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">
            Logged in as
          </p>

          <p className="mt-1 font-semibold text-slate-900">
            {user.name}
          </p>

          <p className="text-sm capitalize text-slate-500">
            {user.role}
          </p>
        </div>
      )}

      {/* Task Selector */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <label
          htmlFor="task"
          className="mb-2 block text-sm font-semibold text-slate-700"
        >
          Select Task
        </label>

        {loadingTasks ? (
          <p className="text-sm text-slate-500">
            Loading tasks...
          </p>
        ) : tasks.length === 0 ? (
          <p className="text-sm text-slate-500">
            No tasks available.
          </p>
        ) : (
          <select
            id="task"
            value={selectedTaskId}
            onChange={(event) =>
              setSelectedTaskId(event.target.value)
            }
            className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          >
            {tasks.map((task) => (
              <option
                key={task.id}
                value={task.id}
              >
                #{task.id} - {task.title}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Selected Task */}
      {selectedTask && (
        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Selected Task
              </p>

              <h2 className="mt-1 text-xl font-bold text-slate-900">
                {selectedTask.title}
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Task #{selectedTask.id}
              </p>
            </div>

            <div className="flex gap-3">
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold capitalize text-slate-700">
                {selectedTask.status.replaceAll("_", " ")}
              </span>

              <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold capitalize text-blue-700">
                {selectedTask.priority}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Activity History */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-6 py-5">
          <h2 className="text-lg font-bold text-slate-900">
            Activity History
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            All recorded actions for the selected task.
          </p>
        </div>

        {loadingActivities ? (
          <div className="p-8 text-center">
            <p className="text-sm text-slate-500">
              Loading activity history...
            </p>
          </div>
        ) : activities.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm font-medium text-slate-600">
              No activity recorded.
            </p>

            <p className="mt-1 text-xs text-slate-400">
              Activity will appear here when actions are performed
              on this task.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {activities.map((activity) => (
              <div
                key={activity.id}
                className="p-6 transition hover:bg-slate-50"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="flex min-w-0 gap-4">
                    {/* Timeline indicator */}
                    <div className="flex flex-col items-center">
                      <div className="h-3 w-3 rounded-full bg-blue-600 ring-4 ring-blue-100" />

                      {activity.id !==
                        activities[activities.length - 1].id && (
                        <div className="mt-2 min-h-8 w-px bg-slate-200" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold ${getActionStyle(
                            activity.action
                          )}`}
                        >
                          {formatAction(activity.action)}
                        </span>

                        <span className="text-xs text-slate-400">
                          Activity #{activity.id}
                        </span>
                      </div>

                      <p className="mt-3 text-sm font-medium text-slate-800">
                        {activity.details ||
                          "No additional details provided."}
                      </p>

                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                        <span>
                          By:{" "}
                          <span className="font-medium text-slate-700">
                            {activity.user_email}
                          </span>
                        </span>

                        <span>
                          {formatDate(activity.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Activity;