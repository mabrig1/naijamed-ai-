import axios from "axios";

const BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD ? window.location.origin : "http://localhost:8000");

const api = axios.create({
  baseURL: BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("naijamed_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("naijamed_token");
      localStorage.removeItem("naijamed_refresh");
      localStorage.removeItem("naijamed_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
