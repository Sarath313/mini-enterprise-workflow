import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Sidebar({ isOpen, onClose }) {
  const { user } = useAuth();

  const links = [
    {
      name: "Dashboard",
      path: "/dashboard",
      roles: ["admin", "manager", "employee"],
    },
    {
      name: user?.role === "employee" ? "My Tasks" : "Tasks",
      path: "/tasks",
      roles: ["admin", "manager", "employee"],
    },
    {
      name: "Kanban",
      path: "/kanban",
      roles: ["admin", "manager", "employee"],
    },
    {
      name: "Comments",
      path: "/comments",
      roles: ["admin", "manager", "employee"],
    },
    {
      name: "Approvals",
      path: "/approvals",
      roles: ["admin", "manager"],
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
    {
      name: "Documents",
      path: "/documents",
      roles: ["admin", "manager", "employee"],
    },
    {
      name: "Notifications",
      path: "/notifications",
      roles: ["admin", "manager", "employee"],
    },
    {
      name: "AI Insights",
      path: "/ai-insights",
      roles: ["admin", "manager", "employee"],
    },
  ];

  const visibleLinks = links.filter((link) =>
    link.roles.includes(user?.role)
  );

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-50 flex h-screen w-64 flex-col border-r border-slate-200 bg-white transition-transform duration-300 lg:static lg:z-auto lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo / Header */}
        <div className="flex h-16 items-center justify-between border-b border-slate-200 px-5">
          <div>
            <h1 className="text-lg font-bold text-slate-900">
              Mini Enterprise
            </h1>
            <p className="text-xs text-slate-500">
              Workflow Management
            </p>
          </div>

          {/* Mobile Close Button */}
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
            aria-label="Close sidebar"
          >
            ✕
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto p-4">
          {visibleLinks.map((link) => (
            <NavLink
              key={link.path}
              to={link.path}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center rounded-lg px-4 py-3 text-sm font-medium transition ${
                  isActive
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`
              }
            >
              {link.name}
            </NavLink>
          ))}
        </nav>

        {/* User Information */}
        <div className="border-t border-slate-200 p-4">
          <div className="rounded-lg bg-slate-50 p-3">
            <p className="truncate text-sm font-semibold text-slate-900">
              {user?.email || "User"}
            </p>

            <p className="mt-1 text-xs capitalize text-slate-500">
              {user?.role || "employee"}
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;