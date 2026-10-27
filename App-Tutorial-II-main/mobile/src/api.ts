import { getAuth, getIdToken } from '@react-native-firebase/auth';
import { config } from './config';
import { Expr } from './expression';
import { Variable } from './distributions';
type BaseSpec = {
  title: string;
  variables: Variable[];
  samples: 100;
};
export type Spec = BaseSpec &
  ({ version: 1; expression: Expr } | { version: 2; expressions: Expr[] });
export const components = (spec: Spec): Expr[] =>
  spec.version === 1 ? [spec.expression] : spec.expressions;
export type Usage = {
  day_utc: string;
  used: number;
  limit: number;
  remaining: number;
  running: boolean;
  resets_at: string;
};
export type Summary = {
  id: string;
  title: string;
  created_at: string;
  color: string;
  dimensions: number;
};
export type Experiment = Summary & { results: number[]; spec: Spec };
export async function api<T>(
  path: string,
  method = 'GET',
  body?: Spec,
  key?: string,
  resource = '/v1/experiments',
): Promise<T> {
  const user = getAuth().currentUser;
  if (!user) throw Error('Inicia sesión con Google.');
  const token = await getIdToken(user),
    controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);
  try {
    const response = await fetch(config.apiUrl + resource + path, {
      method,
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...(key ? { 'Idempotency-Key': key } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw Error(
        typeof data.detail === 'string'
          ? data.detail
          : `Error ${response.status}. Reintenta.`,
      );
    }
    return response.status === 204 ? (undefined as T) : await response.json();
  } catch (e) {
    if (e instanceof Error && e.name === 'AbortError')
      throw Error(
        'Se agotó la espera de red. Actualiza la lista antes de reintentar: el servidor pudo haber guardado el experimento.',
      );
    throw e;
  } finally {
    clearTimeout(timeout);
  }
}
