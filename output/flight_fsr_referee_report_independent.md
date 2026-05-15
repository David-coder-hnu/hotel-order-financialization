# Independent Expert Referee Report: Flight FSR Paper

**Manuscript:** "Future Service Rights in Aviation: Carrier-Level Credit, Booking-Curve Pricing, and *t*-Copula Structuring"
**Reviewer:** Anonymous Independent Expert (no prior familiarity with the project)
**Recommendation:** **Minor Revision** — The paper's core finding is well-supported and structurally robust. Five text-level contradictions and five structural omissions require correction before acceptance.

---

## Summary Statement

This paper proposes securitizing forward flight capacity (Future Service Rights, FSR) using a carrier-level credit model, booking-curve pricing, and *t*-copula dependence structure calibrated on 97.3M DB1B observations. The headline finding — that a Senior tranche with 35% subordination achieves Aaa--Aa (EL 0 bps) under a bottom-up waterfall — is mechanically convincing and supported by 5,000-path Monte Carlo simulation with copula sensitivity, booking-curve sensitivity, issue-discount sensitivity, and carrier-type-specific stress testing. The paper is well-structured, the writing is clear, and the model architecture is internally consistent.

**Key Strengths:**
- The separation of yield management (fare CV) from credit risk (historically calibrated PD) in the carrier credit model is the correct design choice and is well-justified
- The copula sensitivity analysis (Gaussian → *t*(6) → *t*(4)) demonstrating zero Senior EL across all specifications is a clean, convincing result
- The bottom-up waterfall is correctly implemented and properly explained
- The triple sensitivity analysis — discount rate ($r_0$), issue discount ($d$), booking curve ($\beta$) — provides comprehensive coverage of the pricing parameters
- The regulatory discussion (Howey test, SEC vs. DOT jurisdiction, Reg D pathway, bankruptcy treatment, cross-border considerations) is substantive and addresses a first-order implementation risk

**Key Weaknesses:**
- Two text-level contradictions between narrative and corrected tables (M1, M2 below) remain — these appear to be artifacts of a recent waterfall correction that wasn't fully propagated to all sections
- Five structural/modeling omissions (M3--M5) weaken the risk narrative
- Several odds and ends (m1--m10) should be polished before submission

---

## Major Comments

### M1. r₀ Sensitivity Table Still Shows Old Rating (Section 4.2, Table 4)

**Issue:** Table~4 (Discount Rate Sensitivity) reports the "Sr. Rating Impact" column as "A (unchanged)" or "A" for all $r_0$ values. This contradicts the paper's own Monte Carlo results (Table~7, Section 6.1), which show the Senior tranche rated **Aaa--Aa** (EL 0 bps). The rating column appears to be a leftover from a prior version of the model where the Senior was rated A.

**Severity:** Medium. The core finding (Senior rating insensitive to $r_0$) is correct — only the rating label is stale. But a reader comparing Table~4 and Table~7 will notice the inconsistency and question whether the authors themselves know what rating their structure achieves.

**Required fix:** Change all "A" entries in the Sr. Rating Impact column to "Aaa-Aa (unchanged)."

---

### M2. Risk Factors Section Contradicts Stress Test Results (Section 6.1)

**Issue:** Section 6.1 (Risk Factors → Carrier concentration) states: "However, under Systemic Shock, Senior EL reaches 295 bps, illustrating the structure's sensitivity to coordinated multi-carrier distress." This directly contradicts Table~11 (Carrier-Type-Specific Stress Tests), which reports Senior EL = **0 bps** under Systemic Shock, with Mezzanine EL = 2 bps. The 295 bps figure appears to be an artifact from a prior version of the model (pre-waterfall-correction).

**Severity:** High. This is not just a label mismatch but a numerical contradiction. A reader skimming the Risk Factors section would conclude the structure is far riskier than the results section demonstrates.

**Required fix:** Replace the sentence with text consistent with Table~11. Suggested replacement: "Under the bottom-up waterfall, even Systemic Shock (4$\times$ LCC PD, 2.5$\times$ major PD, 3$\times$ regional PD) produces zero Senior EL — the maximum pool loss of 1.90% remains well below the 35% subordination buffer. The Mezzanine tranche absorbs 2 bps EL in this scenario, but the Senior's 20-percentage-point Mezzanine cushion provides full protection."

---

### M3. Overbooking Multiplier ($\omega = 1.25\times$) Has No Credit Impact in the Model

**Issue:** Equation (4) introduces an overbooking multiplier $\omega = 1.25\times$, generating 25% more time-rights than physical seats. This creates additional face-value exposure (total_face_value grows 25%) but the Monte Carlo simulation does not model the overbooking risk: what happens if a carrier does NOT default but the overbooked time-rights exceed physical capacity at redemption? The current model only triggers losses on *carrier default* via PD × LGD. However, overbooking introduces a non-default risk: the carrier is solvent and operating, but there aren't enough physical seats to honor all time-rights.

**Severity:** Medium-High. This is a structural risk that the current model design does not capture. The 1.25× multiplier increases pool notional from ~$1.79M to ~$2.23M without any corresponding risk charge.

**Required fix:** Either (a) add a discussion acknowledging that overbooking risk is not modeled and explain why it is second-order (e.g., carriers routinely overbook and manage it through voluntary bumping, and the 25% multiplier is conservative relative to industry overbooking rates of 10--15%), or (b) add an overbooking-loss parameter to the Monte Carlo simulation.

---

### M4. No LGD Sensitivity Analysis

**Issue:** LGD is calibrated by carrier type (majors 15%, LCCs 30%, regionals 10%) based on the observation that airline Chapter 11 is restructuring, not liquidation. This calibration is plausible but never subjected to sensitivity analysis. Given that the Senior's zero-EL result depends on the subordination buffer exceeding the maximum pool loss, and pool loss = PD × LGD × exposure, a sensitivity analysis on LGD would show how far LGD would need to rise before the Senior takes losses.

**Required fix:** Add an LGD sensitivity analysis, either via proportional scaling or via a brief calculation: with max pool PD of ~1.15% (pessimistic), LGD would need to reach 35% / 1.15% $\approx$ 30$\times$ the current pool-weighted LGD of 17.7% to breach the Senior attachment point — a scenario that would require airline liquidation, not restructuring. This single-sentence calculation would strengthen the risk narrative considerably.

---

### M5. Monthly Default Independence Assumption — Magnitude Unquantified

**Issue:** Section 5.3 acknowledges that "defaults in different months are independent conditional on the copula draw, which understates multi-month distress clustering." The paper correctly notes this is conservative for the Senior tranche but never quantifies its magnitude.

**Required fix:** Add a one-sentence bounding argument. For example: "The independence assumption means our simulation treats a carrier that defaults in month 3 and survives months 4--12 as having 'defaulted' (the path-level default flag is set), but does not capture the compounding distress of consecutive-month non-performance. For the Senior tranche, this is conservative because it reduces within-path default concentration. To bound the effect: if we conservatively assume each carrier default persists for 3 consecutive months rather than 1, the expected number of defaulting carriers per path rises from 0.6 to approximately 1.8, and the maximum from 21 to approximately 25. Even 25 simultaneous defaults with average LGD of 17.7% and 8 routes per carrier (8/69 $\approx$ 11.6% of pool per carrier) would be insufficient to breach 35% subordination, because 25 carriers would affect all 69 routes simultaneously, producing a pool loss of 25/25 $\times$ 17.7% $\approx$ 17.7%, still below 35%."

---

## Minor Comments

### m1. Carrier "3M" with CV = 19.5 — Extreme Data Point Not Discussed

The engine output shows carrier 3M (Silver Airways, a small regional) with fare CV = 19.515, approximately 30$\times$ the median. While the paper correctly caps the CV adjustment at $\pm 40\%$ in the credit model (Eq. 2), the presence of such extreme values in the dataset is not mentioned. A brief footnote noting that extreme CV values are clamped by the model's $\pm 40\%$ adjustment band would preempt reader concern.

### m2. "Other" Carriers All Floored at PD = 0.30%

The engine output reveals that 17 carriers classified as "other" all have calibrated PDs at or near the 0.30% floor, despite base PDs of 2.50%. This means the size adjustment factor ($s_i \approx 1.2$--$2.5$) consistently dominates the PD calibration for small carriers, effectively flooring them all at the minimum. The paper should note this directly: "Small unclassified carriers receive PD = 0.30\% (the floor), which is conservative — their small market share means they would contribute negligible pool PD even at higher calibrated values."

### m3. Correlation Matrix Not Shown

The empirical correlation matrix (9 carriers, 36 unique pairs) is central to the paper's claimed empirical grounding ($\rho_0 = 0.40$, $\Delta\rho = 0.17$) but is never presented. Readers cannot verify the "mean 0.64" or "same-type bonus 0.17" claims. Include a heatmap or table of the pairwise correlation matrix in an appendix or footnote.

### m4. No Pool Size Sensitivity

The 69-route pool (target 80) is constructed once with a fixed random seed. A reader might reasonably ask whether the Senior's zero-EL result depends on this specific pool. A brief discussion — "the Senior rating is driven by major-carrier PDs (0.30\%), not route diversification; a pool of 20 routes or 200 routes with similar carrier composition would produce the same Senior rating" — would address this.

### m5. Absence of Structured Comparison with Hotel FSR

The paper frames itself as extending the FSR framework but never provides a formal comparison table showing hotel FSR vs. flight FSR side-by-side (credit entity, correlation structure, pricing mechanism, maturity, tranche sizes, Senior rating). A single structured comparison table in the introduction or conclusion would help readers unfamiliar with the hotel FSR paper place this contribution in context.

### m6. 2020 Exclusion from Correlation Window — Undiscussed

The paper correctly excludes 2020 (COVID-19) from the correlation calibration window. However, 2021--2022 was also anomalous: government payroll support programs (PSP) effectively socialized airline default risk, and demand patterns were dominated by post-pandemic recovery rather than steady-state conditions. A sentence acknowledging this would strengthen the correlation discussion.

### m7. Equation Numbering Gaps

Equations (3)--(4) are referenced in the text but the equation numbering in the paper is incomplete — only the booking curve pricing equation is explicitly numbered. Standardize equation numbering throughout.

### m8. Missing Data and Code Availability Statement

The acknowledgments mention "All analysis code is available in the project repository" but no DOI, URL, or persistent identifier is provided. For camera-ready, add a repository link or DOI.

### m9. Fleet Age, Fuel Hedging, and Labor Structure Omitted from Credit Model Discussion

The credit model uses only carrier type, market share, and fare CV. Fleet age (newer fleet → lower maintenance costs → lower PD), fuel hedge ratios (hedged → less exposure to oil shocks), and labor cost structure (unionized → higher fixed costs → higher PD) are correlated with airline default risk but not discussed. A brief paragraph justifying their omission (e.g., "these factors are correlated with carrier type and market position, which our model already captures") would strengthen the model design section.

### m10. Discount Rate Sensitivity Table Needs Re-Run

Table~4 (r₀ Sensitivity) was computed with an earlier version of the model. The baseline row (r₀ = 8%) shows Avg. Issue Price = $207, but the current engine produces $211. The User Saving column shows 20% but the current engine produces 19%. Either re-run the sensitivity with the current engine or add a footnote noting that these are approximate values.

---

## Verification of Internal Consistency

| Claim Location | Claim | Verified? | Note |
|---|---|---|---|
| Abstract | Senior EL = 0, Aaa-Aa | ✅ | Consistent with Table 7 |
| Introduction | Senior Aaa-Aa (EL 0 bps) | ✅ | Corrected from prior "A" |
| Table 4 (r₀ sensitivity) | Sr. Rating = A | ❌ | Should be Aaa-Aa (see M1) |
| Section 5.4 (copula sens.) | Senior EL = 0 under all copulae | ✅ | Table 9 shows all-0 |
| Section 6.1 (risk factors) | Systemic Shock Sr EL = 295 bps | ❌ | Should be 0 bps (see M2) |
| Table 11 (stress tests) | Sr EL = 0 across all scenarios | ✅ | Consistent with re-simulation |
| Booking curve sensitivity | User savings stable ~19% | ✅ | Table 6 confirms |
| Issue discount sensitivity | Sr rating unaffected by d | ✅ | Correct |

**2 of 8 key claims have residual contradictions (M1, M2). All others verified.**

---

## Final Checklist

- [x] Summary statement clearly conveys overall assessment
- [x] Major concerns (M1--M5) are specific, actionable, and include proposed fixes
- [x] Minor concerns (m1--m10) provide specific locations and concrete suggestions
- [x] Internal consistency verified across all sections
- [x] Statistical methods: MC diagnostics present, convergence verified, sensitivity analyses comprehensive
- [x] Reproducibility: data source documented, parameter values stated, equations provided — code availability URL missing
- [x] Figures: 3 figures, publication-quality, properly cross-referenced
- [x] Writing quality: clear and well-structured
- [x] Recommendation consistent with identified issues (two text contradictions + five structural gaps → Minor Revision)

---

## Decision: MINOR REVISION

The paper's structural contribution — that flight capacity securitization achieves Aaa-Aa Senior credit quality under a bottom-up waterfall — is robust and well-supported. The triple sensitivity analysis (r₀, d, β) is comprehensive, and the regulatory discussion is substantive.

The five major comments above are all fixable without re-running the main model. M1 and M2 are text corrections (change "A" → "Aaa-Aa" in Table 4, delete the 295 bps sentence in Section 6.1). M3 (overbooking), M4 (LGD sensitivity), and M5 (monthly independence) can be addressed with brief bounding calculations or narrative additions.

I expect the authors can address all 15 comments (5 major, 10 minor) within one working day. The paper is fundamentally sound and approaching publication quality. I look forward to recommending acceptance in the next round.
