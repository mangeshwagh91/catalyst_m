/**
 * useAuth Hook - Authentication state management
 * Provides user info, login/logout functions, and loading state
 */

import { useState, useEffect, useCallback } from "react";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
}

interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  token: string | null;
}

const STORAGE_KEY = "auth_token";
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export const useAuth = () => {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    token: null,
  });

  // Load token from localStorage and verify on mount
  useEffect(() => {
    const loadAuth = async () => {
      const token = localStorage.getItem(STORAGE_KEY);

      if (token) {
        try {
          // Verify token is still valid by calling /auth/me
          const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          });

          if (response.ok) {
            const user = await response.json();
            setState({
              user,
              isLoading: false,
              isAuthenticated: true,
              token,
            });
          } else {
            // Token is invalid, clear it
            localStorage.removeItem(STORAGE_KEY);
            setState({
              user: null,
              isLoading: false,
              isAuthenticated: false,
              token: null,
            });
          }
        } catch (error) {
          console.error("Auth verification failed:", error);
          localStorage.removeItem(STORAGE_KEY);
          setState({
            user: null,
            isLoading: false,
            isAuthenticated: false,
            token: null,
          });
        }
      } else {
        setState((prev) => ({ ...prev, isLoading: false }));
      }
    };

    loadAuth();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setState((prev) => ({ ...prev, isLoading: true }));

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Login failed");
      }

      const data = await response.json();
      localStorage.setItem(STORAGE_KEY, data.access_token);

      setState({
        user: {
          id: data.user_id,
          email: data.username,
          full_name: data.full_name,
        },
        isLoading: false,
        isAuthenticated: true,
        token: data.access_token,
      });

      return data;
    } catch (error) {
      setState((prev) => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const register = useCallback(async (email: string, password: string, full_name: string) => {
    setState((prev) => ({ ...prev, isLoading: true }));

    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password, full_name }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Registration failed");
      }

      const data = await response.json();
      localStorage.setItem(STORAGE_KEY, data.access_token);

      setState({
        user: {
          id: data.user_id,
          email: data.username,
          full_name: data.full_name,
        },
        isLoading: false,
        isAuthenticated: true,
        token: data.access_token,
      });

      return data;
    } catch (error) {
      setState((prev) => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setState({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      token: null,
    });
  }, []);

  return {
    ...state,
    login,
    register,
    logout,
  };
};
