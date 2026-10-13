import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

let accessToken = null;
let csrfToken = null;
let refreshRequest = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function clearAccessToken() {
  accessToken = null;
}

export function clearAuthTokens() {
  clearAccessToken();
  csrfToken = null;
}

export function clearLegacyAuthStorage() {
  try {
    window.localStorage.removeItem("access_token");
    window.localStorage.removeItem("refresh_token");
  } catch {
    console.warn("Legacy browser auth tokens could not be removed.");
  }
}

function refreshAccessToken() {
  if (!refreshRequest) {
    refreshRequest = (async () => {
      if (!csrfToken) {
        const csrfResponse = await api.get("/auth/csrf");
        csrfToken = csrfResponse.data.csrf_token;
      }

      let response;
      try {
        response = await api.post(
          "/auth/refresh",
          null,
          { headers: { "X-CSRF-Token": csrfToken } }
        );
      } catch (error) {
        if (error.response?.status !== 403) {
          clearAuthTokens();
          throw error;
        }

        const csrfResponse = await api.get("/auth/csrf");
        csrfToken = csrfResponse.data.csrf_token;
        response = await api.post(
          "/auth/refresh",
          null,
          { headers: { "X-CSRF-Token": csrfToken } }
        );
      }

      setAccessToken(response.data.access_token);
      csrfToken = response.data.csrf_token;
      return response.data.access_token;
    })().finally(() => {
      refreshRequest = null;
    });
  }

  return refreshRequest;
}

export function setCsrfToken(token) {
  csrfToken = token;
}

export async function logoutSession() {
  if (!csrfToken) {
    const response = await api.get("/auth/csrf");
    csrfToken = response.data.csrf_token;
  }

  try {
    return await api.post(
      "/auth/logout",
      null,
      { headers: { "X-CSRF-Token": csrfToken } }
    );
  } catch (error) {
    if (error.response?.status !== 403) {
      throw error;
    }

    const response = await api.get("/auth/csrf");
    csrfToken = response.data.csrf_token;
    return api.post(
      "/auth/logout",
      null,
      { headers: { "X-CSRF-Token": csrfToken } }
    );
  }
}

api.interceptors.request.use(
  (config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const requestUrl = originalRequest?.url || "";
    const isAuthRequest = [
      "/auth/login",
      "/auth/refresh",
      "/auth/logout",
    ].some((path) => requestUrl.startsWith(path));

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      isAuthRequest
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      const token = await refreshAccessToken();
      originalRequest.headers.Authorization = `Bearer ${token}`;
      return api(originalRequest);
    } catch (refreshError) {
      clearAccessToken();
      window.dispatchEvent(new Event("auth:expired"));
      return Promise.reject(refreshError);
    }
  }
);

export { refreshAccessToken };
export default api;
