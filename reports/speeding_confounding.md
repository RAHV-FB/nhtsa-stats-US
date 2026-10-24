<!-- Generated from reports/templates/speeding_confounding.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# Speeding and alcohol: how much of the speeding–fatality association survives?

*Phase 2 report (research questions A, B and F; `docs/research_plan_phase2.md` §5.1). CRSS
police-reported crashes 2016–2024 with known severity (crash level), survey-weighted; FARS for
recording checks. Every number is read from `outputs/tables/speeding/` when this report is
rendered. All risk ratios are **adjusted associations** — standardised over all police-reported
crashes, conditional on a crash having happened — not causal effects.*

## Summary

**A. How much of the speeding association is explained statistically by alcohol?** For
exceeding the limit (vs no speeding), the crude fatal risk ratio is
10.0 (8.3–12.2). Adjusting for
alcohol alone takes it to 7.0 (5.7–8.5);
for the road, time, light and driver/vehicle environment alone to
6.4 (5.4–7.6); for
both to 5.2 (4.3–6.3).
Averaged over every order in which the seven covariate blocks can be added, alcohol accounts
for 9% (7–11%)
of the crude log risk ratio — between
4% and
16%
depending on what is already in the model. For speeding of any type the alcohol share is
9% (6–12%).
So alcohol accounts for a real but minority part of the speeding association — about as much
as crash configuration (9%)
and less than the five environment blocks together. About
69%
of the crude log risk ratio **remains** after all recorded circumstances are held fixed.

**B. Does exceeding the limit remain independently associated with fatal severity?** Yes. With
all seven blocks, including crash configuration, the risk ratio is
4.9 (4.1–5.8), retaining
69%
of the crude log risk ratio. Among crashes with **no alcohol involvement** it is
6.5 (5.5–7.8) (police-reported
no alcohol: 8.0 (6.1–10.4)).
It is present by day and by night, in single- and multi-vehicle crashes, on low- and
high-speed roads, before and after 2020, and with hit-and-run crashes excluded. It would
require an unmeasured confounder associated with both exceedance and death by a risk ratio of
7.7
each (E-value for the confidence limit) to explain it away.

**The reverse hypothesis fails too.** Alcohol's association is not explained by speeding:
adjusting for speeding type changes alcohol's risk ratio only from
6.41 to
5.62
(Shapley share of speeding type
4%).
The two behaviours overlap in crashes, but each keeps a large association of its own.

---

## 1. Question and why it matters

Official statistics count a death as "speeding-related" if police judged any driver in the crash
to be speeding, whether or not alcohol, drugs or belt non-use were also present. If speeding
occurred mainly in crashes that were dangerous for other recorded reasons, its apparent
association with fatality would partly be borrowed from them. Phase 1 already showed that
"speeding" mixes exceeding the limit (large association) with "too fast for conditions"
(little). It always adjusted for alcohol together with ten other blocks, so it could not say how
much of the speeding association is specifically alcohol's.

## 2. Where speeding occurs (estimated)

*Source: `speeding/type_composition`; weighted shares of police-reported crashes.*

| Domain | Any speeding | Exceeded limit / racing | Too fast for conditions | Exceedance as share of speeding |
|---|---|---|---|---|
| All crashes | 10.1% | 0.85% | 7.9% | 8% |
| Alcohol (imputed): no | 9.7% | 0.74% | 7.8% | 8% |
| Alcohol (imputed): yes | 16.9% | 2.88% | 11.0% | 17% |
| Drugs (police): yes | 16.0% | 4.11% | 8.8% | 26% |
| Night (21–05) | 13.1% | 1.85% | 9.1% | 14% |
| Single-vehicle crash | 15.3% | 1.84% | 11.1% | 12% |
| Snow / ice surface | 36.6% | 0.60% | 32.5% | 2% |
| Limit 60+ mph | 20.7% | 0.89% | 18.3% | 4% |
| Severity O/C/B | 9.9% | 0.75% | 7.9% | 8% |
| Severity K (fatal) | 20.4% | 7.32% | 9.1% | 36% |

Exceeding the limit is about four times as common in alcohol-involved as in other crashes,
and concentrated at night and in single-vehicle crashes; "too fast for conditions" dominates on
snow and ice and on 60+ mph roads. Among fatal crashes about a third of recorded speeding is
exceedance, against under a tenth among minor crashes. The overlap of exceedance with alcohol is
what makes the confounding question real.

## 3. Sequential and Shapley accounting (adjusted association)

*Sources: `speeding/key_models`, `speeding/shapley`, `speeding/sequential`,
`speeding/behaviour_change`. Every model uses the same 467,008 crashes and standardises to the
same population, so changes are not artefacts of sample or non-collapsibility.*

**Key models, exceeding the limit (fatal):**

| Model | Standardised RR | RD per 1,000 | Share of crude log-RR retained | Conditional OR |
|---|---|---|---|---|
| crude | 10.03 (8.26–12.18) | 44.7 (36.0–53.4) | 1.00 | 10.50 (8.58–12.85) |
| other_behaviour_only | 6.97 (5.74–8.48) | 30.0 (24.0–36.1) | 0.84 | 7.33 (5.99–8.98) |
| environment_only | 6.40 (5.35–7.65) | 27.3 (21.3–33.2) | 0.80 | 6.98 (5.75–8.47) |
| environment_and_other_behaviour | 5.22 (4.34–6.27) | 21.6 (16.6–26.5) | 0.72 | 5.71 (4.67–6.98) |
| all_blocks | 4.88 (4.12–5.79) | 19.7 (15.1–24.2) | 0.69 | 5.94 (4.83–7.31) |
| configuration_only | 6.47 (5.42–7.72) | 27.7 (21.6–33.7) | 0.81 | 7.21 (5.90–8.80) |

**Shapley shares of the crude log-RR (exceeded the limit, fatal), all seven blocks:**

| Block | Share of crude log-RR | Smallest share (any order) | Largest share (any order) |
|---|---|---|---|
| calendar_area | 1% (-1 to 3%) | -0% | 3% |
| time | 4% (4–5%) | 1% | 12% |
| light | 3% (2–3%) | -0% | 9% |
| road_environment | 1% (-1 to 3%) | -2% | 5% |
| driver_vehicle_mix | 4% (3–6%) | 2% | 7% |
| alcohol | 9% (7–11%) | 4% | 16% |
| configuration | 9% (6–12%) | 3% | 19% |
| retained_after_all_blocks | 69% (65–73%) | — | — |

**The same without crash configuration (treating it as a mediator to be left out):**

| Block | Share of crude log-RR |
|---|---|
| calendar_area | 1% (-1 to 3%) |
| time | 5% (5–6%) |
| light | 3% (3–4%) |
| road_environment | 2% (-0 to 5%) |
| driver_vehicle_mix | 5% (4–7%) |
| alcohol | 11% (9–14%) |
| retained_after_all_blocks | 72% (68–75%) |

*How much alcohol accounts for depends on what is already in the model.* Added to the crude
model, alcohol removes
16% (13–18%)
of the crude log-RR; added after all five environment blocks and configuration, it removes
4% (3–6%).
The difference arises because alcohol, night, darkness, single-vehicle crashes and young drivers
travel together: once those are held fixed, little of the alcohol–exceedance overlap remains to
remove. Neither number is "the" alcohol share; the Shapley value averages over all orders.

**Any speeding (fatal):**

| Model | Standardised RR | Share retained |
|---|---|---|
| crude | 2.36 (1.89–2.96) | 1.00 |
| other_behaviour_only | 2.04 (1.67–2.50) | 0.83 |
| environment_only | 2.02 (1.66–2.46) | 0.82 |
| environment_and_other_behaviour | 1.82 (1.51–2.19) | 0.70 |
| all_blocks | 2.07 (1.82–2.36) | 0.85 |
| configuration_only | 2.07 (1.80–2.37) | 0.84 |

| Block | Share of crude log-RR |
|---|---|
| calendar_area | 3% (-2 to 9%) |
| time | 3% (2–5%) |
| light | 2% (1–4%) |
| road_environment | -4% (-9 to 1%) |
| driver_vehicle_mix | 4% (2–6%) |
| alcohol | 9% (6–12%) |
| configuration | -3% (-17 to 11%) |
| retained_after_all_blocks | 85% (70–99%) |

**Fatal-or-serious (KA) outcome, exceeded the limit:** crude
5.09 (4.51–5.75), all blocks
2.97 (2.70–3.27); alcohol's Shapley
share 7% (6–8%).

**Alcohol as the exposure (fatal), speeding type as a block:**

| Block | Share of crude log-RR | Smallest | Largest |
|---|---|---|---|
| calendar_area | 1% (0–3%) | 1% | 3% |
| time | 8% (7–10%) | 2% | 17% |
| light | 5% (4–6%) | 0% | 13% |
| road_environment | 3% (2–5%) | -1% | 8% |
| driver_vehicle_mix | -0% (-1 to 0%) | -3% | 1% |
| speeding_type | 4% (3–5%) | 2% | 7% |
| configuration | 18% (16–21%) | 12% | 27% |
| retained_after_all_blocks | 59% (54–64%) | — | — |

*Reading the decompositions.* For exceedance, alcohol and crash configuration are the two
largest single blocks (each about a tenth of the crude log-RR) and most of the association
remains after all seven. For alcohol, crash configuration is by far the largest block
(18%)
and speeding type is small
(4%);
alcohol retains less of its crude association
(59%)
than exceedance does. Alcohol's association runs to a large extent through *which kind of
crash* happens, consistent with impairment acting at Stage A (crash occurrence: departures,
head-on), whereas exceedance keeps most of its association within crash types, consistent with
speed acting at Stage B (energy within a crash). For any speeding, the configuration block's share is not distinguishable from zero
(-3% (-17 to 11%)).

## 4. Stratified associations (Q2)

*Source: `speeding/strata`. Model-A blocks minus those defining the stratum; ratio of the two
strata RRs with a design-based CI and p-value.*

| Split | Stratum | Exposed crashes | Exposed fatal | Adjusted RR | Ratio (2nd / 1st stratum) | p |
|---|---|---|---|---|---|---|
| alcohol_imputed | no alcohol | 4,593 | 555 | 6.54 (5.45–7.84) | — | — |
| alcohol_imputed | alcohol | 1,291 | 316 | 3.29 (2.67–4.05) | 0.50 (0.42–0.61) | 4.6e-09 |
| alcohol_police | police: no alcohol | 3,341 | 308 | 7.99 (6.14–10.38) | — | — |
| alcohol_police | police: alcohol | 1,119 | 216 | 3.21 (2.49–4.15) | 0.40 (0.32–0.51) | 6.4e-10 |
| night | day (06-20) | 3,706 | 461 | 6.22 (4.94–7.83) | — | — |
| night | night (21-05) | 2,149 | 403 | 4.27 (3.51–5.20) | 0.69 (0.54–0.87) | 0.0023 |
| vehicles | single vehicle | 3,310 | 464 | 3.44 (2.94–4.02) | — | — |
| vehicles | multi-vehicle | 2,574 | 407 | 7.70 (5.92–10.02) | 2.24 (1.80–2.79) | 3.2e-09 |
| speed_environment | limit <= 45 mph | 3,921 | 545 | 6.24 (5.13–7.60) | — | — |
| speed_environment | limit >= 50 mph | 1,649 | 302 | 3.79 (2.99–4.82) | 0.61 (0.48–0.77) | 9.1e-05 |
| period | 2016-2019 | 2,432 | 317 | 4.30 (3.40–5.43) | — | — |
| period | 2020-2024 | 3,452 | 554 | 5.96 (4.94–7.19) | 1.39 (1.13–1.70) | 0.0022 |
| hit_and_run | hit-and-run excluded | 5,245 | 838 | 5.53 (4.57–6.71) | — | — |

* **Without alcohol the association is stronger, not weaker** — the relative excess of
  exceedance is larger where the baseline risk is lower. This contradicts the hypothesis that
  exceedance looks dangerous mainly because of alcohol.
* The *relative* association is also weaker at night, in single-vehicle crashes and on 50+ mph
  roads, where the baseline risk is already high. On the *absolute* scale the excess is larger
  where alcohol is present (60
  vs 22 extra fatal
  crashes per 1,000; point estimates, each standardised within its stratum), at night
  (36 vs
  21) and on 50+ mph
  roads (29 vs
  19). The
  formal additive contrast for exceedance × alcohol, with its interval, is in
  `reports/multifactor_interactions.md` §2.
* The association is larger in 2020–2024 than in 2016–2019, consistent with the Phase-1 finding
  that the post-2020 rise in severity was clearest in speeding-related crashes.
* Any speeding (pooled types), for comparison:

| Split | Stratum | Adjusted RR | p |
|---|---|---|---|
| alcohol_imputed | no alcohol | 1.90 (1.55–2.34) | — |
| alcohol_imputed | alcohol | 1.56 (1.25–1.95) | 0.067 |
| alcohol_police | police: no alcohol | 2.06 (1.70–2.50) | — |
| alcohol_police | police: alcohol | 1.63 (1.34–1.99) | 0.019 |
| night | day (06-20) | 1.70 (1.38–2.11) | — |
| night | night (21-05) | 1.90 (1.57–2.29) | 0.23 |
| vehicles | single vehicle | 1.67 (1.43–1.96) | — |
| vehicles | multi-vehicle | 1.94 (1.51–2.49) | 0.17 |
| speed_environment | limit <= 45 mph | 2.35 (1.84–3.00) | — |
| speed_environment | limit >= 50 mph | 1.24 (1.04–1.48) | 2.5e-08 |
| period | 2016-2019 | 1.55 (1.29–1.88) | — |
| period | 2020-2024 | 2.01 (1.64–2.47) | 0.00082 |
| hit_and_run | hit-and-run excluded | 1.88 (1.52–2.32) | — |

## 5. Could differential recording explain the association?

*Sources: `speeding/fars_crss_recording`, `speeding/stratified_qba`, `speeding/e_values`.*

**Recording completeness by alcohol (observed vs estimated).** Among fatal crashes, police in
CRSS jurisdictions record speeding less often than FARS analysts, who use more sources:

| Alcohol stratum | Measure | FARS share | CRSS share | CRSS / FARS |
|---|---|---|---|---|
| no alcohol | any speeding | 22.9% | 18.8% (16.6–21.2%) | 0.82 (0.72–0.92) |
| no alcohol | exceeded limit / racing | 8.8% | 6.3% (5.2–7.6%) | 0.72 (0.60–0.86) |
| alcohol | any speeding | 37.5% | 25.1% (22.1–28.4%) | 0.67 (0.59–0.76) |
| alcohol | exceeded limit / racing | 16.0% | 10.2% (8.1–12.8%) | 0.64 (0.51–0.80) |
| all | any speeding | 27.2% | 20.4% (18.3–22.7%) | 0.75 (0.67–0.83) |
| all | exceeded limit / racing | 10.9% | 7.3% (6.1–8.8%) | 0.67 (0.56–0.81) |

For any speeding, the point estimate of CRSS recording relative to FARS is lower in
alcohol-involved fatal crashes than in others (the intervals overlap and the difference was not
formally tested); for exceedance the two are close. (The two systems'
alcohol measures differ — imputed police report in CRSS, multiply imputed BAC in FARS — so the
comparison is approximate.) This does not support the competing explanation that police
record speeding *more* readily once alcohol is found, which would have inflated the apparent
overlap of the two behaviours; if anything, speeding is under-recorded in alcohol-involved
crashes.

**Outcome-dependent recording.** If exceedance in non-fatal crashes is recorded less completely
than in fatal ones, the crude RR is inflated. Within the no-alcohol stratum the observed crude
RR of 9.9
becomes 5.6
if non-fatal exceedance were recorded only half as completely (fatal sensitivity 0.9), and
2.2 at
a fifth. In the alcohol stratum the same scenarios give
2.3
and 0.84.
The association survives moderate differential recording; only severe under-recording in
non-fatal crashes would remove it, and the alcohol-stratum association is the more fragile.

## 6. Selection by fatality: why co-occurrence among deaths misleads

*Source: `speeding/selection_by_fatality`.*

| Speeding measure | Population | Speeding–alcohol odds ratio | Interval |
|---|---|---|---|
| any speeding | CRSS all crashes | 1.90 (1.61–2.23) | 95% CI (design-based) |
| any speeding | CRSS non-fatal crashes | 1.87 (1.59–2.20) | 95% CI (design-based) |
| any speeding | CRSS fatal crashes | 1.41 (1.20–1.65) | 95% CI (design-based) |
| exceeded limit / racing | CRSS all crashes | 4.24 (3.65–4.93) | 95% CI (design-based) |
| exceeded limit / racing | CRSS non-fatal crashes | 4.05 (3.46–4.74) | 95% CI (design-based) |
| exceeded limit / racing | CRSS fatal crashes | 1.71 (1.42–2.05) | 95% CI (design-based) |
| any speeding | FARS fatal crashes (census; alcohol by multiple imputation) | 2.08 (2.07–2.09) | range over 10 implicates |
| exceeded limit / racing | FARS fatal crashes (census; alcohol by multiple imputation) | 2.32 (2.31–2.33) | range over 10 implicates |

Within one recording system (CRSS), the speeding–alcohol association is weaker among fatal
crashes than among all crashes — for exceedance
1.71
against 4.24.
Both behaviours raise the chance that a crash is fatal, so a fatal crash without alcohol is more
likely to have *another* reason to be fatal, such as speeding (collider stratification). FARS
records both behaviours more completely than CRSS police reports; its odds ratios
(2.08
for any speeding, 2.32
for exceedance) are larger than the CRSS fatal-crash values but, for exceedance, still about
half the all-crash association. Two forces therefore act on FARS-only co-occurrence statistics —
selection on fatality weakens the association, fuller recording strengthens it — and a
"speeding and alcohol" category among deaths cannot be read as the overlap of the two
behaviours in the crashes that produced the deaths.

## 7. Interpretation

* **What survives.** A large association between exceeding the limit and fatal outcomes,
  present without alcohol, by day and night, in single- and multi-vehicle crashes, on lower- and
  higher-speed roads, before and after 2020, and robust to
  moderate recording bias. A large association for alcohol that is not explained by speeding.
* **What changes.** "Speeding" as a category: most of its association belongs to exceedance,
  which is under a tenth of recorded speeding in minor crashes. The share of the exceedance
  association that alcohol accounts for depends on the model — from
  16%
  when alcohol is the only adjustment to
  4%
  when it is added last — and averages
  9%
  of the crude log-RR.
* **What does not follow.** That alcohol "causes" a tenth of speeding deaths, or that speeding
  deaths are "really" alcohol deaths: the decomposition is of a statistical association, the
  ordering of blocks is unverifiable, configuration is plausibly a mediator, and both
  behaviours are recorded after the crash.
* **Mechanisms consistent with the pattern.** Alcohol is associated with *which* crashes happen
  (configuration absorbs much of its association; Stage A), exceedance with how violent a crash
  of a given type is (it keeps its association within configuration; Stage B). This is a
  hypothesis compatible with the decompositions, not a demonstrated pathway: impact speed is not
  observed.

**Answer to H (speeding statistics).** Counts of "speeding-related deaths" combine a strongly
fatality-associated behaviour (exceeding the limit) with a weakly associated one (too fast for
conditions), and about two-fifths of them also involve a drunk driver
(`reports/factor_contributions.md`). They should be read as deaths *involving* speeding, not
deaths *caused* by speeding, and should not be added to alcohol-related deaths.

## 8. What stronger evidence would require

Measured travel and impact speed (event data recorders), speed observations from uncrashed
traffic (exposure), alcohol and drug measurement independent of severity, and variation in
speed enforcement or limits over place and time with comparison areas.
