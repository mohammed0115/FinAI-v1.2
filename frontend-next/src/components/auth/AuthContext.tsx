"use client";

import { createContext, useContext } from "react";

type AuthContextValue = {
  accessToken: string | null;
  refreshToken: string | null;
  setTokens: (accessToken: string, refreshToken?: string | null) => void;
  clearTokens: () => void;
};

const noop = () => undefined;

const defaultValue: AuthContextValue = {
  accessToken: null,
  refreshToken: null,
  setTokens: noop,
  clearTokens: noop,
};

export const AuthContext = createContext<AuthContextValue>(defaultValue);

export function useAuthContext() {
  return useContext(AuthContext);
}
