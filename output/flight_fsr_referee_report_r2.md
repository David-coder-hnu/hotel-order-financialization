# Second-Round Referee Report: Flight FSR Paper (Revised)

**Manuscript:** "Future Service Rights in Aviation" (Revised)
**Reviewer:** Anonymous Referee
**Recommendation:** **Minor Revision** — All major issues from the first round have been satisfactorily addressed. Three minor items remain before acceptance.

---

## Summary Statement

The authors have made a thorough and conscientious revision. All five major issues (M1--M5) are adequately resolved: the booking curve sensitivity analysis demonstrates that the headline finding is robust to $\beta \in [0.10, 0.35]$; the carrier-type-specific stress tests replace the earlier proportional scaling with properly re-simulated scenarios; the pessimistic PD calibration provides a credible upper bound; the Monte Carlo diagnostics confirm convergence and correctly explain the zero Mezzanine EL as a structural property; and the DB1B sampling discussion acknowledges the 10\% limitation transparently.

The eight minor issues are also largely addressed: the abstract is appropriately tightened (approximately 220 words); the hotel comparisons are reduced to a single sentence in the introduction; the tranche proportions now sum to 100\% with a standard 5\% equity share; the reference list expanded from 9 to 16 entries with appropriate coverage of credit modeling, copula theory, and airline economics; the EL-to-rating mapping table is provided; the MC diagnostics include standard errors and convergence checks; and the CPA conditional-PD discussion has been added.

**The paper is now substantially stronger and approaching publishable quality.** Three items remain.

**Key Strengths (unchanged from Round 1):**
- The separation of yield management from default risk in carrier credit modeling is well-motivated and correctly executed
- The copula sensitivity analysis, demonstrating near-invariance of EL to tail dependence specification (3 bps range), is a genuine contribution
- The bankruptcy history calibration provides a transparent, falsifiable empirical foundation, now strengthened by the pessimistic full-period bound

**Remaining Weaknesses:**
- No actual figures (only tables) — this limits the paper's visual communication
- The "20\% user savings stable across $\beta$" finding in Table 5 shows users save ~20\% at all $\beta$, but the carrier position flips from +11\% premium to -14\% discount — this asymmetry deserves narrative attention
- Two factual errors in carrier data require correction

---

## Minor Comments (Round 2)

### m1. Missing Figures Throughout the Paper

**Status from Round 1 (m6):** Not fixed. The preamble includes `\graphicspath{{./paper_figures/}}` but the paper contains zero `\includegraphics` commands. All 11 tables are presented as LaTeX tables.

**Required:** Generate at minimum three figures:
1. **Copula sensitivity comparison** — a bar chart showing Senior EL (bps) and VaR 99\% for Gaussian, $t(6)$, and $t(4)$, making the near-invariance of EL visually immediate
2. **Carrier PD distribution** — a scatter or bar plot of calibrated PD by carrier type, showing the major/LCC/regional stratification
3. **Booking curve sensitivity** — a line plot of issue price and user savings vs. $\beta$, showing the stability of user savings and the carrier position crossover

These three figures directly support the paper's three claimed contributions. They can be generated from the existing JSON output files and inserted without additional model runs.

### m2. Narrative Gap in Booking Curve Results

Table 5 shows a striking pattern: user savings are constant at ~20\% across all $\beta$ values, but the carrier position shifts from earning an 11.2\% premium ($\beta=0.10$) to providing a 14.0\% discount ($\beta=0.35$). The paper notes this asymmetry in one sentence but does not explore its economic implication.

**Suggested addition (Section 4.3, after Table 5):** The stability of user savings across $\beta$ arises from the endogenous adjustment of the issue price: higher $\beta$ increases the face value (via $F = P_0 e^\beta$) but also increases the discounting denominator (since $r_{\text{adj}}$ depends on route CV, not on $\beta$). The net effect is that users consistently capture the forward premium minus the time discount and issue discount. The carrier position, by contrast, is directly exposed to $\beta$: at low $\beta$, the forward premium is modest and the airline receives above-spot revenue; at high $\beta$, the forward premium exceeds the time discount and the airline effectively subsidizes the user's price lock. The breakeven near $\beta \approx 0.22$ aligns with industry estimates of typical advance-purchase discounts, suggesting that the FSR structure would operate near parity pricing under realistic booking-curve assumptions.

### m3. Factual Corrections in Carrier Data

**3a. JetBlue (B6) fare CV.**

Table 1 reports B6's fare CV as 0.844. The paper states that NK (Spirit) has CV 0.654 and B6 0.844. B6, as a hybrid carrier (neither pure LCC nor full-service network carrier), typically has *lower* fare dispersion than ultra-low-cost carriers like Spirit and Frontier, because B6 offers a more standardized product (single-class cabin with extra legroom, no basic economy until recently). The 0.844 value appears to be higher than expected but is plausible given B6's Northeast-focused network with high business-leisure fare mixing on transcontinental routes (JFK--LAX, JFK--SFO). Verify this value or add a footnote explaining the network-driven CV elevation.

**3b. Allegiant (G4) route count.**

Table 1 reports G4 serving 1,384 routes with 5.4M passengers. This implies approximately 3,900 passengers per route per quarter, or about 43 passengers per day per route. G4's business model uses low-frequency service (2--4 flights per week) on thin routes. The passenger-to-route ratio is consistent with this model, but the route count may include seasonal-only routes from the 2024 Q2 data. Clarify whether routes are defined as OD pairs served in that specific quarter or across all 13 quarters.

---

## Verification of Round 1 Issues

| Round 1 # | Issue | Status | Notes |
|-----------|-------|--------|-------|
| **M1** | $\beta$ uncalibrated | ✅ **Resolved** | Section 4.3 + Table 5: $\beta \in [0.10, 0.35]$ sensitivity. User savings stable at ~20\%. |
| **M2** | Stress test proportional | ✅ **Resolved** | Section 6.3 + Table 8: three carrier-type-specific re-simulations. |
| **M3** | Survivorship bias | ✅ **Resolved** | Section 3.2 + Table 2: pessimistic 2000-2025 window (PD 0.76\%→1.15\%). |
| **M4** | Zero Mezzanine EL | ✅ **Resolved** | Section 6.1 + Table 7: MC diagnostics, max pool loss 15.6\%, structural explanation. |
| **M5** | DB1B sampling | ✅ **Resolved** | Section 2.1: 10\% sample discussion, passenger-volume weighting. |
| **m1** | Hotel comparisons | ✅ **Resolved** | Reduced to single sentence in Introduction. |
| **m2** | Equity 1\% | ✅ **Resolved** | Tranche proportions: 65/20/10/5. |
| **m3** | Sparse references | ✅ **Resolved** | Expanded from 9 to 16 references. |
| **m4** | MC diagnostics | ✅ **Resolved** | Table 7: SE 1.2 bps, convergence, per-carrier default frequency. |
| **m5** | Abstract length | ✅ **Resolved** | ~220 words. |
| **m6** | Missing figures | ❌ **Not fixed** | Zero `\includegraphics` commands. See Round 2 m1. |
| **m7** | Rating mapping | ✅ **Resolved** | Table 3: EL→Rating with VaR99 guidelines. |
| **m8** | CPA conditional PD | ✅ **Resolved** | Section 3.4: two-layer credit discussion. |

**12 of 13 Round 1 issues resolved. 1 (m6, now Round 2 m1) remains open.**

---

## Final Checklist

- [x] Summary statement clearly conveys overall assessment
- [x] All Round 1 issues verified against revised manuscript
- [x] Three new minor issues identified with specific locations and fixes
- [x] Statistical methods now include sensitivity analysis, convergence diagnostics, and pessimistic bounds
- [x] Reproducibility: methods section describes DB1B source, parameter values, and simulation design
- [x] Ethical: public data, no human subjects concerns
- [x] Recommendation consistent with identified issues (three minor items → Minor Revision)

---

## Overall Assessment

The revision demonstrates substantial improvement. The three remaining items (three figures, booking curve narrative, two factual clarifications) can be addressed within one working day and do not require re-running the main model. I recommend **Minor Revision** with the expectation that the next round will be the final one. The paper's core contribution---that flight capacity can be securitized at investment-grade credit quality using carrier-level credit models and booking-curve pricing---is now well-supported by the empirical evidence and robustness checks.
