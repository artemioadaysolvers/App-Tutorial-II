import type { Messages, SavedMessage, Session, User } from './types';

const baseUrl = (process.env.EXPO_PUBLIC_API_URL || '').replace(/\/+$/, '');
export const webClientId = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID || '';

export function configurationIssue(): string | null {
  if (!baseUrl || baseUrl.includes('TU-BACKEND')) return 'Configura EXPO_PUBLIC_API_URL en .env y vuelve a compilar.';
  if (!baseUrl.startsWith('https://') && !(__DEV__ && baseUrl.startsWith('http://'))) return 'El servidor debe usar https://.';
  if (!webClientId.endsWith('.apps.googleusercontent.com') || webClientId.includes('REEMPLAZAR')) return 'Configura el cliente de Google en .env y vuelve a compilar.';
  return null;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

async function request<T>(path: string, token?: string, body?: unknown): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25000);
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }), signal: controller.signal,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new ApiError(typeof data.detail === 'string' ? data.detail : 'El servidor no pudo procesar el envío.', response.status);
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('No pudimos conectar con el servidor. Revisa tu conexión y vuelve a intentar.', 0);
  } finally { clearTimeout(timeout); }
}

export const signInApi = (idToken: string) => request<Session>('/api/v1/auth/google', undefined, { idToken });
export const getMe = (token: string) => request<User>('/api/v1/me', token);
export const sendMessages = (token: string, requestId: string, values: Messages) => request<SavedMessage>('/api/v1/messages', token, { requestId, ...values });
