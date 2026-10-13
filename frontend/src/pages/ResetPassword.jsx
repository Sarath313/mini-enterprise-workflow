import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import api from "../api/axios";

function ResetPassword() {
  const location = useLocation();
  const token = new URLSearchParams(location.hash.slice(1)).get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(
    token ? "" : "This password reset link is missing its token."
  );
  const [completed, setCompleted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("The passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/auth/reset-password", {
        token,
        new_password: password,
      });
      setCompleted(true);
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Unable to reset the password. The link may have expired."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <main className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <h1 className="text-2xl font-bold text-slate-900">
          Reset your password
        </h1>
        {completed ? (
          <>
            <p role="status" className="mt-4 text-sm text-green-800">
              Your password has been updated. You can now sign in.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-block rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700"
            >
              Back to sign in
            </Link>
          </>
        ) : (
          <>
            <p className="mt-2 text-sm text-slate-600">
              Choose a new password with at least 12 characters.
            </p>
            <form onSubmit={handleSubmit} className="mt-6 space-y-5">
              {error && (
                <div
                  role="alert"
                  className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
                >
                  {error}
                </div>
              )}
              <div>
                <label
                  htmlFor="new-password"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  New password
                </label>
                <input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={12}
                  maxLength={128}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                />
              </div>
              <div>
                <label
                  htmlFor="confirm-password"
                  className="mb-2 block text-sm font-medium text-slate-700"
                >
                  Confirm new password
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={12}
                  maxLength={128}
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  required
                  className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                />
              </div>
              <button
                type="submit"
                disabled={submitting || !token}
                className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "Updating..." : "Update password"}
              </button>
            </form>
            <Link
              to="/login"
              className="mt-6 inline-block text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Back to sign in
            </Link>
          </>
        )}
      </main>
    </div>
  );
}

export default ResetPassword;
