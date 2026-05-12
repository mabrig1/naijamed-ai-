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
    const raw = localStorage.getItem("nigerflora_user");
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(loadUser);
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("nigerflora_token")
  );

  const persist = useCallback((tokenData: Token) => {
    localStorage.setItem("nigerflora_token", tokenData.access_token);
    localStorage.setItem("nigerflora_refresh", tokenData.refresh_token);
    localStorage.setItem("nigerflora_user", JSON.stringify(tokenData.user));
    setToken(tokenData.access_token);
    setUser(tokenData.user);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<Token>("/api/auth/login", { email, password });
    persist(data);
  }, [persist]);

  const register = useCallback(
    async (email: string, fullName: string, password: string, role: string) => {
      await api.post("/api/auth/register", {
        email,
        full_name: fullName,
        password,
        role,
      });
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    const storedToken = localStorage.getItem("nigerflora_token");
    if (storedToken) {
      api.post("/api/auth/logout").catch(() => { /* fire-and-forget */ });
    }
    localStorage.removeItem("nigerflora_token");
    localStorage.removeItem("nigerflora_refresh");
    localStorage.removeItem("nigerflora_user");
    setToken(null);
    setUser(null);
  }, []);

  // Re-validate stored token against the server on mount to catch deactivated accounts
  // or tokens that were invalidated server-side. If /me fails we clear local state.
  useEffect(() => {
    if (!token) return;
    api.get<User>("/api/auth/me")
      .then(({ data }) => setUser(data))
      .catch(() => {
        localStorage.removeItem("nigerflora_token");
        localStorage.removeItem("nigerflora_refresh");
        localStorage.removeItem("nigerflora_user");
        setToken(null);
        setUser(null);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentionally runs once on mount only

  return (
    <AuthContext.Provider
      value={{ user, token, isAuthenticated: !!token, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
