/**
 * AuthContext and AuthProvider - Global authentication state management
 * Wraps the entire application to provide authentication state to all components
 */

import { createContext, useContext, ReactNode } from "react";
import { useAuth } from "../hooks/useAuth";

export interface AuthContextType extends ReturnType<typeof useAuth> {
  // Exported from useAuth hook
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const auth = useAuth();

  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
};

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return context;
};
