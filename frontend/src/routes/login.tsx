/**
 * Login Page - Authentication UI
 * Allows users to login or register a new account
 */

import { useState } from "react";
import { useNavigate, createFileRoute } from "@tanstack/react-router";
import { useAuthContext } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

type AuthMode = "login" | "register";

export const LoginPage = () => {
  const navigate = useNavigate();
  const auth = useAuthContext();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      if (mode === "login") {
        await auth.login(email, password);
      } else {
        await auth.register(email, password, fullName);
      }
      // Redirect to workspace on success
      navigate({ to: "/workspace" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-2xl">
        <div className="p-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Catalyst AI</h1>
          <p className="text-slate-600">
            {mode === "login" ? "Sign in to your account" : "Create a new account"}
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
              Email Address
            </label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          {/* Full Name (Register only) */}
          {mode === "register" && (
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-slate-700 mb-2">
                Full Name
              </label>
              <Input
                id="fullName"
                type="text"
                placeholder="John Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
          )}

          {/* Password */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
              Password
            </label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isLoading}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2 rounded-lg transition-colors"
          >
            {isLoading ? "Loading..." : mode === "login" ? "Sign In" : "Create Account"}
          </Button>
        </form>

        {/* Mode Toggle */}
        <div className="mt-6 text-center">
          <p className="text-slate-600 text-sm">
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError("");
                setEmail("");
                setPassword("");
                setFullName("");
              }}
              className="text-purple-600 hover:text-purple-700 font-semibold transition-colors"
            >
              {mode === "login" ? "Sign up" : "Sign in"}
            </button>
          </p>
        </div>

        {/* Test Credentials */}
        {mode === "login" && (
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-blue-700 text-xs font-medium mb-2">Demo Credentials:</p>
            <p className="text-blue-600 text-xs">Email: demo@example.com</p>
            <p className="text-blue-600 text-xs">Password: demo123</p>
          </div>
        )}
      </Card>
    </div>
  );
};
