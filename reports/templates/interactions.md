# Which circumstances amplify each other? Interactions and co-occurrence in crash severity

*CRSS police-reported crashes 2016–2024 (survey-weighted). Outcome: the crash is fatal (K), with
fatal-or-serious (KA) as a check. Every number below is read from `outputs/tables/interactions/`
when this report is rendered.*

## Why interaction is not co-occurrence

Two circumstances often appear together in fatal crashes simply because each is common in
fatal crashes, or because they tend to co-occur in all crashes. Neither pattern shows that one
*amplifies* the other. This report therefore keeps three quantities apart:

1. **Co-occurrence**: how much more often A and B appear together than they would if they
   were independent (observed/expected joint prevalence), among all crashes and among fatal
   crashes.
2. **Additive interaction**: whether the excess fatality risk when both are present exceeds
   the sum of the separate excesses. It is reported as the interaction contrast
   IC = p11 − p10 − p01 + p00, per 1,000 crashes. This scale determines how many *extra*
   fatal crashes the combination produces, so it is the relevant scale for burden and
   targeting. A positive additive interaction (IC or RERI > 0) is expected whenever two factors
   each raise risk and combine multiplicatively, so it shows where excess deaths concentrate
   (burden), not a special mechanism.
3. **Multiplicative interaction**: whether the risk ratio of A differs when B is present,
   reported as RR11 / (RR10 × RR01). A combination is called *amplifying* in this report only
   when this ratio of risk ratios is above 1 with a confidence interval that excludes 1.

Adjusted risks p00, p10, p01, p11 are standardised predictive margins from a survey-weighted
logistic model. The model contains the full pre-crash adjustment set (model A; model B adds
crash configuration for pedestrian- and angle-crash pairs) plus one product term for the pair.
The margins are standardised to the covariate mix of *all* police-reported crashes (the angle
pair: all multi-vehicle crashes). For example, p11 for "pedestrian × unlit darkness" is the
risk if every crash — with its own roads, speed limits, areas and drivers — were a pedestrian
crash in unlit darkness. It is not the observed fatality rate among pedestrian crashes, which
happen in a different mix of places.

Thirteen pairs were registered in advance (`docs/research_plan.md`, RQ2; operational
definitions in its change log). The rationale for each is recorded in the output table.
p-values are Holm-adjusted across these 13 pairs, separately for each scale. Confidence
intervals are design-based (Taylor linearisation, {{descriptive/crss_design||design_df|.0f}} df).

## Results: registered pairs, fatal outcome

{{mdtable:interactions/pairs_fatal|prespecified=True|pair:Pair (A x B):;adj_p00:Risk with neither (per 1,000):cix1000:1;adj_p11:Risk with both (per 1,000):cix1000:1;rr_A_given_B0:RR of A when B absent:ci:2;rr_A_given_B1:RR of A when B present:ci:2;ic:Additive interaction (per 1,000):cix1000:1;ic_p_holm:Holm p, additive:.2g;ratio_of_rr:Ratio of RRs (multiplicative):ci:2;ratio_of_rr_p_holm:Holm p, multiplicative:.2g;obs_exp_all:Co-occurrence O/E, all crashes:.2f;min_cell_events:Fewest events in a cell:,.0f}}

Figure: `outputs/figures/summary/interactions.png`.

### What the pattern shows

**Pedestrian crashes in unlit darkness are super-multiplicative, and so also carry a large additive excess.**
The standardised risk that a crash is fatal when it is a pedestrian crash in unlit darkness is
{{interactions/pairs_fatal|pair=pedestrian x dark_unlit|adj_p11|cix1000:0}} per 1,000, against
{{interactions/pairs_fatal|pair=pedestrian x dark_unlit|adj_p00|cix1000:1}} for a
non-pedestrian crash in daylight. The pedestrian risk ratio is
{{interactions/pairs_fatal|pair=pedestrian x dark_unlit|rr_A_given_B0|ci:1}} in daylight and
{{interactions/pairs_fatal|pair=pedestrian x dark_unlit|rr_A_given_B1|ci:1}} in unlit darkness:
a ratio of risk ratios of {{interactions/pairs_fatal|pair=pedestrian x dark_unlit|ratio_of_rr|ci:2}}
(Holm p {{interactions/pairs_fatal|pair=pedestrian x dark_unlit|ratio_of_rr_p_holm|.2g}}), that is,
the two risks combine by more than multiplying. Because an additive excess is expected whenever two
risks multiply, the additive excess of {{interactions/pairs_fatal|pair=pedestrian x dark_unlit|ic|cix1000:0}} fatal
crashes per 1,000 (Holm p {{interactions/pairs_fatal|pair=pedestrian x dark_unlit|ic_p_holm|.2g}})
follows from it and is not separate evidence.

**Motorcycle crashes involving alcohol: a large additive excess.** The ratio of risk ratios is
{{interactions/pairs_fatal|pair=motorcycle x alcohol|ratio_of_rr|ci:2}}, but the additive
excess is {{interactions/pairs_fatal|pair=motorcycle x alcohol|ic|cix1000:0}} per 1,000
(Holm p {{interactions/pairs_fatal|pair=motorcycle x alcohol|ic_p_holm|.2g}}), giving a
standardised fatal risk of {{interactions/pairs_fatal|pair=motorcycle x alcohol|adj_p11|cix1000:0}}
per 1,000. The two scales answer different questions. On the ratio scale, alcohol involvement is
associated with a *smaller* relative excess in motorcycle crashes than in other crashes (the
combination is sub-multiplicative), but because motorcycle crashes start from a much higher
baseline, the absolute excess associated with alcohol is far larger.
The additive excess shows where excess deaths concentrate (burden): it is expected whenever two
factors each raise risk, even if they combine multiplicatively or less, so it is not evidence
of a special mechanism.

**Heavy trucks on 50+ mph roads.** The additive excess is
{{interactions/pairs_fatal|pair=heavy_truck x high_speed_road|ic|cix1000:1}} per 1,000
(Holm p {{interactions/pairs_fatal|pair=heavy_truck x high_speed_road|ic_p_holm|.2g}}). The ratio
of risk ratios is {{interactions/pairs_fatal|pair=heavy_truck x high_speed_road|ratio_of_rr|ci:2}}
(Holm p {{interactions/pairs_fatal|pair=heavy_truck x high_speed_road|ratio_of_rr_p_holm|.2g}}).
The multiplicative excess counts as supported only if its Holm-adjusted p-value is small and
the interval for the ratio of risk ratios excludes 1; the additive excess alone shows where
deaths concentrate, not why.

**Several commonly assumed amplifiers are not detected for the fatal outcome.** Speeding in
unlit darkness (ratio of RRs {{interactions/pairs_fatal|pair=speeding x dark_unlit|ratio_of_rr|ci:2}})
and a young driver late at night
({{interactions/pairs_fatal|pair=young_driver x late_night|ratio_of_rr|ci:2}}) show no detectable
excess on the ratio scale; the intervals do not exclude a moderate one, so this is absence of
evidence, not evidence of absence. For fatal-or-serious (KA) crashes, speeding in unlit darkness
shows an additive excess of
{{interactions/pairs_ka|pair=speeding x dark_unlit|ic|cix1000:1}} per 1,000 (Holm p
{{interactions/pairs_ka|pair=speeding x dark_unlit|ic_p_holm|.1g}}) and a ratio of risk ratios of
{{interactions/pairs_ka|pair=speeding x dark_unlit|ratio_of_rr|ci:2}} (Holm p
{{interactions/pairs_ka|pair=speeding x dark_unlit|ratio_of_rr_p_holm|.2g}}). A young driver late
at night has a ratio of risk ratios of
{{interactions/pairs_ka|pair=young_driver x late_night|ratio_of_rr|ci:2}} for KA crashes (Holm p
{{interactions/pairs_ka|pair=young_driver x late_night|ratio_of_rr_p_holm|.2g}}). Behavioural
factors are recorded differently by severity, which can bias associations in either direction
(the police-recorded alcohol, drug, distraction and speeding fields are more often unknown in
fatal crashes, while killed drivers are tested far more often), and can create such patterns. Rural area × unlit darkness
({{interactions/pairs_fatal|pair=rural x dark_unlit|ratio_of_rr|ci:2}}), weekend × late night
({{interactions/pairs_fatal|pair=weekend x late_night|ratio_of_rr|ci:2}}) and 50+ mph road ×
unlit darkness ({{interactions/pairs_fatal|pair=high_speed_road x dark_unlit|ratio_of_rr|ci:2}})
have ratios of risk ratios below 1. Each factor matters on its own, but the combination is not
more severe than the separate factors imply.

**Speeding on wet roads is less severe than expected.** The additive interaction is
{{interactions/pairs_fatal|pair=speeding x wet|ic|cix1000:1}} per 1,000. Police
"speeding-related" is mostly "too fast for conditions", which concentrates on wet and icy roads
and carries little excess fatal risk (`reports/findings.md`, finding 3), so the pair mixes two
different exposures; a mix of speeding types is one possible reason for the deficit, not an
established one. The exploratory analysis below separates drivers who exceeded the limit, and
the deficit persists there.

## Exploratory pairs (not in the registered family)

Two pairs were added when the analysis was implemented (speeding × 50+ mph road, pedestrian ×
50+ mph road), and three after the speeding-type analysis (drivers who exceeded the limit).
They are outside the Holm family and are hypothesis-generating; p-values are unadjusted.

{{mdtable:interactions/pairs_fatal|prespecified=False|pair:Pair:;adj_p00:Risk with neither (per 1,000):cix1000:1;adj_p11:Risk with both (per 1,000):cix1000:1;rr_A_given_B0:RR of A when B absent:ci:2;rr_A_given_B1:RR of A when B present:ci:2;ic:Additive interaction (per 1,000):cix1000:1;ic_p:p, additive:.2g;ratio_of_rr:Ratio of RRs:ci:2;ratio_of_rr_p:p, multiplicative:.2g}}

* **Pedestrian crashes on 50+ mph roads** have the largest additive excess of any pair,
  {{interactions/pairs_fatal|pair=pedestrian x high_speed_road|ic|cix1000:0}} per 1,000, with a
  standardised fatal risk of {{interactions/pairs_fatal|pair=pedestrian x high_speed_road|adj_p11|cix1000:0}}
  per 1,000. On the ratio scale the combination is
  {{interactions/pairs_fatal|pair=pedestrian x high_speed_road|ratio_of_rr|ci:2}}: the speed
  environment multiplies pedestrian risk by a somewhat larger factor than other risks
  (exploratory, unadjusted p {{interactions/pairs_fatal|pair=pedestrian x high_speed_road|ratio_of_rr_p|.2f}}; KA
  {{interactions/pairs_ka|pair=pedestrian x high_speed_road|ratio_of_rr|ci:2}}), and from a much higher baseline.
* **Exceeding the limit on wet roads keeps its deficit.** The risk ratio for limit exceedance
  is {{interactions/pairs_fatal|pair=exceeded_limit x wet|rr_A_given_B1|ci:2}} on wet roads and
  {{interactions/pairs_fatal|pair=exceeded_limit x wet|rr_A_given_B0|ci:2}} on dry roads. The
  additive interaction (the excess for exceedance on wet roads relative to dry roads) is
  {{interactions/pairs_fatal|pair=exceeded_limit x wet|ic|cix1000:1}} per 1,000 fatal crashes
  (unadjusted p {{interactions/pairs_fatal|pair=exceeded_limit x wet|ic_p|.2g}}), and for
  fatal-or-serious crashes {{interactions/pairs_ka|pair=exceeded_limit x wet|ic|cix1000:1}} per
  1,000. The ratio-scale estimate, {{interactions/pairs_fatal|pair=exceeded_limit x wet|ratio_of_rr|ci:2}}
  for fatal crashes ({{interactions/pairs_ka|pair=exceeded_limit x wet|ratio_of_rr|ci:2}} for KA),
  is imprecise for fatal crashes. The deficit on the additive scale therefore does not depend on
  the mix of speeding types, so the registered speeding × wet pattern is not explained by that
  mix alone; the lower baseline risk on wet roads and the unobserved impact speed remain
  candidate explanations that these data cannot separate.
* **Exceeding the limit on 50+ mph roads**: ratio of RRs
  {{interactions/pairs_fatal|pair=exceeded_limit x high_speed_road|ratio_of_rr|ci:2}}; below 1
  means the relative excess of exceeding the limit is smaller on roads that are already fast.

## Stability across periods

The same models refitted separately for 2016–2019 and 2020–2024:

**2016–2019**

{{mdtable:interactions/pairs_fatal_by_period|period=2016-2019;prespecified=True|pair:Pair:;ic:Additive interaction (per 1,000):cix1000:1;ratio_of_rr:Ratio of RRs:ci:2;min_cell_events:Fewest events:,.0f}}

**2020–2024**

{{mdtable:interactions/pairs_fatal_by_period|period=2020-2024;prespecified=True|pair:Pair:;ic:Additive interaction (per 1,000):cix1000:1;ratio_of_rr:Ratio of RRs:ci:2;min_cell_events:Fewest events:,.0f}}

Where the two periods' intervals overlap widely, the interaction is stable. Fewer events per
period widen the intervals, so a pair that is significant pooled but not within each period
is not evidence of change.

## Fatal-or-serious (KA) outcome

{{mdtable:interactions/pairs_ka|prespecified=True|pair:Pair:;adj_p00:Risk with neither (per 1,000):cix1000:1;adj_p11:Risk with both (per 1,000):cix1000:1;ic:Additive interaction (per 1,000):cix1000:1;ratio_of_rr:Ratio of RRs:ci:2}}

## Three-factor combinations

These are estimated only when the fully exposed cell contains at least 20 fatal crashes.

{{mdtable:interactions/triples_fatal|outcome=fatal|combination:Combination:;p111_n_events:Fatal crashes with all three:,.0f;adj_p000:Risk with none (per 1,000):cix1000:1;adj_p111:Risk with all three (per 1,000):cix1000:1;rr_p111:RR, all three vs none:ci:1;ic3:Three-way additive contrast (per 1,000):cix1000:1;excess_over_additive_singles:Excess over sum of single excesses (per 1,000):cix1000:1}}

## What these results do and do not justify

* **Justified:** "Among police-reported crashes, the excess fatality risk of a pedestrian crash
  is larger in unlit darkness, beyond the separate excesses, after adjusting for the recorded
  circumstances."
* **Not justified:** that darkness *causes* additional pedestrian deaths by a given amount
  (crash occurrence, exposure and unrecorded factors such as impact speed are not observed),
  or that two factors which co-occur in fatal crashes interact.
* Behavioural factors (speeding, alcohol) are recorded differently by severity, which can bias
  associations in either direction (`reports/findings.md`, finding 9; police-recorded fields are
  more often unknown in fatal crashes, while killed drivers are tested far more often). This can
  create, exaggerate or hide apparent interactions involving them. Interactions among objectively recorded circumstances (light, speed limit,
  crash type, vehicle type) are the most trustworthy.
