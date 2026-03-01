"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import LoadingState from "@/src/components/data/LoadingState";
import { AuthContext } from "@/src/components/auth/AuthContext";

type AuthGateClientProps = {
  locale: string;
  children: ReactNode;
};

const ACCESS_TOKEN_KEYS = ["access", "access_token", "token"];
const REFRESH_TOKEN_KEYS = ["refresh", "refresh_token"];

function readAccessTokenFromStorage(): string | null {
  for (const key of ACCESS_TOKEN_KEYS) {
    const value = localStorage.getItem(key);
    if (value) {
      return value;
    }
  }
  return null;
}

function readRefreshTokenFromStorage(): string | null {
  for (const key of REFRESH_TOKEN_KEYS) {
    const value = localStorage.getItem(key);
    if (value) {
      return value;
    }
  }
  return null;
}

export default function AuthGateClient({
  locale,
  children,
}: AuthGateClientProps) {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [authorized, setAuthorized] = useState(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);

  const loginPath = useMemo(() => `/${locale}/login`, [locale]);

  useEffect(() => {
    const token = readAccessTokenFromStorage();
    const refresh = readRefreshTokenFromStorage();

    if (!token) {
      setAccessToken(null);
      setRefreshToken(null);
      setAuthorized(false);
      setChecking(false);
      router.replace(loginPath);
      return;
    }

    setAccessToken(token);
    setRefreshToken(refresh);
    setAuthorized(true);
    setChecking(false);
  }, [loginPath, router]);

  const setTokens = (nextAccessToken: string, nextRefreshToken?: string | null) => {
    localStorage.setItem("access_token", nextAccessToken);
    setAccessToken(nextAccessToken);

    if (nextRefreshToken) {
      localStorage.setItem("refresh_token", nextRefreshToken);
      setRefreshToken(nextRefreshToken);
    }
  };

  const clearTokens = () => {
    for (const key of ACCESS_TOKEN_KEYS) {
      localStorage.removeItem(key);
    }
    for (const key of REFRESH_TOKEN_KEYS) {
      localStorage.removeItem(key);
    }
    setAccessToken(null);
    setRefreshToken(null);
    setAuthorized(false);
    router.replace(loginPath);
  };

  if (checking || !authorized) {
    return <LoadingState />;
  }

  return (
    <AuthContext.Provider value={{ accessToken, refreshToken, setTokens, clearTokens }}>
      {children}
    </AuthContext.Provider>
  );
}
