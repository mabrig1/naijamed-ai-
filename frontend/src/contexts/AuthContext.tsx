import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { api } from "../lib/api";
import type { User, Token } from "../types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string, role: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function loadUser(): User | null {
  try {
    const raw = localStorage.getItem("naijamed_user");
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(loadUser);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("naijamed_token"));

  const persist = useCallback((tokenData: Token) => {
    localStorage.setItem("naijamed_token", tokenData.access_token);
    localStorage.setItem("naijamed_refresh", tokenData.refresh_token);
    localStorage.setItem("naijamed_user", JSON.stringify(tokenData.user));
    setToken(tokenData.access_token);
    setUser(tokenData.user);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<Token>("/api/auth/login", { email, password });
    persist(data);
  }, [persist]);

  const register = useCallback(async (email: string, fullName: string, password: string, role: string) => {
    if (role === "researcher") {
      await api.post("/api/research-studio", {
        action: "register_researcher",
        email,
        full_name: fullName,
        password,
      });
    } else {
      await api.post("/api/auth/register", {
        email,
        full_name: fullName,
        password,
        role,
      });
    }
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    const storedToken = localStorage.getItem("naijamed_token");
    if (storedToken) api.post("/api/auth/logout").catch(() => undefined);
    localStorage.removeItem("naijamed_token");
    localStorage.removeItem("naijamed_refresh");
    localStorage.removeItem("naijamed_user");
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    if (!token) return;
    api.get<User>("/api/auth/me")
      .then(({ data }) => setUser(data))
      .catch(() => {
        localStorage.removeItem("naijamed_token");
        localStorage.removeItem("naijamed_refresh");
        localStorage.removeItem("naijamed_user");
        setToken(null);
        setUser(null);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated: !!token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
