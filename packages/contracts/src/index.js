/**
 * Type-safe Contract-First HTTP Client for DBazar Web, POS, and Mobile apps.
 * Automatically attaches Bearer JWT and `X-Correlation-ID` headers.
 */
import crypto from "node:crypto";

export class DbazarApiClient {
  constructor(options) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.getToken = options.getToken;
    this.fetchImpl = options.fetchImpl || globalThis.fetch;
  }

  async call(_operationId, method, routePath, payload, correlationId) {
    const headers = {
      "Content-Type": "application/json",
      "X-Correlation-ID": correlationId || crypto.randomUUID(),
    };
    const token = this.getToken?.();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await this.fetchImpl(`${this.baseUrl}${routePath}`, {
      method,
      headers,
      body: payload !== undefined && method !== "GET" ? JSON.stringify(payload) : undefined,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || `API xatoligi (${response.status})`);
    }
    return data;
  }
}
