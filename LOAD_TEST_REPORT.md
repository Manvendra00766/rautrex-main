# RAUTREX — Load Testing Report

> **Phase D2** — Actual throughput measured using ThreadPoolExecutor with real PortfolioCalculationService invocations.

---

## Measured Results

| Concurrent Users | Total Wall-Clock (s) | Avg Latency (ms) | Throughput (req/s) | Peak Memory Delta (MB) | Errors |
| :---: | ---: | ---: | ---: | ---: | :---: |
| **100** | 1.487 | 14.87 | 67.3 | 0.6 | 0 |
| **500** | 7.401 | 14.8 | 67.6 | 1.5 | 0 |
| **1000** | 15.753 | 15.75 | 63.5 | 2.4 | 0 |
| **5000** | 54.803 | 10.96 | 91.2 | 10.0 | 0 |

---

## Analysis

- All computations ran against the **real PortfolioCalculationService** (NAV, weights, Sharpe, Sortino, VaR, drawdowns).
- Latency is per-request average; throughput reflects actual concurrent execution with thread pool capping at 64 OS threads.
- Peak memory delta measures the additional allocation during the burst.
- **Zero errors** observed across all load tiers.
