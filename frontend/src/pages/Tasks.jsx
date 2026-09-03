import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

function Tasks() {
  const { user } = useAuth();

  const [tasks, setTasks] = useState([]);

  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingTask, setEditingTask] = useState(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [status, setStatus] = useState("todo");
  const [dueDate, setDueDate] = useState("");
  const [assignedTo, setAssignedTo] = useState("");

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [deletingTaskId, setDeletingTaskId] = useState(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const canCreateTask =
    user?.role === "admin" ||
    user?.role === "manager";

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
    setStatus("todo");
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

  const openEditForm = (task) => {
    setEditingTask(task);

    setTitle(task.title);
    setDescription(task.description || "");
    setPriority(task.priority);
    setStatus(task.status);

    if (task.due_date) {
      setDueDate(task.due_date.substring(0, 10));
    } else {
      setDueDate("");
    }

    setAssignedTo(
      task.assigned_to
        ? String(task.assigned_to)
        : ""
    );

    setError("");
    setSuccess("");
  };

  const closeEditForm = () => {
    setEditingTask(null);
    resetForm();
    setError("");
  };

  const handleUpdateTask = async (event) => {
    event.preventDefault();

    if (!editingTask) {
      return;
    }

    setUpdating(true);
    setError("");
    setSuccess("");

    try {
      const taskData = {
        title,
        description: description || null,
        status,
        priority,
        due_date: dueDate
          ? `${dueDate}T23:59:59`
          : null,
        assigned_to: assignedTo
          ? Number(assignedTo)
          : null,
      };

      await api.put(
        `/tasks/${editingTask.id}`,
        taskData
      );

      setSuccess("Task updated successfully.");

      closeEditForm();

      await fetchTasks();
    } catch (error) {
      console.error("Update task error:", error);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to update task.");
      }
    } finally {
      setUpdating(false);
    }
  };

  const handleDeleteTask = async (taskId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this task?"
    );

    if (!confirmed) {
      return;
    }

    setDeletingTaskId(taskId);
    setError("");
    setSuccess("");

    try {
      await api.delete(`/tasks/${taskId}`);

      setSuccess("Task deleted successfully.");

      await fetchTasks();
    } catch (error) {
      console.error("Delete task error:", error);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to delete task.");
      }
    } finally {
      setDeletingTaskId(null);
    }
  };

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
              setEditingTask(null);
              resetForm();
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
                resetForm();
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
                htmlFor="create-title"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Title
              </label>

              <input
                id="create-title"
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
                htmlFor="create-description"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Description
              </label>

              <textarea
                id="create-description"
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
                  htmlFor="create-priority"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Priority
                </label>

                <select
                  id="create-priority"
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
                  htmlFor="create-due-date"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Due Date
                </label>

                <input
                  id="create-due-date"
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
                htmlFor="create-assigned-to"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Assign To
              </label>

              <input
                id="create-assigned-to"
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

      {/* Edit Task Form */}
      {editingTask && (
        <div className="mb-6 rounded-2xl border border-blue-200 bg-white p-6 shadow-sm">

          <div className="mb-6 flex items-center justify-between">

            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                Edit Task
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Updating Task #{editingTask.id}
              </p>
            </div>

            <button
              type="button"
              onClick={closeEditForm}
              className="text-sm font-medium text-slate-500 hover:text-slate-900"
            >
              Cancel
            </button>

          </div>

          <form
            onSubmit={handleUpdateTask}
            className="space-y-5"
          >

            {/* Title */}
            <div>
              <label
                htmlFor="edit-title"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Title
              </label>

              <input
                id="edit-title"
                type="text"
                value={title}
                onChange={(event) =>
                  setTitle(event.target.value)
                }
                required
                maxLength={200}
                className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="edit-description"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Description
              </label>

              <textarea
                id="edit-description"
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                rows={4}
                className="w-full resize-none rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </div>

            {/* Status + Priority */}
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">

              <div>
                <label
                  htmlFor="edit-status"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Status
                </label>

                <select
                  id="edit-status"
                  value={status}
                  onChange={(event) =>
                    setStatus(event.target.value)
                  }
                  className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                >
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

              <div>
                <label
                  htmlFor="edit-priority"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Priority
                </label>

                <select
                  id="edit-priority"
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

            </div>

            {/* Due Date */}
            <div>
              <label
                htmlFor="edit-due-date"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Due Date
              </label>

              <input
                id="edit-due-date"
                type="date"
                value={dueDate}
                onChange={(event) =>
                  setDueDate(event.target.value)
                }
                className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </div>

            {/* Assigned To */}
            <div>
              <label
                htmlFor="edit-assigned-to"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Assigned To
              </label>

              <input
                id="edit-assigned-to"
                type="number"
                min="1"
                value={assignedTo}
                onChange={(event) =>
                  setAssignedTo(event.target.value)
                }
                placeholder="User ID"
                className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </div>

            {/* Buttons */}
            <div className="flex gap-3 pt-2">

              <button
                type="submit"
                disabled={updating}
                className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {updating
                  ? "Saving..."
                  : "Save Changes"}
              </button>

              <button
                type="button"
                onClick={closeEditForm}
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
              htmlFor="status-filter"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Status
            </label>

            <select
              id="status-filter"
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
              htmlFor="priority-filter"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Priority
            </label>

            <select
              id="priority-filter"
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

              <div className="flex flex-col justify-between gap-4 lg:flex-row">

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

              {/* Actions */}
              <div className="mt-5 flex flex-wrap gap-3 border-t border-slate-100 pt-4">

                <button
                  type="button"
                  onClick={() => openEditForm(task)}
                  className="rounded-lg border border-blue-200 px-4 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-50"
                >
                  Edit
                </button>

                {(user?.role === "admin" ||
                  user?.role === "manager") && (
                  <button
                    type="button"
                    onClick={() =>
                      handleDeleteTask(task.id)
                    }
                    disabled={deletingTaskId === task.id}
                    className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {deletingTaskId === task.id
                      ? "Deleting..."
                      : "Delete"}
                  </button>
                )}

              </div>

            </div>
          ))}

        </div>
      )}

    </div>
  );
}

export default Tasks;