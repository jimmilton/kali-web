import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi, User } from '@/lib/api';
import { setTokens, removeTokens, getAccessToken, isTokenExpired, getRefreshToken } from '@/lib/auth';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;

  login: (username: string, password: string, mfaCode?: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  fetchUser: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
  checkAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,

      login: async (username: string, password: string, mfaCode?: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.login(username, password, mfaCode);
          setTokens(response.access_token, response.refresh_token);
          const user = await authApi.me();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) {
          const err = error as { status?: number; detail?: string };
          // Check if MFA is required (428 status)
          if (err.status === 428) {
            set({ isLoading: false });
            throw { mfaRequired: true, status: 428, detail: err.detail };
          }
          const message = err.detail || (error instanceof Error ? error.message : 'Login failed');
          set({ error: message, isLoading: false, isAuthenticated: false });
          throw error;
        }
      },

      register: async (email: string, username: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.register({ email, username, password });
          setTokens(response.access_token, response.refresh_token);
          const user = await authApi.me();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Registration failed';
          set({ error: message, isLoading: false, isAuthenticated: false });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          const refreshToken = getRefreshToken();
          if (refreshToken) {
            await authApi.logout(refreshToken);
          }
        } catch {
          // Ignore logout errors
        } finally {
          removeTokens();
          set({ user: null, isAuthenticated: false, isLoading: false, error: null });
        }
      },

      refreshToken: async () => {
        const refreshToken = getRefreshToken();
        if (!refreshToken) {
          set({ isAuthenticated: false, user: null });
          return false;
        }

        try {
          const response = await authApi.refresh(refreshToken);
          setTokens(response.access_token, response.refresh_token);
          return true;
        } catch {
          removeTokens();
          set({ isAuthenticated: false, user: null });
          return false;
        }
      },

      fetchUser: async () => {
        set({ isLoading: true });
        try {
          const user = await authApi.me();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch {
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },

      refreshUser: async () => {
        try {
          const user = await authApi.me();
          set({ user });
        } catch {
          // Silently fail - user data will be stale but still usable
        }
      },

      clearError: () => set({ error: null }),

      checkAuth: async () => {
        const token = getAccessToken();
        if (!token) {
          set({ isAuthenticated: false, user: null });
          return false;
        }

        if (isTokenExpired(token)) {
          const refreshed = await get().refreshToken();
          if (!refreshed) {
            return false;
          }
        }

        if (!get().user) {
          await get().fetchUser();
        }

        return get().isAuthenticated;
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
);
