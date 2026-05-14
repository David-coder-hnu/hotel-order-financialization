# Third-Round (Final) Referee Report: Flight FSR Paper

**Manuscript:** "Future Service Rights in Aviation: Carrier-Level Credit, Booking-Curve Pricing, and *t*-Copula Structuring"
**Reviewer:** Anonymous Referee
**Round:** 3 (Final)
**Recommendation:** **ACCEPT** — No further revisions required.

---

## Summary Statement

This manuscript has undergone a rigorous three-round peer review process. Round 1 identified 13 issues (5 major, 8 minor) requiring substantial revision. Round 2 verified the resolution of 12 of 13 issues and identified 3 remaining minor items. This third round confirms that all issues from all prior rounds have been satisfactorily addressed.

The paper now presents a complete, internally consistent, and empirically grounded argument that commercial aviation capacity can be securitized at investment-grade credit quality using carrier-level credit models, booking-curve pricing, and *t*-copula dependence structures. The three figures (copula sensitivity, carrier PD distribution, booking curve sensitivity) effectively communicate the paper's core contributions. The narrative is well-structured: data → credit model → pricing → structuring → results → stress tests → limitations. The reference list (16 entries) provides adequate coverage of the relevant literatures in credit modeling, copula theory, airline economics, and structured finance.

**Key Strengths:**
- The central finding (Senior A-rated, EL 24 bps) is supported by Monte Carlo diagnostics (EL SE 1.2 bps, convergence verified), copula sensitivity analysis (3 bps EL range), booking curve sensitivity ($\beta \in [0.10, 0.35]$), pessimistic PD calibration (2000--2025 window), and carrier-type-specific stress tests
- The separation of yield management from default risk in the carrier credit model is well-motivated and correctly executed, with historical bankruptcy data providing a transparent calibration basis
- The paper is honest about its principal limitation (uncalibrated booking curve) and addresses it through formal sensitivity analysis rather than obscuring it

**Remaining Issues:** None that affect acceptance.

---

## Verification of All Prior Issues

### Round 1 Issues

| # | Issue | Status |
|---|-------|--------|
| M1 | $\beta$ uncalibrated | ✅ Section 4.3 + Table 5 + Figure 3 |
| M2 | Stress test proportional | ✅ Section 6.3 + Table 11 (carrier-type re-simulations) |
| M3 | Survivorship bias | ✅ Section 3.2 + Table 2 (pessimistic PD 1.15%) |
| M4 | Zero Mezzanine EL | ✅ Section 6.1 + Table 7 (MC diagnostics, structural explanation) |
| M5 | DB1B sampling | ✅ Section 2.1 (10% sample discussion, volume weighting) |
| m1 | Hotel comparisons | ✅ Single sentence in Introduction |
| m2 | Equity 1% | ✅ 65/20/10/5 structure |
| m3 | Sparse references | ✅ 16 entries |
| m4 | MC diagnostics | ✅ Table 7 |
| m5 | Abstract length | ✅ ~220 words |
| m6 | Missing figures | ✅ 3 figures (Figs. 1--3) |
| m7 | Rating mapping | ✅ Table 3 |
| m8 | CPA conditional PD | ✅ Section 3.4 |

### Round 2 Issues

| # | Issue | Status |
|---|-------|--------|
| m1 | Missing figures | ✅ Figures 1--3 embedded with captions and cross-references |
| m2 | Booking curve narrative | ✅ New paragraph in Section 4.3 explaining endogenous stability mechanism |
| m3a | B6 CV footnote | ✅ Footnote [1] in Table 1 |
| m3b | G4 route count footnote | ✅ Footnote [2] in Table 1 |

**16 of 16 issues resolved across all rounds.**

---

## Final Quality Assessment

### Figures (Stage 5)

Three figures are present and publication-quality:

- **Figure 1** (Copula Sensitivity): Dual-panel bar chart correctly communicates the paper's key finding — EL invariance vs. VaR99 tail concentration. Color scheme (blue/green/orange) is colorblind-accessible. A-rating thresholds marked with dashed reference lines.
- **Figure 2** (Carrier PD): Horizontal bar chart with type-based color coding. Pool PD reference line clearly marked. All 25 carriers labeled with exact PD values. Readable at journal column width.
- **Figure 3** (Booking Curve Sensitivity): Dual-axis plot with carrier position bars (green/red for premium/discount) and user saving line (blue). Baseline $\beta=0.22$ marked. Forward premium annotations provide context.

All figures have standalone captions and are referenced in the text. Figure placement follows the narrative flow.

### Tables

Eleven tables present all quantitative results in reproducible form. Key tables (MC results, diagnostics, stress tests, sensitivity analyses) include sufficient detail for independent verification. The EL-to-Rating mapping (Table 3) makes the rating assignments transparent and reproducible.

### Methods Reproducibility (Stage 4)

The Methods sections provide: data source (DB1B, with URL), parameter values (all key parameters stated with numerical values), model equations (PD calibration, booking curve pricing, *t*-copula definition), and simulation design (5,000 paths, 12-month horizon, $\nu=4$). The DB1B data is publicly available from the U.S. DOT Bureau of Transportation Statistics. Code availability is mentioned in the acknowledgments.

**Recommendation for camera-ready:** Add a DOI or repository link for the analysis code in the acknowledgments section.

### Writing Quality (Stage 7)

The writing is clear, precise, and well-organized. Technical terms are defined on first use. The abstract accurately reflects the paper's content. The conclusion does not overstate the findings — limitations (booking curve calibration, DB1B sampling, regional carrier CPA structure, regulatory uncertainty) are acknowledged in Section 7.

### Ethical Considerations (Stage 6)

No concerns. Publicly available data. No human subjects. No conflicts of interest to disclose. The funding source is not stated — this is standard for working papers but should be added before journal submission if applicable.

---

## Cosmetic Notes (Optional, Not Blocking Acceptance)

1. **C1 (Section 2.1):** The sentence "The median route in our pool has 145 fare observations" could be moved to the pool construction section (5.1) where the pool is actually defined.
2. **C2 (Figure 2):** The pool PD reference line crosses several carrier labels on the right side. Consider moving the annotation to the left margin in the camera-ready version.
3. **C3 (References):** Bharath & Shumway (2008), Merton (1974), and Crosbie & Bohn (2003) are cited in the bibliography but could be more explicitly connected to the carrier credit model in the main text. A brief sentence in Section 3.1 noting that "our structural approach draws on the Merton (1974) framework as operationalized by Bharath & Shumway (2008) and Crosbie & Bohn (2003), with the critical modification that we replace asset volatility with a composite of carrier-type base PD and operational CV adjustment" would strengthen the methodological lineage.
4. **C4 (Acknowledgments):** Consider adding the U.S. DOT citation more formally and a statement about code availability.

---

## Final Checklist

- [x] Summary statement clearly conveys overall assessment
- [x] All prior-round issues verified as resolved (16/16)
- [x] No major concerns remain
- [x] No minor concerns remain (4 cosmetic suggestions only)
- [x] Statistical methods: sensitivity analysis, convergence diagnostics, pessimistic bounds all present
- [x] Reproducibility: data source documented, parameters stated, equations provided
- [x] Figures evaluated: 3 figures, publication quality, standalone captions
- [x] Writing quality assessed: clear, well-structured, limitations acknowledged
- [x] Tone is constructive and professional
- [x] Recommendation (Accept) is consistent with the paper's current state

---

## Decision: ACCEPT

The manuscript is scientifically sound, methodologically rigorous, and clearly written. The three-round revision process has substantially strengthened the paper: the booking curve sensitivity analysis, carrier-type-specific stress tests, pessimistic PD calibration, Monte Carlo diagnostics, and figures collectively transform what was a promising but incomplete draft into a publication-ready manuscript.

I recommend acceptance without further revision. The four cosmetic notes above are entirely optional and can be addressed at the authors' discretion during the camera-ready preparation. I congratulate the authors on a rigorous piece of work and look forward to seeing it in print.
