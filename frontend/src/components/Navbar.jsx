import { useAuth } from "../context/AuthContext";

function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
      {/* Left side */}
      <div>
        <h1 className="text-lg font-bold text-slate-900">
          Mini Enterprise Workflow
        </h1>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-5">
        {user && (
          <div className="text-right">
            <p className="text-sm font-semibold text-slate-800">
              {user.name}
            </p>

            <p className="text-xs capitalize text-slate-500">
              {user.role}
            </p>
          </div>
        )}

        <button
          onClick={logout}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
        >
          Logout
        </button>
      </div>
    </header>
  );
}

export default Navbar;