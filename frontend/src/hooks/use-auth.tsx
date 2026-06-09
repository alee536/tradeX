import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { UserProfile, AuthResponse, setUnauthorizedHandler } from "@workspace/api-client-react";
import {
  AUTH_TOKEN_KEY,
  AUTH_USER_KEY,
  clearAuthSession,
  getStoredAuthToken,
  redirectToLoginAfterSessionExpiry,
} from "@/lib/auth-session";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  login: (data: AuthResponse) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(() => {
    clearAuthSession();
    setToken(null);
    setUser(null);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    window.location.href = "/login";
  }, [clearSession]);

  const handleSessionExpired = useCallback(() => {
    clearSession();
    redirectToLoginAfterSessionExpiry();
  }, [clearSession]);

  useEffect(() => {
    setUnauthorizedHandler(handleSessionExpired);
    return () => setUnauthorizedHandler(null);
  }, [handleSessionExpired]);

  useEffect(() => {
    const storedToken = getStoredAuthToken();
    const storedUser = localStorage.getItem(AUTH_USER_KEY);

    const bootstrapAuth = async () => {
      if (storedToken && storedUser) {
        try {
          setToken(storedToken);
          setUser(JSON.parse(storedUser));

          const response = await fetch("/api/profile", {
            headers: {
              Authorization: `Bearer ${storedToken}`,
            },
          });

          if (response.ok) {
            const profile = await response.json();
            setUser(profile);
            localStorage.setItem(AUTH_USER_KEY, JSON.stringify(profile));
          } else if (response.status === 401) {
            clearSession();
          }
        } catch {
          clearSession();
        }
      }

      setIsLoading(false);
    };

    void bootstrapAuth();
  }, [clearSession]);

  const login = (data: AuthResponse) => {
    setToken(data.token);
    setUser(data.user);
    localStorage.setItem(AUTH_TOKEN_KEY, data.token);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.user));
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
