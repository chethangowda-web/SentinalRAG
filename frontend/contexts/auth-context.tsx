"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { getStoredToken, setStoredToken, clearStoredToken } from "@/services/api";
import {
  loginUser,
  registerUser,
  logoutUser,
  getMe,
  type UserResponse,
  type RegisterRequest,
  type LoginRequest,
} from "@/services/auth";

interface AuthContextType {
  user: UserResponse | null;
  loading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const userData = await getMe();
      setUser(userData);
    } catch {
      clearStoredToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (data: LoginRequest) => {
    const res = await loginUser(data);
    setStoredToken(res.access_token);
    setUser(res.user);
    router.push("/dashboard");
  }, [router]);

  const register = useCallback(async (data: RegisterRequest) => {
    const res = await registerUser(data);
    setStoredToken(res.access_token);
    setUser(res.user);
    router.push("/dashboard");
  }, [router]);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch {
      // ignore
    }
    clearStoredToken();
    setUser(null);
    router.push("/");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
