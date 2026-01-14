'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';
import { ROUTES } from '@/lib/constants';

export function useAuth() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading, checkAuth, logout } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return {
    user,
    isAuthenticated,
    isLoading,
    logout: async () => {
      await logout();
      router.push(ROUTES.login);
    },
  };
}

export function useRequireAuth(redirectTo = ROUTES.login) {
  const router = useRouter();
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();

  useEffect(() => {
    const verify = async () => {
      const authenticated = await checkAuth();
      if (!authenticated && !isLoading) {
        router.push(redirectTo);
      }
    };
    verify();
  }, [checkAuth, isLoading, redirectTo, router]);

  return { isAuthenticated, isLoading };
}

export function useRedirectIfAuthenticated(redirectTo = ROUTES.dashboard) {
  const router = useRouter();
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    const verify = async () => {
      const authenticated = await checkAuth();
      if (authenticated) {
        router.push(redirectTo);
      }
    };
    verify();
  }, [checkAuth, redirectTo, router]);

  return { isAuthenticated };
}

export function useUser() {
  const { user, fetchUser, isLoading } = useAuthStore();

  useEffect(() => {
    if (!user) {
      fetchUser();
    }
  }, [user, fetchUser]);

  return { user, isLoading };
}

export function usePermissions() {
  const { user } = useAuthStore();

  const hasRole = (requiredRole: string) => {
    if (!user) return false;
    const roleHierarchy: Record<string, number> = {
      admin: 4,
      manager: 3,
      operator: 2,
      viewer: 1,
    };
    return (roleHierarchy[user.role] || 0) >= (roleHierarchy[requiredRole] || 0);
  };

  return {
    isAdmin: user?.role === 'admin',
    isManager: hasRole('manager'),
    canRunTools: hasRole('operator'),
    canView: hasRole('viewer'),
    hasRole,
  };
}
