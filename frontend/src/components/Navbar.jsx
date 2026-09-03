import { useAuth } from "../context/AuthContext";

function Navbar({ onMenuClick }) {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
      <div className="flex items-center gap-3">
        {/* Mobile Menu Button */}
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-lg border border-slate-300 px-3 py-2 text-slate-700 transition hover:bg-slate-100 md:hidden"
          aria-label="Open navigation"
        >
          ☰
        </button>

        <div>
          <h1 className="text-base font-bold text-slate-900 sm:text-lg">
            Mini Enterprise Workflow
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-5">
        {user && (
          <div className="hidden text-right sm:block">
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
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 sm:px-4"
        >
          Logout
        </button>
      </div>
    </header>
  );
}

export default Navbar;