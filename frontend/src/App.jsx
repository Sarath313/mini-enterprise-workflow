import { BrowserRouter, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Tasks from "./pages/Tasks";

function AppLayout({ children }) {
  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <Navbar />

        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<ProtectedRoute />}>
          <Route
            path="/dashboard"
            element={
              <AppLayout>
                <Dashboard />
              </AppLayout>
            }
          />

          <Route
            path="/tasks"
            element={
              <AppLayout>
                <Tasks />
              </AppLayout>
            }
          />
        </Route>

        <Route path="*" element={<Login />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;