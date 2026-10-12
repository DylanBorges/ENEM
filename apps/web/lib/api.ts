export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1";

export function token(): string | null {
  return typeof window === "undefined" ? null : sessionStorage.getItem("access_token");
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const accessToken = token();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  // Wake a sleeping free backend before sending a write. Replaying POST after
  // a lost response could create a duplicate account, attempt, or essay.
  if (method !== "GET" && method !== "HEAD" && path !== "/health/ready") {
    await waitForBackend();
  }

  let response: Response | null = null;
  const maxAttempts = method === "GET" || method === "HEAD" ? 18 : 1;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
      const isJson = response.headers.get("Content-Type")?.includes("application/json");
      if (response.ok && isJson) break;
      if (!response.ok && ![502, 503, 504].includes(response.status)) break;
    } catch {
      response = null;
    }
    if (attempt < maxAttempts) await delay(Math.min(attempt * 1000, 5000));
  }

  if (!response) {
    throw new Error("O servidor não respondeu. Aguarde um minuto e tente novamente.");
  }

  if (response.ok && !response.headers.get("Content-Type")?.includes("application/json")) {
    throw new Error("O servidor ainda está iniciando. Tente novamente em instantes.");
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : `Erro HTTP ${response.status}`);
  }
  return body as T;
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForBackend(): Promise<void> {
  for (let attempt = 1; attempt <= 18; attempt++) {
    try {
      const response = await fetch(`${API_URL.replace(/\/v1\/?$/, "")}/health/ready`, { cache: "no-store" });
      if (response.ok) return;
      if (![502, 503, 504].includes(response.status)) break;
    } catch {
      // A sleeping service may not accept connections yet.
    }
    if (attempt < 18) await delay(Math.min(attempt * 1000, 5000));
  }
  throw new Error("O servidor não respondeu. Aguarde um minuto e tente novamente.");
}
