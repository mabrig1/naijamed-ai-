import axios from "axios";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nigerflora_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("nigerflora_refresh");
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/api/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem("nigerflora_token", data.access_token);
          localStorage.setItem("nigerflora_refresh", data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          // refresh failed — fall through to clear + redirect
        }
      }
      localStorage.removeItem("nigerflora_token");
      localStorage.removeItem("nigerflora_refresh");
      localStorage.removeItem("nigerflora_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
