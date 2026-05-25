"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import {
  clearStoredToken,
  getMe,
  getStoredToken,
  login as apiLogin,
  setStoredToken,
} from "@/lib/api";
import type { UserResponse } from "@/lib/types";

type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: UserResponse | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<UserResponse>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const router = useRouter();

  const loadMe = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setStatus("anonymous");
      return;
    }
    try {
      const me = await getMe();
      setUser(me);
      setStatus("authenticated");
    } catch {
      clearStoredToken();
      setUser(null);
      setStatus("anonymous");
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await apiLogin(email, password);
      setStoredToken(data.access_token);
      setUser(data.user);
      setStatus("authenticated");
      return data.user;
    },
    []
  );

  const logout = useCallback(() => {
    clearStoredToken();
    setUser(null);
    setStatus("anonymous");
    router.replace("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, logout, refresh: loadMe }),
    [user, status, login, logout, loadMe]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
