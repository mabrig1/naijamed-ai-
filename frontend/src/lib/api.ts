import axios from "axios";

const BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? window.location.origin : "http://localhost:8000");

export const api = axios.create({
  baseURL: BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("naijamed_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("naijamed_refresh");
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/api/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem("naijamed_token", data.access_token);
          localStorage.setItem("naijamed_refresh", data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          // Refresh failed; clear the local session below.
        }
      }
      localStorage.removeItem("naijamed_token");
      localStorage.removeItem("naijamed_refresh");
      localStorage.removeItem("naijamed_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
