/**
 * DBazar Phase 5 High-Load Stress Test (`k6 run deploy/k6/load-test.js`)
 * Target SLA (reja.md Section 4 & 5.1): 1,000+ RPS with p95 latency < 200ms.
 */
import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    high_load_b2b_and_pos: {
      executor: "constant-arrival-rate",
      rate: 1000,
      timeUnit: "1s",
      duration: "60s",
      preAllocatedVUs: 100,
      maxVUs: 500,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.001"],
    http_req_duration: ["p(95)<200"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8001";

export default function () {
  const res = http.get(`${BASE_URL}/api/v1/catalog/offers`);
  check(res, {
    "status is 200": (r) => r.status === 200,
    "has correlation id": (r) => Boolean(r.headers["X-Correlation-Id"]),
  });
}
