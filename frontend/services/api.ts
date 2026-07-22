import axios from "axios";

export const api = axios.create({
  baseURL: "",
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === "ECONNABORTED") {
      throw new Error("Request timed out. The server may be busy.");
    }
    if (!error.response) {
      throw new Error("Cannot connect to server. Please check if the backend is running.");
    }
    const message = error.response?.data?.detail || error.message || "An unexpected error occurred";
    throw new Error(message);
  }
);
