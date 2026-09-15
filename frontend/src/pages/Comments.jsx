import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

function Comments() {
  const { user } = useAuth();

  const [tasks, setTasks] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");

  const [comments, setComments] = useState([]);

  const [content, setContent] = useState("");
  const [visibility, setVisibility] = useState("public");

  const [editingCommentId, setEditingCommentId] = useState(null);
  const [editingContent, setEditingContent] = useState("");

  const [loadingTasks, setLoadingTasks] = useState(true);
  const [loadingComments, setLoadingComments] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deletingCommentId, setDeletingCommentId] =
    useState(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const canUseInternal =
    user?.role === "admin" ||
    user?.role === "manager";

  const fetchTasks = async () => {
    setLoadingTasks(true);
    setError("");

    try {
      const response = await api.get("/tasks/");

      const taskList = response.data || [];

      setTasks(taskList);

      if (taskList.length > 0) {
        setSelectedTaskId(String(taskList[0].id));
      } else {
        setSelectedTaskId("");
      }
    } catch (error) {
      console.error("Comments tasks error:", error);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to load tasks.");
      }
    } finally {
      setLoadingTasks(false);
    }
  };

  const fetchComments = async (taskId) => {
    if (!taskId) {
      setComments([]);
      return;
    }

    setLoadingComments(true);
    setError("");

    try {
      const response = await api.get(
        `/tasks/${taskId}/comments`
      );

      setComments(response.data || []);
    } catch (error) {
      console.error("Comments error:", error);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to load comments.");
      }

      setComments([]);
    } finally {
      setLoadingComments(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  useEffect(() => {
    if (selectedTaskId) {
      fetchComments(selectedTaskId);
    }
  }, [selectedTaskId]);

  useEffect(() => {
    if (!canUseInternal && visibility === "internal") {
      setVisibility("public");
    }
  }, [canUseInternal, visibility]);

  const selectedTask = tasks.find(
    (task) => String(task.id) === String(selectedTaskId)
  );

  const resetMessages = () => {
    setError("");
    setSuccess("");
  };

  const handleCreateComment = async (event) => {
    event.preventDefault();

    if (!selectedTaskId) {
      setError("Please select a task.");
      return;
    }

    if (!content.trim()) {
      setError("Comment cannot be empty.");
      return;
    }

    setSubmitting(true);
    resetMessages();

    try {
      await api.post(
        `/tasks/${selectedTaskId}/comments`,
        {
          content: content.trim(),
          visibility,
        }
      );

      setContent("");
      setVisibility("public");

      setSuccess("Comment added successfully.");

      await fetchComments(selectedTaskId);
    } catch (error) {
      console.error("Create comment error:", error);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to add comment.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const startEditing = (comment) => {
    setEditingCommentId(comment.id);
    setEditingContent(comment.content);
    resetMessages();
  };

  const cancelEditing = () => {
    setEditingCommentId(null);
    setEditingContent("");
  };

  const handleUpdateComment = async (commentId) => {
    if (!editingContent.trim()) {
      setError("Comment cannot be empty.");
      return;
    }

    resetMessages();

    try {
      await api.put(
        `/tasks/${selectedTaskId}/comments/${commentId}`,
        {
          content: editingContent.trim(),
        }
      );

      setSuccess("Comment updated successfully.");

      cancelEditing();

      await fetchComments(selectedTaskId);
    } catch (error) {
      console.error("Update comment error:", error);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to update comment.");
      }
    }
  };

  const handleDeleteComment = async (commentId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this comment?"
    );

    if (!confirmed) {
      return;
    }

    setDeletingCommentId(commentId);
    resetMessages();

    try {
      await api.delete(
        `/tasks/${selectedTaskId}/comments/${commentId}`
      );

      setSuccess("Comment deleted successfully.");

      await fetchComments(selectedTaskId);
    } catch (error) {
      console.error("Delete comment error:", error);

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to delete comment.");
      }
    } finally {
      setDeletingCommentId(null);
    }
  };

  const formatDate = (value) => {
    if (!value) {
      return "Unknown date";
    }

    return new Date(value).toLocaleString();
  };

  const getVisibilityClasses = (comment) => {
    if (comment.visibility === "internal") {
      return "border-amber-200 bg-amber-50";
    }

    return "border-slate-200 bg-white";
  };

  return (
    <div className="p-4 md:p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900">
          Comments & Collaboration
        </h1>

        <p className="mt-2 text-slate-500">
          Collaborate with your team through task comments
          and internal notes.
        </p>
      </div>

      {/* Task selector */}
      <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <label
          htmlFor="task"
          className="mb-2 block text-sm font-semibold text-slate-700"
        >
          Select Task
        </label>

        {loadingTasks ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
            Loading tasks...
          </div>
        ) : tasks.length === 0 ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
            No tasks are available for your account.
          </div>
        ) : (
          <select
            id="task"
            value={selectedTaskId}
            onChange={(event) => {
              setSelectedTaskId(event.target.value);
              setContent("");
              setEditingCommentId(null);
              resetMessages();
            }}
            className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          >
            {tasks.map((task) => (
              <option
                key={task.id}
                value={task.id}
              >
                #{task.id} — {task.title}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Selected task */}
      {selectedTask && (
        <div className="mb-6 rounded-2xl border border-blue-100 bg-blue-50 p-5">
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">
                Selected Task
              </p>

              <h2 className="mt-1 text-xl font-bold text-blue-900">
                {selectedTask.title}
              </h2>
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold capitalize text-slate-600">
                {selectedTask.status.replace(
                  "_",
                  " "
                )}
              </span>

              <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold capitalize text-slate-600">
                {selectedTask.priority}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      {success && (
        <div className="mb-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-700">
          {success}
        </div>
      )}

      {error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Add comment */}
      {selectedTaskId && (
        <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-900">
              Add Comment
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Share an update, question, or note about this
              task.
            </p>
          </div>

          <form
            onSubmit={handleCreateComment}
            className="space-y-4"
          >
            <div>
              <label
                htmlFor="comment-content"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Comment
              </label>

              <textarea
                id="comment-content"
                value={content}
                onChange={(event) =>
                  setContent(event.target.value)
                }
                rows={5}
                maxLength={5000}
                placeholder="Write your comment..."
                className="w-full resize-y rounded-lg border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />

              <p className="mt-1 text-right text-xs text-slate-400">
                {content.length}/5000
              </p>
            </div>

            <div>
              <label
                htmlFor="visibility"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Visibility
              </label>

              <select
                id="visibility"
                value={visibility}
                onChange={(event) =>
                  setVisibility(event.target.value)
                }
                className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200 md:max-w-sm"
              >
                <option value="public">
                  Public — visible to everyone with task access
                </option>

                {canUseInternal && (
                  <option value="internal">
                    Internal — managers and admins only
                  </option>
                )}
              </select>

              {!canUseInternal && (
                <p className="mt-2 text-xs text-slate-400">
                  Internal notes are restricted to managers
                  and administrators.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={submitting || !selectedTaskId}
              className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting
                ? "Adding..."
                : "Add Comment"}
            </button>
          </form>
        </div>
      )}

      {/* Comments list */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-5 flex flex-col justify-between gap-2 md:flex-row md:items-center">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Comment History
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Collaboration history for the selected task.
            </p>
          </div>

          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
            {comments.length}{" "}
            {comments.length === 1
              ? "comment"
              : "comments"}
          </span>
        </div>

        {loadingComments ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-10 text-center">
            <div className="mx-auto mb-3 h-7 w-7 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />

            <p className="text-sm text-slate-500">
              Loading comments...
            </p>
          </div>
        ) : comments.length === 0 ? (
          <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 p-10 text-center">
            <p className="font-medium text-slate-600">
              No comments yet
            </p>

            <p className="mt-1 text-sm text-slate-400">
              Be the first to add a comment to this task.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {comments.map((comment) => {
              const isOwner =
                comment.user_id === user?.id;

              const canEdit =
                isOwner ||
                user?.role === "admin";

              const isEditing =
                editingCommentId === comment.id;

              return (
                <div
                  key={comment.id}
                  className={`rounded-xl border p-4 ${getVisibilityClasses(
                    comment
                  )}`}
                >
                  <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-slate-900">
                          {comment.user_email}
                        </span>

                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                            comment.visibility ===
                            "internal"
                              ? "bg-amber-200 text-amber-800"
                              : "bg-green-100 text-green-700"
                          }`}
                        >
                          {comment.visibility ===
                          "internal"
                            ? "Internal"
                            : "Public"}
                        </span>
                      </div>

                      <p className="mt-1 text-xs text-slate-400">
                        {formatDate(
                          comment.created_at
                        )}

                        {comment.updated_at &&
                          comment.updated_at !==
                            comment.created_at && (
                            <span>
                              {" "}
                              · edited{" "}
                              {formatDate(
                                comment.updated_at
                              )}
                            </span>
                          )}
                      </p>
                    </div>

                    {canEdit && !isEditing && (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            startEditing(comment)
                          }
                          className="rounded-lg border border-blue-200 px-3 py-1.5 text-xs font-semibold text-blue-700 transition hover:bg-blue-50"
                        >
                          Edit
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            handleDeleteComment(
                              comment.id
                            )
                          }
                          disabled={
                            deletingCommentId ===
                            comment.id
                          }
                          className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {deletingCommentId ===
                          comment.id
                            ? "Deleting..."
                            : "Delete"}
                        </button>
                      </div>
                    )}
                  </div>

                  {isEditing ? (
                    <div className="mt-4 space-y-3">
                      <textarea
                        value={editingContent}
                        onChange={(event) =>
                          setEditingContent(
                            event.target.value
                          )
                        }
                        rows={4}
                        maxLength={5000}
                        className="w-full resize-y rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                      />

                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            handleUpdateComment(
                              comment.id
                            )
                          }
                          className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-blue-700"
                        >
                          Save Changes
                        </button>

                        <button
                          type="button"
                          onClick={cancelEditing}
                          className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                      {comment.content}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default Comments;