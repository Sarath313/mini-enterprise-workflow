import { createContext, useContext, useEffect, useState } from "react";
import api, {
  clearAuthTokens,
  clearLegacyAuthStorage,
  logoutSession,
  refreshAccessToken,
  setCsrfToken,
  setAccessToken,
} from "../api/axios";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    clearLegacyAuthStorage();

    const handleExpiredSession = () => {
      clearAuthTokens();
      setUser(null);
    };
    window.addEventListener("auth:expired", handleExpiredSession);

    refreshAccessToken()
      .then(() => api.get("/auth/me"))
      .then((response) => {
        setUser(response.data);
      })
      .catch(() => {
        clearAuthTokens();
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });

    return () => {
      window.removeEventListener("auth:expired", handleExpiredSession);
    };
  }, []);

  const login = async (email, password) => {
    const formData = new URLSearchParams();

    formData.append("username", email);
    formData.append("password", password);

    const response = await api.post("/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    setAccessToken(response.data.access_token);
    setCsrfToken(response.data.csrf_token);

    try {
      const userResponse = await api.get("/auth/me");

      setUser(userResponse.data);

      return userResponse.data;
    } catch (error) {
      clearAuthTokens();
      throw error;
    }
  };

  const logout = async () => {
    try {
      await logoutSession();
    } catch {
      console.warn("Server logout failed; local session was cleared.");
    } finally {
      clearAuthTokens();
      setUser(null);
    }
  };

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: Boolean(user),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}