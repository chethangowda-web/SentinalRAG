import axios from "axios";

export const TOKEN_KEY = "sentinelrag_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const api = axios.create({
  baseURL: "",
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const token = getStoredToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === "ECONNABORTED") {
      throw new Error("Request timed out. The server may be busy.");
    }
    if (!error.response) {
      throw new Error("Cannot connect to server. Please check if the backend is running.");
    }
    // FastAPI sends validation errors (422) as a list of {msg}; everything else as a string.
    const detail = error.response?.data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d: { msg?: string }) => (d.msg ?? "").replace(/^Value error, /, "")).filter(Boolean).join(". ")
      : detail || error.message || "An unexpected error occurred";

    if (error.response?.status === 401) {
      clearStoredToken();
      const publicPages = ["/login", "/register", "/forgot-password", "/reset-password", "/terms", "/privacy"];
      if (typeof window !== "undefined" && !publicPages.some((p) => window.location.pathname.startsWith(p))) {
        window.location.href = "/login";
      }
    }

    throw new Error(message);
  }
);
