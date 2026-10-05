import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";

function Dashboard() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [provider, setProvider] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadUser = async () => {
      try {
        const [meResponse, providerResponse] = await Promise.all([
          api.get("/auth/me"),
          api.get("/auth/provider"),
        ]);

        setUser(meResponse.data);
        setProvider(providerResponse.data);
      } catch (err) {
        console.error(err);
        localStorage.removeItem("access_token");
        setError("Session expired. Please login again.");
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  const logout = () => {
    localStorage.removeItem("access_token");
    window.location.href = "http://localhost:8001/auth/google/logout";
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="rounded-xl bg-white p-8 shadow-lg">
          <p className="text-slate-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
        <div className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-lg">
          <h1 className="text-xl font-bold text-red-600">
            Authentication Error
          </h1>

          <p className="mt-3 text-sm text-slate-600">
            {error}
          </p>

          <button
            onClick={() => navigate("/login")}
            className="mt-6 rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              Mini Enterprise
            </h1>

            <p className="text-xs text-slate-500">
              Enterprise Collaboration Platform
            </p>
          </div>

          <button
            onClick={logout}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-slate-900">
            Welcome to your Dashboard
          </h2>

          <p className="mt-2 text-slate-500">
            OAuth authentication is active.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl bg-white p-6 shadow">
            <p className="text-sm font-medium text-slate-500">
              Authentication
            </p>

            <p className="mt-2 text-2xl font-bold text-green-600">
              Authenticated
            </p>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow">
            <p className="text-sm font-medium text-slate-500">
              Provider
            </p>

            <p className="mt-2 text-2xl font-bold capitalize text-slate-900">
              {provider?.provider || "Unknown"}
            </p>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow">
            <p className="text-sm font-medium text-slate-500">
              User
            </p>

            <p className="mt-2 break-all text-sm font-semibold text-slate-900">
              {user?.user?.email || "Authenticated User"}
            </p>
          </div>
        </div>

        <div className="mt-8 rounded-2xl bg-white p-6 shadow">
          <h3 className="text-lg font-bold text-slate-900">
            Authentication Details
          </h3>

          <div className="mt-5 space-y-4">
            <div>
              <p className="text-xs font-medium uppercase text-slate-400">
                Email
              </p>

              <p className="mt-1 text-sm text-slate-700">
                {user?.user?.email || "Not available"}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase text-slate-400">
                Provider
              </p>

              <p className="mt-1 text-sm capitalize text-slate-700">
                {provider?.provider || "Unknown"}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase text-slate-400">
                Subject
              </p>

              <p className="mt-1 break-all text-sm text-slate-700">
                {provider?.subject || user?.user?.sub || "Not available"}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase text-slate-400">
                Status
              </p>

              <span className="mt-1 inline-block rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
                Active
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
