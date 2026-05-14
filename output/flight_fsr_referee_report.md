# Referee Report: Flight FSR Paper

**Manuscript:** "Future Service Rights in Aviation: Carrier-Level Credit, Booking-Curve Pricing, and *t*-Copula Structuring of Flight Capacity"
**Reviewer:** Anonymous Referee
**Recommendation:** **Major Revision** — The paper contains substantial original contributions but has methodological issues requiring correction before acceptance.

---

## Summary Statement

This paper extends the Future Service Rights framework from hotels to commercial aviation, addressing the fundamentally different risk topology of the airline industry (25 carriers vs. 16,257 independent properties) through three innovations: carrier-level credit calibration from historical bankruptcy data, booking-curve pricing, and *t*-copula dependence modeling. The headline finding—that a flight FSR Senior tranche achieves an A rating (EL 26 bps) under *t*(4)-copula simulation of 5,000 paths—is well-supported and economically significant. The use of 97.3M DB1B fare observations provides credible empirical grounding.

**Key Strengths:**
- The carrier credit model correctly identifies that fare CV is a poor default proxy for airlines (it reflects yield management, not financial distress), and the separation of base PD / size adjustment / CV modifier is well-motivated
- The copula sensitivity analysis is a genuine contribution—demonstrating that EL is nearly invariant to copula choice (only 2 bps difference) isolates the primacy of base PD over correlation structure
- The bankruptcy history calibration (2013-2025) provides a transparent, falsifiable empirical foundation

**Key Weaknesses:**
- The booking curve parameter β = 0.22 is **entirely uncalibrated** from the data, which undermines the pricing model's empirical credibility
- The stress test methodology is overly simplistic (proportional scaling rather than re-simulation) and may understate tail risk
- Several structural limitations (survivorship bias in PD calibration, DB1B sampling effects on route statistics, regional carrier CPA two-layer credit structure) are mentioned but not quantitatively addressed

---

## Major Comments

### M1. Booking Curve β Cannot Be Calibrated from DB1B (Section 4)

**Issue:** The paper acknowledges (Section 2.1, line 56-58) that "DB1B records tickets by travel quarter, not purchase date, preventing direct calibration of the booking curve." Yet the entire pricing model (equations 4-5) depends on β = 0.22, which is described as "consistent with industry estimates of average advance-purchase discounts of 20-30%." A parameter that drives the face value (25% forward premium), issue price, and user savings (19%) cannot rest on a literature citation alone.

**Why this matters:** If β = 0.10 (only 10.5% booking-curve premium), the user savings drop from 19% to approximately 8%, and the airline discount becomes more significant. If β = 0.35 (42% premium), the forward pricing becomes too attractive for airlines to accept. The paper's stakeholder economics are sensitive to this parameter.

**Required fix:** 
1. Conduct a formal sensitivity analysis of all stakeholder economics (airline revenue, user savings, platform spread) to β ∈ [0.10, 0.35]
2. Provide a table showing the range of outcomes
3. Defend the β = 0.22 choice with multiple literature citations (Belobaba 2015, Gaggero & Piga 2012 are cited but not linked to specific β estimates)
4. Consider whether the booking curve could be calibrated from a different data source (e.g., published airline revenue management studies, GDS data samples)

### M2. Stress Test Methodology Is Incomplete (Section 6.3)

**Issue:** The stress test (Table 5) applies PD and LGD multipliers to the *pool-level loss distribution* rather than re-simulating with stressed carrier-level parameters. This approach:

1. **Understates tail risk:** Multiplying pool EL by a factor assumes losses scale linearly, but a 4× PD scenario for carriers would change the *distribution shape*, not just the mean. Carriers with currently low PDs (WN 0.30%) that become 4× (1.20%) remain below the PDs of already-distressed carriers, but the correlation structure of *which* carriers default changes materially.
2. **Cannot capture concentration effects:** In a real stress scenario, similar carrier types would experience correlated PD increases (e.g., all LCCs simultaneously deteriorate). The current method applies a uniform multiplier.
3. **The "Extreme Stress" scenario (6× PD, 2× LGD) pushes WN's PD from 0.30% to 1.80%—still below B6's baseline 1.20%.** This suggests the stress scenarios are not as extreme as the labels imply. A genuine airline stress scenario (pandemic, fuel crisis) would disproportionately affect weaker carriers, producing a non-uniform PD shift.

**Required fix:**
1. Implement at least one re-simulation with stressed carrier-level PDs (not just pool-level scaling)
2. Define stress scenarios in terms of carrier-specific shocks (e.g., "all LCC PDs × 3, majors × 1.5")
3. Report the resulting Senior EL from the re-simulation alongside the proportional estimates
4. Clarify that the proportional method underestimates tail risk when carrier PDs have heterogeneous responses to stress

### M3. Survivorship Bias in PD Calibration (Section 3.2)

**Issue:** The base PD calibration uses the period 2013-2025, defined as "post-consolidation." The choice of 2013 as the cutoff is consequential:
- American Airlines emerged from Ch.11 in December 2013 → excluding this year removes the last major-carrier bankruptcy from the calibration window
- US Airways (2002, 2004), United (2002), Delta (2005), Northwest (2005), American (2011) all filed in the preceding period
- Selecting 2013 as the breakpoint conditions on the data: it maximizes the "clean" period

A reader could reasonably argue that using a 12-year clean window to calibrate PDs for an industry known to be cyclical is vulnerable to survivorship bias. The 2000-2012 period had 6 major-carrier bankruptcies over 13 years.

**Required fix:**
1. Report what the pool-weighted PD would be using the full 2000-2025 period (including pre-consolidation bankruptcies). This provides a "pessimistic" calibration bound.
2. Discuss why the post-consolidation period is structurally different (industry consolidation → reduced competition → higher profitability → lower default risk) with supporting evidence (e.g., airline profitability data, Borenstein 2011)
3. Consider a Bayesian approach: use the post-consolidation data as the likelihood but incorporate a skeptical prior based on the full historical record

### M4. The "Zero Mezzanine and Junior EL" Problem (Table 4)

**Issue:** Table 4 reports Mezzanine EL = 0.00% and Junior EL = 0.00%, with implied ratings of Aaa. This result is implausible and likely reflects a modeling artifact rather than genuine risk assessment.

The pool VaR 99% is 4.37%, meaning in 1% of paths, more than 4.37% of the pool is lost. With 35% credit enhancement protecting the Senior tranche, the Senior should absorb losses up to 4.37% of the pool (which is about 6.7% of the Senior tranche since Senior = 65% of pool). The Mezzanine (attachment 65%, detachment 87%) would be hit if pool losses exceed 65% of the pool value—but 65% of the pool is equivalent to 100% of Senior. Translated: if pool losses exceed 65%, Mezzanine takes losses.

However, with an average of only 0.6 carrier defaults per path and each defaulted carrier affecting at most 8 routes (8/69 ≈ 11.6% of the pool), a single carrier default produces a maximum pool loss of 11.6% × LGD ≈ 11.6% × 17.7% ≈ 2.1%. This is well within the 35% Senior CE. Multiple carriers would need to default simultaneously to breach Mezzanine—which the *t*-copula should make possible in tail scenarios.

**The Mezzanine EL should be non-zero if the simulation is correctly implemented.** A 0.00% EL for Mezzanine implies that not a single path out of 5,000 produced pool losses exceeding 65%. To verify: with 25 carriers, base correlation 0.35, and *t*(4) copula, the probability of ≥5 carriers defaulting simultaneously should be non-negligible (each affecting ~8 routes, 5 × 8 / 69 ≈ 58% of pool, which could breach past Senior).

**Required fix:**
1. Verify the waterfall implementation—are losses correctly allocated from the pool through each tranche?
2. Report the maximum pool loss across all 5,000 paths
3. If Mezzanine EL is genuinely zero, explain why the *t*-copula with ν=4 does not produce enough joint defaults to breach the 65% attachment point
4. If it's an artifact, fix the simulation and re-report

### M5. DB1B Sampling Effects on Route Statistics (Section 2)

**Issue:** DB1B is a 10% sample of tickets. The paper computes route-level statistics (mean fare, CV, passenger volume) from this sample without addressing whether the 10% sampling rate introduces bias in variance estimates.

For high-volume routes (thousands of passengers per quarter), the 10% sample should provide reliable estimates. But for low-volume routes near the 20-observation threshold, the sampling error on CV estimates could be substantial. Since 25,137 routes survive the "≥20 obs" filter, many of these are thin routes where sampling variance inflates the observed CV.

**Required fix:**
1. Add a brief discussion of how DB1B's 10% sampling affects route-level CV estimates
2. Consider weighting routes by observation count (inverse-variance weights) in the pool statistics
3. Report the median observation count for routes in the pool (not just the minimum of 20)

---

## Minor Comments

### m1. Excessive Hotel FSR Comparisons

The paper compares flight FSR to hotel FSR in at least 8 distinct locations (abstract, introduction, data section, credit model, pricing, results, discussion, conclusion), despite presenting itself as a standalone contribution. Remove or reduce most comparisons—especially since the current hotel results are from a different model specification (ternary settlement engine vs. simplified default model). Either make this a formal comparison paper or remove the hotel references to 1-2 sentences in introduction/discussion.

### m2. The Equity Tranche Percentage

Table 3 (Tranche Structure) shows Equity at "1.0%" — Senior (65%) + Mezzanine (22%) + Junior (12%) + Equity (1%) = 100%. However, this is stated as $100\% - 99\%$ attachment, which gives 1%. The low equity share is unconventional—ABS structures typically retain 3-5% equity for incentive alignment. Clarify why 1% is sufficient.

### m3. Sparse Reference List

Only 9 references for a 14-page paper. Missing citations include:
- Credit risk modeling: Merton (1974), Crosbie & Bohn (KMV, 2003)
- Airline yield management: Talluri & van Ryzin (2004), McGill & van Ryzin (1999)
- Copula theory: Embrechts, Lindskog, & McNeil (2003), Joe (1997)
- Airline bankruptcy analysis: Gritta, Chow, & Freed (multiple papers on airline financial distress prediction)
- Securitization: Gorton & Metrick (2012), Coval, Jurek, & Stafford (2009)

### m4. Missing Monte Carlo Diagnostics

The paper reports EL, VaR 95%, and VaR 99% but omits standard MC diagnostics:
- Standard error of the EL estimate (given 5,000 paths, this would be roughly σ/√5000)
- Convergence diagnostics (did the EL stabilize after 5,000 paths?)
- The expected number of defaults *per carrier* (not just the pool average), to assess whether small carriers with high PDs drive the results

### m5. Abstract Length

The abstract is approximately 350 words—conventionally, abstracts are 150-250 words. The detailed methodology (book pricing, copula, route pool construction) should be condensed. The abstract should focus on: (1) what was done, (2) main finding, (3) significance.

### m6. Missing Figure References

The paper includes `\graphicspath{{./paper_figures/}}` in the preamble but contains no `\includegraphics` commands. Either create the referenced figures (price convergence path, MC loss distribution, copula sensitivity comparison) or remove the graphics path.

### m7. Specificity of "Investment Grade" Thresholds

Tables 4-5 use "A" and "Aaa" as Moody's-equivalent ratings but do not provide the explicit EL→Rating mapping. This makes the rating assignments non-reproducible. Include a table of the mapping thresholds used.

### m8. Regional Carrier CPA Treatment

The paper notes that regional carriers "operate under CPA where the major airline partner bears the revenue risk" (Section 7) but then assigns them independent PDs (OO 0.80%, YX 1.50%). If a regional's default is contingent on its partner's default, this is a *conditional* PD, not an independent one. Clarify the modeling assumption or use conditional PDs.

---

## Questions for Authors

1. What is the maximum pool loss across all 5,000 MC paths? This number would contextualize the Mezzanine/Junior zero-EL result.

2. How sensitive is the Senior rating to the carrier concentration limit (currently 8 routes per carrier)? If raised to 12 or lowered to 5, what happens to Senior EL?

3. Have you considered using actual airline credit ratings (S&P/Moody's) as a validation of your calibrated PDs? For example, WN is rated BBB+/Baa1, which typically corresponds to a 1-year PD of approximately 0.10-0.15%. Your calibrated WN PD of 0.30% is 2-3× higher—can you reconcile this?

4. The 12-month maturity is motivated by "capturing a full seasonal cycle." But airlines publish schedules 330 days in advance and adjust them continuously. Would a 6-month or 18-month maturity produce materially different Senior ratings?

5. What happens to the pool if Spirit Airlines (NK, PD 3.00%, 5.4% market share) is excluded? Given that NK filed Ch.11 in 2024, its inclusion as a "baseline" carrier rather than a "stressed" carrier could inflate the pool PD.

---

## Final Checklist

- [x] Summary statement clearly conveys overall assessment
- [x] Major concerns clearly identified (M1-M5) and justified
- [x] Suggested revisions are specific and actionable
- [x] Minor issues noted and properly categorized (m1-m8)
- [x] Statistical methods evaluated (MC diagnostics, sampling effects, calibration bias)
- [x] Reproducibility and data availability assessed
- [x] Figures and tables evaluated (missing figures, formatting)
- [x] Writing quality assessed (abstract length, excessive comparisons)
- [x] Tone is constructive and professional
- [x] Recommendation (Major Revision) is consistent with identified issues

---

## Overall Assessment

The paper makes a genuine contribution to the FSR research program and the core finding—that airline credit quality supports an A-rated securitization—is robust to most parameter variations. The carrier credit model's separation of yield management from default risk is both novel and correct. However, **the booking curve parameter must be empirically validated or subjected to rigorous sensitivity analysis (M1), the stress test methodology must include at least one re-simulation (M2), and the survivorship bias in PD calibration must be addressed (M3)** before the paper is suitable for submission. The zero-EL Mezzanine/Junior result (M4) may indicate a simulation bug and requires immediate investigation.

**Decision: Major Revision.** I expect the authors can address these comments within 2-3 weeks, after which I would recommend acceptance.
