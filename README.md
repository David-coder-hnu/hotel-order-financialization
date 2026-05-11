# Future Service Rights (FSR)

### A New Asset Class for Service-Capacity Securitization

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Working%20Paper-brightgreen.svg)]()

**Tokenizing tomorrow's hotel rooms today.**  
Not digitizing existing assets (RWA). Creating new ones.

---

## What Is This?

A hotel room-night on June 15 has economic value today — but that value is trapped. The hotel can't sell it forward. Investors can't buy exposure to hotel demand without owning property. Consumers can't lock in prices.

**Future Service Rights (FSR)** solves this. We define a Time-Right as a tokenized claim on a future hotel room-night. It trades on secondary markets. It settles via cash, discounted physical stay, or transfer. And critically — holders can sell at **any time**, applying proceeds directly as booking credit toward **any** hotel reservation.

The discount is market-driven, not hotel-funded. The hotel pays zero commission. OTA takes 15–25%. Time-Right takes 0%.

---

## Key Findings

| Metric | Value |
|--------|-------|
| **System value created** | ¥1,227 per Time-Right (positive-sum) |
| **Hotel revenue vs. OTA** | +56% annually (¥35.2M vs. ¥22.6M per hotel-year) |
| **Senior tranche rating** | Aa–A (EL 0.16%, VaR99 3.98%) under calibrated PDs |
| **User booking discount** | 4.4% market-driven (hotel pays ¥0) |
| **Investor nominal return** | ~73% for bearing default + liquidity risk |
| **Data scale** | 16,257 hotels · 1.7M price records · Chengdu, China |

### Stakeholder Distribution (per Time-Right)

```
Hotels      +¥817  (66.6%)  — guaranteed revenue, zero OTA, zero debt
Users       +¥221  (18.0%)  — market-driven booking discounts
Platform    +¥98   ( 8.0%)  — wholesale-retail spread + trading fees
Investors   +¥91   ( 7.4%)  — 73% return for risk-bearing
─────────────────────────────────────────────
System      +¥1,227/TR       — positive-sum coordination
```

---

## Architecture

```
                    ┌──────────────┐
                    │   PLATFORM   │
                    │ (Market Maker)│
                    └──┬───────┬───┘
           wholesale  │       │  retail
           P_issue    │       │  P_retail
          (¥1,174)    │       │  (¥1,268)
               ┌──────┘       └──────┐
               ▼                      ▼
        ┌──────────┐          ┌──────────┐
        │  HOTELS  │          │  USERS/  │
        │          │          │ INVESTORS│
        └──────────┘          └────┬─────┘
              │                    │
              │    Secondary       │
              │    Market          │
              └────────────────────┘
                   P_secondary
                   (market-driven)
```

### Settlement Mechanisms

| Mechanism | When | Discount Source | User Share |
|-----------|------|----------------|------------|
| **Continuous Offset** (primary) | Anytime | Market supply/demand | 45% |
| Ternary Physical (floor) | At maturity | Fixed α = 0.70 | 30% |
| Cash / Transfer | At maturity | Contractual / market | 25% |

---

## Credit Risk: Resolved

Three structural models produced PDs spanning **9.8% → 49.4% → 98.2%** — a 10× range indicating model failure.

We resolved this by constructing a **data-calibrated PD model** from the survival analysis of 14,851 hotels tracked over four months:

| Tier | Calibrated PD | Source |
|------|-------------|--------|
| Economy | 15.7% | 9.0% 3-month platform exit |
| Comfort | 6.8% | 3.6% 3-month platform exit |
| Upscale | 2.5% | 1.3% 3-month platform exit |
| Luxury | 0.5% | 0.0% 3-month platform exit |

Under calibrated PDs, Monte Carlo simulation (2,000 paths) yields:

| PD Model | Pool PD | Senior EL | Senior VaR99 | Rating |
|----------|---------|-----------|-------------|--------|
| **Calibrated** | **9.7%** | **0.16%** | **3.98%** | **Aa–A** |
| KMV | 9.8% | 0.09% | 1.98% | Aa |
| Merton (capped) | 49.4% | 1.61% | 37.12% | Ba–B |

Senior tranche is solidly investment-grade under our best empirical estimate.

---

## Project Structure

```
├── src/
│   ├── hotel_abs_engine_fusion.py    # Main engine (V6-Fusion)
│   ├── credit_model.py               # Merton DD + GARCH (configurable guards)
│   ├── monte_carlo_simulator.py      # tqdm + joblib parallel MC
│   ├── robustness_checks.py          # KMV + t-Copula + Bootstrap
│   ├── waterfall_engine.py           # Sequential-pay waterfall
│   ├── tranche_structure.py          # ABS tranche design
│   ├── asset_pool.py                 # Stratified sampling
│   ├── time_right_pool.py            # Time-Right issuance parameters
│   ├── model_params.py               # Centralized parameter management
│   ├── manual_verification.py        # 3-hotel hand-calculation verification
│   └── config.py                     # Path configuration
├── output/
│   ├── fsr_framework_paper.pdf       # Academic paper (24pp)
│   ├── fsr_paper_guide.pdf           # Beginner's guide in Chinese (24pp)
│   ├── fsr_project_summary.html      # Interactive HTML dashboard
│   ├── abs_report_v6_fusion.json     # Full engine output
│   └── figures/                      # Publication-quality figures
├── data/                             # 1.7M Chengdu hotel price records
└── README.md
```

---

## Quick Start

```bash
pip install pandas numpy scipy matplotlib tqdm joblib
python src/hotel_abs_engine_fusion.py
```

**Modify parameters:**
```python
from hotel_abs_engine_fusion import HotelTimeRightABSEngine
engine = HotelTimeRightABSEngine()
engine.issue_discount = 0.10     # Adjust wholesale discount
engine.run_full_analysis(pool_size=80, n_paths=5000)
```

**Run robustness checks:**
```python
from robustness_checks import CopulaSensitivityAnalyzer
# Gaussian vs. t-Copula · Rho sensitivity · Bootstrap CI
```

**Customize credit model:**
```python
from credit_model import HotelCreditModel
model = HotelCreditModel(prices, info, pd_cap=None,          # Remove PD ceiling
                         default_barrier_ratio=0.65)         # Adjust barrier
```

---

## Why This Matters

**For hotels:** 56% more annual revenue than OTA distribution. Guaranteed. Zero commission. No debt.

**For users:** Market-driven booking discounts (4.4%). Funded by secondary-market liquidity — not hotel margin compression.

**For investors:** Exposure to a new, diversifying asset class. Senior tranche rated Aa–A.

**For platforms:** Asset-light infrastructure. 5× fee differential steers users toward value-recycling within the ecosystem.

**For the industry:** A research program. FSR generalizes beyond hotels — flights, events, coworking. This paper is the foundation.

---

## Documentation

| Document | Description |
|----------|-------------|
| [`fsr_framework_paper.pdf`](output/fsr_framework_paper.pdf) | Academic paper (24pp, English) |
| [`fsr_paper_guide.pdf`](output/fsr_paper_guide.pdf) | Beginner's guide (24pp, Chinese) |
| [`fsr_project_summary.html`](output/fsr_project_summary.html) | Interactive dashboard |

---

## Citation

```bibtex
@article{fsr2026,
  title   = {Future Service Rights: Tokenization, Pricing, and Structuring
             — Theory and Evidence from the Chengdu Hotel Market},
  author  = {Hotel Finance Research Group},
  journal = {Working Paper},
  year    = {2026}
}
```

## License

MIT — see [LICENSE](LICENSE).

---

*The FSR framework is not merely a paper about hotel securitization.*  
*It is the foundation of a research program on generalized service-capacity financialization.*
