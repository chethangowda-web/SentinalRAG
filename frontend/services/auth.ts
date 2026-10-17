import { api } from "./api";

export interface UserResponse {
  id: string;
  name: string;
  email: string;
  created_at: string | null;
  total_documents?: number;
  total_sessions?: number;
  total_evaluations?: number;
  is_admin?: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  invite_code?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export async function registerUser(data: RegisterRequest): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>("/api/v1/auth/register", data);
  return res.data;
}

export async function loginUser(data: LoginRequest): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>("/api/v1/auth/login", data);
  return res.data;
}

export interface AuthConfig {
  registration_requires_code: boolean;
  password_reset_available: boolean;
}

export async function getAuthConfig(): Promise<AuthConfig> {
  const res = await api.get("/api/v1/auth/config");
  return res.data;
}

export async function forgotPassword(email: string): Promise<void> {
  await api.post("/api/v1/auth/forgot-password", { email });
}

export async function resetPassword(token: string, password: string): Promise<void> {
  await api.post("/api/v1/auth/reset-password", { token, password });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>("/api/v1/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return res.data;
}

export async function logoutEverywhere(): Promise<void> {
  await api.post("/api/v1/auth/logout-everywhere");
}

export async function deleteAccount(password: string): Promise<void> {
  await api.delete("/api/v1/auth/me", { data: { password } });
}

export async function logoutUser(): Promise<void> {
  await api.post("/api/v1/auth/logout");
}

export async function getMe(): Promise<UserResponse> {
  const res = await api.get<UserResponse>("/api/v1/auth/me");
  return res.data;
}
