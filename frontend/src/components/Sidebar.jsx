import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Sidebar({ mobileOpen, setMobileOpen }) {
  const { user } = useAuth();

  const links = [
    {
      name: "Dashboard",
      path: "/dashboard",
      roles: ["admin", "manager", "employee"],
    },
    {
      name: "Tasks",
      path: "/tasks",
      roles: ["admin", "manager"],
    },
    {
      name: "My Tasks",
      path: "/tasks",
      roles: ["employee"],
    },
    {
      name: "Users",
      path: "/users",
      roles: ["admin"],
    },
    {
      name: "Activity",
      path: "/activity",
      roles: ["admin", "manager", "employee"],
    },
  ];

  const visibleLinks = links.filter((link) =>
    link.roles.includes(user?.role)
  );

  const handleNavigation = () => {
    if (setMobileOpen) {
      setMobileOpen(false);
    }
  };

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden w-64 flex-shrink-0 bg-slate-900 text-white md:block">
        <div className="flex h-16 items-center border-b border-slate-700 px-6">
          <h2 className="text-lg font-bold">
            Enterprise Workflow
          </h2>
        </div>

        <nav className="space-y-2 p-4">
          {visibleLinks.map((link) => (
            <NavLink
              key={link.name}
              to={link.path}
              onClick={handleNavigation}
              className={({ isActive }) =>
                `block rounded-lg px-4 py-3 text-sm font-medium transition ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              {link.name}
            </NavLink>
          ))}
        </nav>

        {user && (
          <div className="absolute bottom-0 w-64 border-t border-slate-700 p-4">
            <p className="text-sm font-semibold text-white">
              {user.name}
            </p>

            <p className="mt-1 text-xs capitalize text-slate-400">
              {user.role}
            </p>
          </div>
        )}
      </aside>

      {/* Mobile Overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/50 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 transform bg-slate-900 text-white shadow-xl transition-transform duration-200 md:hidden ${
          mobileOpen
            ? "translate-x-0"
            : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-slate-700 px-5">
          <h2 className="text-lg font-bold">
            Enterprise Workflow
          </h2>

          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="rounded-lg px-3 py-2 text-slate-300 hover:bg-slate-800 hover:text-white"
            aria-label="Close navigation"
          >
            ✕
          </button>
        </div>

        <nav className="space-y-2 p-4">
          {visibleLinks.map((link) => (
            <NavLink
              key={link.name}
              to={link.path}
              onClick={handleNavigation}
              className={({ isActive }) =>
                `block rounded-lg px-4 py-3 text-sm font-medium transition ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              {link.name}
            </NavLink>
          ))}
        </nav>

        {user && (
          <div className="absolute bottom-0 w-full border-t border-slate-700 p-4">
            <p className="text-sm font-semibold text-white">
              {user.name}
            </p>

            <p className="mt-1 text-xs capitalize text-slate-400">
              {user.role}
            </p>
          </div>
        )}
      </aside>
    </>
  );
}

export default Sidebar;