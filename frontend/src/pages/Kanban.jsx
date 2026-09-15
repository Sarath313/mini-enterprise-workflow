import { useEffect, useState } from "react";
import api from "../api/axios";

const columns = [
  {
    key: "todo",
    title: "To Do",
    description: "Tasks waiting to be started",
  },
  {
    key: "in_progress",
    title: "In Progress",
    description: "Tasks currently being worked on",
  },
  {
    key: "review",
    title: "Review",
    description: "Tasks waiting for review or approval",
  },
  {
    key: "done",
    title: "Done",
    description: "Completed tasks",
  },
];

const priorityClasses = {
  low: "bg-slate-100 text-slate-700",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-red-100 text-red-700",
};

function formatStatus(status) {
  return status
    .replace("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function Kanban() {
  const [board, setBoard] = useState({
    todo: [],
    in_progress: [],
    review: [],
    done: [],
  });

  const [loading, setLoading] = useState(true);
  const [draggedTask, setDraggedTask] = useState(null);
  const [dragOverColumn, setDragOverColumn] = useState(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [updatingTaskId, setUpdatingTaskId] = useState(null);

  const fetchKanban = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/tasks/kanban");

      setBoard({
        todo: response.data.todo || [],
        in_progress: response.data.in_progress || [],
        review: response.data.review || [],
        done: response.data.done || [],
      });
    } catch (error) {
      console.error("Kanban error:", error);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to load Kanban board.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKanban();
  }, []);

  const handleDragStart = (event, task) => {
    setDraggedTask(task);
    setError("");
    setSuccess("");

    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData(
      "text/plain",
      String(task.id)
    );
  };

  const handleDragEnd = () => {
    setDraggedTask(null);
    setDragOverColumn(null);
  };

  const handleDragOver = (event, columnKey) => {
    event.preventDefault();

    event.dataTransfer.dropEffect = "move";

    if (dragOverColumn !== columnKey) {
      setDragOverColumn(columnKey);
    }
  };

  const handleDragLeave = (event, columnKey) => {
    if (
      event.currentTarget.contains(event.relatedTarget)
    ) {
      return;
    }

    if (dragOverColumn === columnKey) {
      setDragOverColumn(null);
    }
  };

  const handleDrop = async (event, newStatus) => {
    event.preventDefault();

    setDragOverColumn(null);

    if (!draggedTask) {
      return;
    }

    const currentStatus = draggedTask.status;

    if (currentStatus === newStatus) {
      setDraggedTask(null);
      return;
    }

    setUpdatingTaskId(draggedTask.id);
    setError("");
    setSuccess("");

    try {
      await api.patch(
        `/tasks/${draggedTask.id}/status`,
        {
          status: newStatus,
        }
      );

      setSuccess(
        `Task "${draggedTask.title}" moved to ${formatStatus(
          newStatus
        )}.`
      );

      setDraggedTask(null);

      await fetchKanban();
    } catch (error) {
      console.error(
        "Kanban status update error:",
        error
      );

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError(
          "Unable to update task status."
        );
      }

      setDraggedTask(null);

      await fetchKanban();
    } finally {
      setUpdatingTaskId(null);
    }
  };

  const getTotalTasks = () => {
    return (
      board.todo.length +
      board.in_progress.length +
      board.review.length +
      board.done.length
    );
  };

  const renderTaskCard = (task) => {
    const isUpdating =
      updatingTaskId === task.id;

    return (
      <div
        key={task.id}
        draggable={!isUpdating}
        onDragStart={(event) =>
          handleDragStart(event, task)
        }
        onDragEnd={handleDragEnd}
        className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition ${
          isUpdating
            ? "cursor-wait opacity-60"
            : "cursor-grab hover:-translate-y-0.5 hover:shadow-md active:cursor-grabbing"
        }`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-semibold text-slate-900">
              {task.title}
            </h3>

            <p className="mt-1 text-xs text-slate-400">
              Task #{task.id}
            </p>
          </div>

          <span
            className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${
              priorityClasses[task.priority] ||
              priorityClasses.medium
            }`}
          >
            {task.priority}
          </span>
        </div>

        {task.description && (
          <p className="mt-3 line-clamp-3 text-sm leading-5 text-slate-500">
            {task.description}
          </p>
        )}

        <div className="mt-4 space-y-2 border-t border-slate-100 pt-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">
              Assigned to
            </span>

            <span className="font-medium text-slate-600">
              {task.assigned_to
                ? `User #${task.assigned_to}`
                : "Unassigned"}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">
              Due date
            </span>

            <span className="font-medium text-slate-600">
              {task.due_date
                ? new Date(
                    task.due_date
                  ).toLocaleDateString()
                : "No due date"}
            </span>
          </div>
        </div>

        {isUpdating && (
          <div className="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-center text-xs font-medium text-blue-700">
            Updating status...
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">
            Kanban Board
          </h1>

          <p className="mt-2 text-slate-500">
            Drag tasks between workflow stages
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Total Tasks
          </p>

          <p className="mt-1 text-2xl font-bold text-slate-900">
            {getTotalTasks()}
          </p>
        </div>
      </div>

      {/* Workflow Information */}
      <div className="mb-6 rounded-2xl border border-blue-100 bg-blue-50 p-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-semibold text-blue-900">
              Workflow
            </p>

            <p className="mt-1 text-sm text-blue-700">
              Tasks must follow the defined workflow.
              Invalid status transitions are blocked by
              the backend.
            </p>
          </div>

          <div className="text-sm font-semibold text-blue-800">
            To Do → In Progress → Review → Done
          </div>
        </div>
      </div>

      {/* Success */}
      {success && (
        <div className="mb-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-700">
          {success}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <span>{error}</span>

            <button
              type="button"
              onClick={fetchKanban}
              className="self-start rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-700 transition hover:bg-red-100"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />

          <p className="text-sm text-slate-500">
            Loading Kanban board...
          </p>
        </div>
      ) : (
        /* Board */
        <div className="overflow-x-auto pb-4">
          <div className="grid min-w-[1100px] grid-cols-4 gap-5">
            {columns.map((column) => {
              const columnTasks =
                board[column.key] || [];

              const isDropTarget =
                dragOverColumn === column.key;

              return (
                <div
                  key={column.key}
                  onDragOver={(event) =>
                    handleDragOver(
                      event,
                      column.key
                    )
                  }
                  onDragLeave={(event) =>
                    handleDragLeave(
                      event,
                      column.key
                    )
                  }
                  onDrop={(event) =>
                    handleDrop(
                      event,
                      column.key
                    )
                  }
                  className={`min-h-[500px] rounded-2xl border p-4 transition ${
                    isDropTarget
                      ? "border-blue-400 bg-blue-50/60 shadow-md"
                      : "border-slate-200 bg-slate-50"
                  }`}
                >
                  {/* Column Header */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between">
                      <h2 className="font-bold text-slate-900">
                        {column.title}
                      </h2>

                      <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-slate-600 shadow-sm">
                        {columnTasks.length}
                      </span>
                    </div>

                    <p className="mt-1 text-xs text-slate-400">
                      {column.description}
                    </p>
                  </div>

                  {/* Drop Area */}
                  <div
                    className={`space-y-3 rounded-xl transition ${
                      isDropTarget
                        ? "min-h-[420px]"
                        : "min-h-[420px]"
                    }`}
                  >
                    {columnTasks.length === 0 ? (
                      <div
                        className={`flex min-h-[180px] items-center justify-center rounded-xl border-2 border-dashed text-center ${
                          isDropTarget
                            ? "border-blue-300 bg-blue-50 text-blue-600"
                            : "border-slate-200 bg-white text-slate-400"
                        }`}
                      >
                        <div>
                          <p className="text-sm font-medium">
                            {isDropTarget
                              ? "Drop task here"
                              : "No tasks"}
                          </p>

                          <p className="mt-1 text-xs">
                            {isDropTarget
                              ? "Release to change status"
                              : "Drag a task into this column"}
                          </p>
                        </div>
                      </div>
                    ) : (
                      columnTasks.map(
                        renderTaskCard
                      )
                    )}

                    {isDropTarget &&
                      columnTasks.length > 0 && (
                        <div className="rounded-xl border-2 border-dashed border-blue-300 bg-blue-50 p-5 text-center text-xs font-medium text-blue-600">
                          Drop task here to move it to{" "}
                          {column.title}
                        </div>
                      )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Mobile hint */}
      <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 text-center text-xs text-slate-500 md:hidden">
        Swipe horizontally to view all Kanban columns.
      </div>
    </div>
  );
}

export default Kanban;