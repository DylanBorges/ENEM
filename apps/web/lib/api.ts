export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

export function token(): string | null {
  return typeof window === "undefined" ? null : sessionStorage.getItem("access_token");
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const accessToken = token();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  let response: Response | null = null;
  const maxAttempts = 3;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
      break;
    } catch (caught) {
      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, attempt * 250));
      }
    }
  }

  if (!response) {
    throw new Error("Não foi possível conectar à API. Verifique se o servidor está ativo.");
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : `Erro HTTP ${response.status}`);
  }
  return body as T;
}
