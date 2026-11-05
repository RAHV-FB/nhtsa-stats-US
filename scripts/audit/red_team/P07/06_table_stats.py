"""P07: committed-table statistics (no data load). How often is an allocation available, how often
are shares negative/outside [0,1], how wide is the first-vs-last range, for supported cases;
and how many cases (>=2 factors present) have allocation_supported. Also 96/48 count check."""
import pandas as pd, numpy as np
s = pd.read_csv("outputs/tables/cases/scenarios.csv"); c = pd.read_csv("outputs/tables/cases/scenario_contrasts.csv")
print(s.groupby("model").agg(cells=("scenario","size"), supported=("supported","sum")))
for mdl, g in c.groupby("model"):
    cs = g.groupby("scenario").agg(nf=("factor","size"), alloc=("allocation_supported","first"))
    print(mdl, "cases with factors present:", len(cs), "| >=2 factors:", int((cs.nf>=2).sum()),
          "| allocation shown (>=2 factors):", int(((cs.nf>=2)&cs.alloc).sum()),
          "| allocation shown (all, incl 1 factor):", int(cs.alloc.sum()))
    a = g[(g.allocation_supported) & (g.groupby('scenario').factor.transform('size') >= 2)].copy()
    a["range_first_last"] = (a.share_if_added_last - a.share_if_added_first).abs()
    print("  rows", len(a), "negative Shapley(RD):", int((a.shapley_share_risk_difference<0).sum()),
          "negative any of 4 shares:", int((a[['shapley_share_risk_difference','shapley_share_log_rr','share_if_added_first','share_if_added_last']]<0).any(axis=1).sum()),
          "| median |last-first|:", round(a.range_first_last.median(),3), "| median |Shapley RD - Shapley logRR|:", round((a.shapley_share_risk_difference-a.shapley_share_log_rr).abs().median(),3))
    # factors whose own contrast CI includes 1
    a["ci_incl_1"] = (a.rr_case_vs_without_low<=1)&(a.rr_case_vs_without_high>=1)
    print("  rows with RR CI incl 1:", int(a.ci_incl_1.sum()), "of", len(a), "; negatives among those:", int(((a.shapley_share_risk_difference<0)&a.ci_incl_1).sum()),
          "; negatives among CI-excl-1:", int(((a.shapley_share_risk_difference<0)&~a.ci_incl_1).sum()))
    # sign of a contrast where CI excludes 1 and RR<1 (genuinely protective)
    print("  rows RR<1 with CI excluding 1:", int(((a.rr_case_vs_without_high<1)).sum()))
