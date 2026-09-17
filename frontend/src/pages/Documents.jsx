import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";

function Documents() {
  const { user } = useAuth();

  const [tasks, setTasks] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [documents, setDocuments] = useState([]);

  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadTaskId, setUploadTaskId] = useState("");

  const [loadingTasks, setLoadingTasks] = useState(true);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // -------------------------------------------------------------------------
  // Load tasks
  // -------------------------------------------------------------------------

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        setLoadingTasks(true);
        setError("");

        const response = await api.get("/tasks/", {
          params: {
            limit: 100,
          },
        });

        const taskList = response.data || [];

        setTasks(taskList);

        if (taskList.length > 0) {
          setSelectedTaskId(String(taskList[0].id));
        }
      } catch (err) {
        console.error("Failed to load tasks:", err);

        setError(
          err.response?.data?.detail ||
            "Failed to load tasks."
        );
      } finally {
        setLoadingTasks(false);
      }
    };

    fetchTasks();
  }, []);

  // -------------------------------------------------------------------------
  // Load documents for selected task
  // -------------------------------------------------------------------------

  useEffect(() => {
    const fetchDocuments = async () => {
      if (!selectedTaskId) {
        setDocuments([]);
        return;
      }

      try {
        setLoadingDocuments(true);
        setError("");

        const response = await api.get(
          `/documents/task/${selectedTaskId}`
        );

        setDocuments(response.data || []);
      } catch (err) {
        console.error("Failed to load documents:", err);

        setDocuments([]);

        setError(
          err.response?.data?.detail ||
            "Failed to load task documents."
        );
      } finally {
        setLoadingDocuments(false);
      }
    };

    fetchDocuments();
  }, [selectedTaskId]);

  // -------------------------------------------------------------------------
  // Upload document
  // -------------------------------------------------------------------------

  const handleUpload = async (event) => {
    event.preventDefault();

    if (!selectedFile) {
      setError("Please select a file.");
      setSuccess("");
      return;
    }

    try {
      setUploading(true);
      setError("");
      setSuccess("");

      const formData = new FormData();

      formData.append("file", selectedFile);

      if (uploadTaskId) {
        formData.append("task_id", uploadTaskId);
      }

      const response = await api.post(
        "/documents/upload",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      const uploadedDocument = response.data;

      setSelectedFile(null);
      setUploadTaskId("");

      const fileInput = document.getElementById(
        "document-file"
      );

      if (fileInput) {
        fileInput.value = "";
      }

      setSuccess(
        `${uploadedDocument.file_name} uploaded successfully as version ${uploadedDocument.version}.`
      );

      // Refresh the currently selected task's documents.
      if (
        selectedTaskId &&
        String(uploadedDocument.task_id) === selectedTaskId
      ) {
        const documentsResponse = await api.get(
          `/documents/task/${selectedTaskId}`
        );

        setDocuments(documentsResponse.data || []);
      }
    } catch (err) {
      console.error("Failed to upload document:", err);

      setError(
        err.response?.data?.detail ||
          "Failed to upload document."
      );

      setSuccess("");
    } finally {
      setUploading(false);
    }
  };

  // -------------------------------------------------------------------------
  // Download document
  // -------------------------------------------------------------------------

  const handleDownload = async (document) => {
    try {
      setDownloadingId(document.id);
      setError("");

      const response = await api.get(
        `/documents/${document.id}`,
        {
          responseType: "blob",
        }
      );

      const blob = new Blob(
        [response.data],
        {
          type:
            document.content_type ||
            "application/octet-stream",
        }
      );

      const url = window.URL.createObjectURL(blob);

      const link = window.document.createElement("a");

      link.href = url;
      link.download = document.file_name;

      window.document.body.appendChild(link);
      link.click();

      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download document:", err);

      setError(
        err.response?.data?.detail ||
          "Failed to download document."
      );
    } finally {
      setDownloadingId(null);
    }
  };

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  const formatDate = (value) => {
    if (!value) {
      return "—";
    }

    return new Date(value).toLocaleString();
  };

  const selectedTask = tasks.find(
    (task) => String(task.id) === selectedTaskId
  );

  const formatFileSize = (file) => {
    if (!file) {
      return "";
    }

    const size = file.size;

    if (size < 1024) {
      return `${size} B`;
    }

    if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    }

    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="min-h-screen bg-slate-100 p-4 md:p-6">
      <div className="mx-auto max-w-7xl space-y-6">

        {/* ---------------------------------------------------------------- */}
        {/* Header                                                           */}
        {/* ---------------------------------------------------------------- */}

        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Documents
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Upload, manage, version and download enterprise documents.
          </p>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Alerts                                                           */}
        {/* ---------------------------------------------------------------- */}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {success}
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Upload section                                                   */}
        {/* ---------------------------------------------------------------- */}

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">

          <div className="mb-5">
            <h2 className="text-lg font-semibold text-slate-900">
              Upload Document
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Maximum file size: 10 MB. Supported documents include PDF,
              Word, Excel, CSV, TXT and common image formats.
            </p>
          </div>

          <form
            onSubmit={handleUpload}
            className="grid gap-5 md:grid-cols-3"
          >

            {/* File */}
            <div className="md:col-span-2">
              <label
                htmlFor="document-file"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Select file
              </label>

              <input
                id="document-file"
                type="file"
                onChange={(event) => {
                  setSelectedFile(
                    event.target.files?.[0] || null
                  );

                  setError("");
                  setSuccess("");
                }}
                className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium"
              />

              {selectedFile && (
                <p className="mt-2 text-xs text-slate-500">
                  {selectedFile.name} ·{" "}
                  {formatFileSize(selectedFile)}
                </p>
              )}
            </div>

            {/* Task */}
            <div>
              <label
                htmlFor="upload-task"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Link to task
              </label>

              <select
                id="upload-task"
                value={uploadTaskId}
                onChange={(event) =>
                  setUploadTaskId(event.target.value)
                }
                disabled={loadingTasks}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                <option value="">
                  No task
                </option>

                {tasks.map((task) => (
                  <option
                    key={task.id}
                    value={task.id}
                  >
                    #{task.id} — {task.title}
                  </option>
                ))}
              </select>
            </div>

            {/* Upload button */}
            <div className="md:col-span-3">
              <button
                type="submit"
                disabled={uploading || !selectedFile}
                className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {uploading
                  ? "Uploading..."
                  : "Upload Document"}
              </button>
            </div>
          </form>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Task documents                                                   */}
        {/* ---------------------------------------------------------------- */}

        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">

          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">

            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Task Documents
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                View all document versions associated with a task.
              </p>
            </div>

            <div className="w-full md:w-96">
              <label
                htmlFor="selected-task"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Select task
              </label>

              <select
                id="selected-task"
                value={selectedTaskId}
                onChange={(event) =>
                  setSelectedTaskId(event.target.value)
                }
                disabled={
                  loadingTasks || tasks.length === 0
                }
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              >
                {tasks.length === 0 && (
                  <option value="">
                    No tasks available
                  </option>
                )}

                {tasks.map((task) => (
                  <option
                    key={task.id}
                    value={task.id}
                  >
                    #{task.id} — {task.title}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Selected task */}
          {selectedTask && (
            <div className="mt-5 rounded-lg bg-slate-50 p-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="rounded-md bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
                  TASK #{selectedTask.id}
                </span>

                <span className="font-semibold text-slate-900">
                  {selectedTask.title}
                </span>

                <span className="rounded-md bg-slate-200 px-2.5 py-1 text-xs font-medium capitalize text-slate-600">
                  {selectedTask.status}
                </span>

                <span className="rounded-md bg-slate-200 px-2.5 py-1 text-xs font-medium capitalize text-slate-600">
                  {selectedTask.priority}
                </span>
              </div>
            </div>
          )}

          {/* Documents */}
          <div className="mt-6 overflow-hidden rounded-lg border border-slate-200">

            {loadingDocuments ? (
              <div className="p-8 text-center text-sm text-slate-500">
                Loading documents...
              </div>
            ) : documents.length === 0 ? (
              <div className="p-8 text-center">
                <p className="font-medium text-slate-700">
                  No documents found
                </p>

                <p className="mt-1 text-sm text-slate-500">
                  Upload a document and link it to this task
                  to see it here.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Document
                      </th>

                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Version
                      </th>

                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Type
                      </th>

                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Uploaded By
                      </th>

                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Created
                      </th>

                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Action
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-200 bg-white">
                    {documents.map((document) => (
                      <tr
                        key={document.id}
                        className="hover:bg-slate-50"
                      >
                        <td className="px-4 py-4">
                          <div className="font-medium text-slate-900">
                            {document.file_name}
                          </div>

                          <div className="mt-1 text-xs text-slate-400">
                            Document #{document.id}
                          </div>
                        </td>

                        <td className="px-4 py-4">
                          <span className="rounded-md bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
                            v{document.version}
                          </span>
                        </td>

                        <td className="px-4 py-4 text-sm text-slate-600">
                          {document.content_type ||
                            "Unknown"}
                        </td>

                        <td className="px-4 py-4 text-sm text-slate-600">
                          User #{document.uploaded_by}
                        </td>

                        <td className="px-4 py-4 text-sm text-slate-600">
                          {formatDate(
                            document.created_at
                          )}
                        </td>

                        <td className="px-4 py-4 text-right">
                          <button
                            type="button"
                            onClick={() =>
                              handleDownload(document)
                            }
                            disabled={
                              downloadingId ===
                              document.id
                            }
                            className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                          >
                            {downloadingId ===
                            document.id
                              ? "Downloading..."
                              : "Download"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Information                                                      */}
        {/* ---------------------------------------------------------------- */}

        <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
          <h3 className="font-semibold text-blue-900">
            Document Management
          </h3>

          <ul className="mt-2 space-y-1 text-sm text-blue-800">
            <li>• Files are limited to 10 MB.</li>
            <li>• Unsupported file extensions are rejected.</li>
            <li>• Uploaded files receive unique server-side names.</li>
            <li>• Re-uploading the same filename creates a new version.</li>
            <li>• Task-linked documents follow task access permissions.</li>
          </ul>
        </div>

        <div className="pb-6 text-xs text-slate-400">
          Signed in as{" "}
          <span className="font-medium">
            {user?.email || "User"}
          </span>
        </div>
      </div>
    </div>
  );
}

export default Documents;