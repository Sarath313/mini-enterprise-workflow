import { useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/axios";

function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSubmitted(true);
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Unable to process the request right now. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <main className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <h1 className="text-2xl font-bold text-slate-900">
          Forgot your password?
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Enter your account email and, if it exists, reset instructions will
          be sent.
        </p>

        {submitted ? (
          <div
            role="status"
            className="mt-6 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-800"
          >
            If the account exists and email delivery is configured, password
            reset instructions will be sent.
          </div>
        ) : (
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
                htmlFor="reset-email"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Email
              </label>
              <input
                id="reset-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Sending..." : "Send reset instructions"}
            </button>
          </form>
        )}

        <Link
          to="/login"
          className="mt-6 inline-block text-sm font-medium text-blue-600 hover:text-blue-700"
        >
          Back to sign in
        </Link>
      </main>
    </div>
  );
}

export default ForgotPassword;
