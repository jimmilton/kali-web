const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function removeTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

export function parseJwt(token: string): JwtPayload | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = parseJwt(token);
  if (!payload || !payload.exp) return true;
  return Date.now() >= payload.exp * 1000;
}

export function getTokenExpiry(token: string): Date | null {
  const payload = parseJwt(token);
  if (!payload || !payload.exp) return null;
  return new Date(payload.exp * 1000);
}

export function getUserIdFromToken(token: string): string | null {
  const payload = parseJwt(token);
  return payload?.sub || null;
}

export function getUserRoleFromToken(token: string): string | null {
  const payload = parseJwt(token);
  return payload?.role || null;
}

export interface JwtPayload {
  sub: string;
  exp: number;
  iat: number;
  role?: string;
  email?: string;
}

export type UserRole = 'admin' | 'manager' | 'operator' | 'viewer';

export const ROLE_HIERARCHY: Record<UserRole, number> = {
  admin: 4,
  manager: 3,
  operator: 2,
  viewer: 1,
};

export function hasRole(userRole: UserRole, requiredRole: UserRole): boolean {
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[requiredRole];
}

export function canManageUsers(role: UserRole): boolean {
  return hasRole(role, 'admin');
}

export function canManageProjects(role: UserRole): boolean {
  return hasRole(role, 'manager');
}

export function canRunTools(role: UserRole): boolean {
  return hasRole(role, 'operator');
}

export function canViewData(role: UserRole): boolean {
  return hasRole(role, 'viewer');
}
