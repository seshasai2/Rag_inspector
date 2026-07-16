/**
 * k6 stress — 1000 VUs against health/readiness endpoints.
 *
 * Usage:
 *   k6 run loadtests/k6/stress_1000.js
 *   k6 run -e BASE_URL=http://localhost:8000 loadtests/k6/stress_1000.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const liveTrend = new Trend("raginspector_live_duration", true);
const healthTrend = new Trend("raginspector_health_duration", true);
const readyTrend = new Trend("raginspector_ready_duration", true);

export const options = {
  stages: [
    { duration: "1m", target: 200 },
    { duration: "2m", target: 600 },
    { duration: "2m", target: 1000 },
    { duration: "2m", target: 1000 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(50)<600", "p(95)<2500", "p(99)<5000"],
    http_req_failed: ["rate<0.10"],
    checks: ["rate>0.90"],
  },
};

function hit(path, trend) {
  const res = http.get(`${BASE_URL}${path}`);
  trend.add(res.timings.duration);
  check(res, {
    [`${path} status is 200 or 503`]: (r) =>
      r.status === 200 || (path.includes("/ready") && r.status === 503),
  });
  return res;
}

export default function () {
  hit("/live", liveTrend);
  hit("/health", healthTrend);
  hit("/api/v1/ops/ready", readyTrend);
  sleep(0.1);
}

export function handleSummary(data) {
  const metrics = data.metrics || {};
  const pick = (name) => {
    const m = metrics[name];
    if (!m || !m.values) return {};
    return {
      p50: m.values["p(50)"],
      p95: m.values["p(95)"],
      p99: m.values["p(99)"],
    };
  };
  return {
    stdout: JSON.stringify(
      {
        scenario: "stress_1000vu",
        baseUrl: BASE_URL,
        http_req_duration: pick("http_req_duration"),
        live: pick("raginspector_live_duration"),
        health: pick("raginspector_health_duration"),
        ready: pick("raginspector_ready_duration"),
      },
      null,
      2
    ),
  };
}
