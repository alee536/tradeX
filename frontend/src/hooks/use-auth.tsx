import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { UserProfile, AuthResponse, LoginInput, RegisterInput } from "@workspace/api-client-react";

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

  useEffect(() => {
    const storedToken = localStorage.getItem("24tradex_token");
    const storedUser = localStorage.getItem("24tradex_user");

    const bootstrapAuth = async () => {
      if (storedToken && storedUser) {
        try {
          setToken(storedToken);
          const cachedUser = JSON.parse(storedUser);
          setUser(cachedUser);

          const response = await fetch("/api/profile", {
            headers: {
              Authorization: `Bearer ${storedToken}`,
            },
          });

          if (response.ok) {
            const profile = await response.json();
            setUser(profile);
            localStorage.setItem("24tradex_user", JSON.stringify(profile));
          }
        } catch (e) {
          localStorage.removeItem("24tradex_token");
          localStorage.removeItem("24tradex_user");
          setToken(null);
          setUser(null);
        }
      }

      setIsLoading(false);
    };

    void bootstrapAuth();
  }, []);

  const login = (data: AuthResponse) => {
    setToken(data.token);
    setUser(data.user);
    localStorage.setItem("24tradex_token", data.token);
    localStorage.setItem("24tradex_user", JSON.stringify(data.user));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("24tradex_token");
    localStorage.removeItem("24tradex_user");
    window.location.href = "/login";
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
