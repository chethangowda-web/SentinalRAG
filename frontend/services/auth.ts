import { api } from "./api";

export interface UserResponse {
  id: string;
  name: string;
  email: string;
  created_at: string | null;
  total_documents?: number;
  total_sessions?: number;
  total_evaluations?: number;
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

export async function logoutUser(): Promise<void> {
  await api.post("/api/v1/auth/logout");
}

export async function getMe(): Promise<UserResponse> {
  const res = await api.get<UserResponse>("/api/v1/auth/me");
  return res.data;
}
