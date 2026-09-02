import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Sidebar() {
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

  return (
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
  );
}

export default Sidebar;