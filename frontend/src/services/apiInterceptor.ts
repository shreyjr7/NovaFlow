// src/services/apiInterceptor.ts
// Global API Interceptor for NovaFlow Urban Fleet Platform
// Automatically reroutes relative /api/... calls to configured backend (localtunnel, Render, Railway, or local)

import { getBackendBaseUrl } from "./roadScanApi";

let isInterceptorInstalled = false;

/**
 * Installs a transparent fetch interceptor that:
 * 1. Rewrites relative `/api/...` calls to the configured backend base URL.
 * 2. Rewrites hardcoded `http://localhost:8000/api/...` calls to the active backend URL.
 * 3. Injects headers (`bypass-tunnel-reminder`, `ngrok-skip-browser-warning`) so tunneling services
 *    do not display interstitial HTML warning pages to API fetch calls.
 */
export function setupApiInterceptor(): void {
  if (isInterceptorInstalled) return;
  if (typeof window === "undefined" || !window.fetch) return;

  const originalFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    let url: string;
    if (typeof input === "string") {
      url = input;
    } else if (input instanceof URL) {
      url = input.toString();
    } else if (input && typeof (input as Request).url === "string") {
      url = (input as Request).url;
    } else {
      return originalFetch(input, init);
    }

    const backendBase = getBackendBaseUrl();

    if (backendBase) {
      if (url.startsWith("/api/")) {
        url = `${backendBase}${url}`;
      } else if (url.startsWith("http://localhost:8000/api/")) {
        url = url.replace("http://localhost:8000", backendBase);
      }
    }

    // Tunnel bypass headers for localtunnel, ngrok, cloudflare tunnels
    const isTunnel =
      url.includes("loca.lt") ||
      url.includes("ngrok") ||
      url.includes("trycloudflare") ||
      (backendBase && (backendBase.includes("loca.lt") || backendBase.includes("ngrok")));

    if (isTunnel) {
      const headers = new Headers(init?.headers || {});
      if (!headers.has("bypass-tunnel-reminder")) {
        headers.set("bypass-tunnel-reminder", "true");
      }
      if (!headers.has("ngrok-skip-browser-warning")) {
        headers.set("ngrok-skip-browser-warning", "true");
      }
      return originalFetch(url, { ...init, headers });
    }

    if (url !== (typeof input === "string" ? input : "")) {
      return originalFetch(url, init);
    }

    return originalFetch(input, init);
  };

  isInterceptorInstalled = true;
  console.info("NovaFlow API Interceptor active. Backend base:", getBackendBaseUrl() || "(default relative)");
}
