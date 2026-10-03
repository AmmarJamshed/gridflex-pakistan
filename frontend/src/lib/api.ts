const API_BASE = import.meta.env.VITE_API_URL ?? "";

export type TokenResponse = { access_token: string; token_type: string };

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/api/auth/token", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: (token: string) => request<any>("/api/auth/me", {}, token),
  gridStatus: () => request<any>("/api/grid/status"),
  zones: () => request<any[]>("/api/grid/zones"),
  marketSummary: () => request<any>("/api/market/summary"),
  offers: () => request<any[]>("/api/market/offers"),
  bids: () => request<any[]>("/api/market/bids"),
  transactions: () => request<any[]>("/api/market/transactions"),
  clearMarket: (token: string, zoneId?: string) =>
    request<any>(
      "/api/market/clear",
      { method: "POST", body: JSON.stringify({ zone_id: zoneId ?? null }) },
      token
    ),
  consumerDashboard: (token: string) => request<any>("/api/consumer/dashboard", {}, token),
  aggregatorDashboard: (token: string) => request<any>("/api/aggregator/dashboard", {}, token),
  wallet: (token: string) => request<any>("/api/wallet/me", {}, token),
  runSimulation: (body?: Record<string, number>) =>
    request<any>("/api/simulation/run", {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
  prices: () => request<any[]>("/api/pricing/daily"),
  forecasts: () => request<any>("/api/ai/forecasts"),
  anomalies: () => request<any>("/api/ai/anomalies"),
  fraudAlerts: () => request<any[]>("/api/fraud/alerts"),
  concept: () => request<any>("/api/concept/flexibility-accounting"),
  regulatory: () => request<any>("/api/concept/regulatory"),
  loadShift: (body: any) =>
    request<any>("/api/optimize/load-shift", { method: "POST", body: JSON.stringify(body) }),
  clearingExample: () => request<any>("/api/market/clearing-example"),
  participants: () => request<any[]>("/api/participants"),
  drEvents: () => request<any[]>("/api/dr/events"),
  config: () => request<any>("/api/admin/config"),
  updateConfig: (token: string, body: any) =>
    request<any>("/api/admin/config", { method: "PUT", body: JSON.stringify(body) }, token),
  triggerCongestion: (token: string, zone_code: string) =>
    request<any>(
      "/api/grid/trigger-congestion",
      { method: "POST", body: JSON.stringify({ zone_code, loading_factor: 0.98 }) },
      token
    ),
  createOffer: (token: string, body: any) =>
    request<any>("/api/market/offers", { method: "POST", body: JSON.stringify(body) }, token),
  createBid: (token: string, body: any) =>
    request<any>("/api/market/bids", { method: "POST", body: JSON.stringify(body) }, token),
};