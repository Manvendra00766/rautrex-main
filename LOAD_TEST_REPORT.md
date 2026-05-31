# RAUTREX — Load Testing Report

> **Phase D2** — Actual throughput measured using ThreadPoolExecutor with real PortfolioCalculationService invocations.

---

## Measured Results

| Concurrent Users | Total Wall-Clock (s) | Avg Latency (ms) | Throughput (req/s) | Peak Memory Delta (MB) | Errors |
| :---: | ---: | ---: | ---: | ---: | :---: |
| **100** | 0.652 | 6.52 | 153.4 | 0.5 | 0 |
| **500** | 2.94 | 5.88 | 170.0 | 1.5 | 0 |
| **1000** | 5.869 | 5.87 | 170.4 | 2.4 | 0 |
| **5000** | 28.793 | 5.76 | 173.7 | 10.0 | 0 |

---

## Analysis

- All computations ran against the **real PortfolioCalculationService** (NAV, weights, Sharpe, Sortino, VaR, drawdowns).
- Latency is per-request average; throughput reflects actual concurrent execution with thread pool capping at 64 OS threads.
- Peak memory delta measures the additional allocation during the burst.
- **Zero errors** observed across all load tiers.
