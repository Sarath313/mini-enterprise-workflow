import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

function Tasks() {
  const { user } = useAuth();

  const [tasks, setTasks] = useState([]);

  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");

  const [showCreateForm, setShowCreateForm] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [dueDate, setDueDate] = useState("");
  const [assignedTo, setAssignedTo] = useState("");

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchTasks = async () => {
    setLoading(true);
    setError("");

    try {
      const params = {};

      if (statusFilter) {
        params.status = statusFilter;
      }

      if (priorityFilter) {
        params.priority = priorityFilter;
      }

      const response = await api.get("/tasks/", {
        params,
      });

      setTasks(response.data);
    } catch (error) {
      console.error("Tasks error:", error);
      setError("Unable to load tasks.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [statusFilter, priorityFilter]);

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setPriority("medium");
    setDueDate("");
    setAssignedTo("");
  };

  const handleCreateTask = async (event) => {
    event.preventDefault();

    setCreating(true);
    setError("");
    setSuccess("");

    try {
      const taskData = {
        title,
        description: description || null,
        priority,
        due_date: dueDate
          ? `${dueDate}T23:59:59`
          : null,
        assigned_to: assignedTo
          ? Number(assignedTo)
          : null,
      };

      await api.post("/tasks/", taskData);

      setSuccess("Task created successfully.");

      resetForm();
      setShowCreateForm(false);

      await fetchTasks();
    } catch (error) {
      console.error("Create task error:", error);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to create task.");
      }
    } finally {
      setCreating(false);
    }
  };

  const canCreateTask =
    user?.role === "admin" ||
    user?.role === "manager";

  return (
    <div className="p-6">

      {/* Page Header */}
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-center">

        <div>
          <h1 className="text-3xl font-bold text-slate-900">
            Tasks
          </h1>

          <p className="mt-2 text-slate-500">
            Manage and track your workflow tasks
          </p>
        </div>

        {canCreateTask && (
          <button
            type="button"
            onClick={() => {
              setShowCreateForm(true);
              setError("");
              setSuccess("");
            }}
            className="rounded-lg bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-700"
          >
            + Create Task
          </button>
        )}
      </div>

      {/* Success Message */}
      {success && (
        <div className="mb-6 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">
          {success}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Create Task Form */}
      {showCreateForm && (
        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">

          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                Create New Task
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Add a new task to the enterprise workflow
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                setShowCreateForm(false);
                setError("");
              }}
              className="text-sm font-medium text-slate-500 hover:text-slate-900"
            >
              Cancel
            </button>
          </div>

          <form
            onSubmit={handleCreateTask}
            className="space-y-5"
          >

            {/* Title */}
            <div>
              <label
                htmlFor="title"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Title
              </label>

              <input
                id="title"
                type="text"
                value={title}
                onChange={(event) =>
                  setTitle(event.target.value)
                }
                placeholder="Enter task title"
                required
                maxLength={200}
                className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="description"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Description
              </label>

              <textarea
                id="description"
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                placeholder="Describe the task"
                rows={4}
                className="w-full resize-none rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </div>

            {/* Priority + Due Date */}
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">

              <div>
                <label
                  htmlFor="priority"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Priority
                </label>

                <select
                  id="priority"
                  value={priority}
                  onChange={(event) =>
                    setPriority(event.target.value)
                  }
                  className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                >
                  <option value="low">
                    Low
                  </option>

                  <option value="medium">
                    Medium
                  </option>

                  <option value="high">
                    High
                  </option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="dueDate"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Due Date
                </label>

                <input
                  id="dueDate"
                  type="date"
                  value={dueDate}
                  onChange={(event) =>
                    setDueDate(event.target.value)
                  }
                  className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                />
              </div>

            </div>

            {/* Assigned To */}
            <div>
              <label
                htmlFor="assignedTo"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Assign To
              </label>

              <input
                id="assignedTo"
                type="number"
                min="1"
                value={assignedTo}
                onChange={(event) =>
                  setAssignedTo(event.target.value)
                }
                placeholder="Enter employee user ID (optional)"
                className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />

              <p className="mt-2 text-xs text-slate-500">
                Leave empty to create an unassigned task.
              </p>
            </div>

            {/* Buttons */}
            <div className="flex gap-3 pt-2">

              <button
                type="submit"
                disabled={creating}
                className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {creating
                  ? "Creating..."
                  : "Create Task"}
              </button>

              <button
                type="button"
                onClick={() => {
                  resetForm();
                  setShowCreateForm(false);
                  setError("");
                }}
                className="rounded-lg border border-slate-300 px-6 py-3 font-medium text-slate-700 transition hover:bg-slate-100"
              >
                Cancel
              </button>

            </div>

          </form>
        </div>
      )}

      {/* Filters */}
      <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

        <div className="flex flex-col gap-4 md:flex-row md:items-end">

          <div className="w-full md:w-56">
            <label
              htmlFor="status"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Status
            </label>

            <select
              id="status"
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value)
              }
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            >
              <option value="">
                All statuses
              </option>

              <option value="todo">
                To Do
              </option>

              <option value="in_progress">
                In Progress
              </option>

              <option value="done">
                Completed
              </option>
            </select>
          </div>

          <div className="w-full md:w-56">
            <label
              htmlFor="priorityFilter"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Priority
            </label>

            <select
              id="priorityFilter"
              value={priorityFilter}
              onChange={(event) =>
                setPriorityFilter(event.target.value)
              }
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            >
              <option value="">
                All priorities
              </option>

              <option value="low">
                Low
              </option>

              <option value="medium">
                Medium
              </option>

              <option value="high">
                High
              </option>
            </select>
          </div>

          <button
            type="button"
            onClick={() => {
              setStatusFilter("");
              setPriorityFilter("");
            }}
            className="rounded-lg border border-slate-300 px-5 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Clear Filters
          </button>

        </div>
      </div>

      {/* Task List */}
      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm">
          <p className="text-slate-500">
            Loading tasks...
          </p>
        </div>
      ) : tasks.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm">
          <p className="text-slate-500">
            No tasks match the selected filters.
          </p>
        </div>
      ) : (
        <div className="space-y-4">

          {tasks.map((task) => (
            <div
              key={task.id}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md"
            >

              <div className="flex flex-col justify-between gap-4 md:flex-row">

                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    {task.title}
                  </h2>

                  {task.description && (
                    <p className="mt-2 text-sm text-slate-500">
                      {task.description}
                    </p>
                  )}
                </div>

                <div className="flex gap-2">

                  <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium capitalize text-slate-700">
                    {task.status.replace("_", " ")}
                  </span>

                  <span className="rounded-full bg-blue-100 px-3 py-1 text-sm font-medium capitalize text-blue-700">
                    {task.priority}
                  </span>

                </div>

              </div>

              <div className="mt-5 grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 text-sm text-slate-500 md:grid-cols-3">

                <div>
                  <span className="font-medium text-slate-700">
                    Task ID:
                  </span>{" "}
                  #{task.id}
                </div>

                <div>
                  <span className="font-medium text-slate-700">
                    Assigned To:
                  </span>{" "}
                  {task.assigned_to
                    ? `User #${task.assigned_to}`
                    : "Unassigned"}
                </div>

                <div>
                  <span className="font-medium text-slate-700">
                    Due Date:
                  </span>{" "}
                  {task.due_date
                    ? new Date(
                        task.due_date
                      ).toLocaleDateString()
                    : "No due date"}
                </div>

              </div>

            </div>
          ))}

        </div>
      )}

    </div>
  );
}

export default Tasks;