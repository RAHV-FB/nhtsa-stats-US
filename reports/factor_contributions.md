<!-- Generated from reports/templates/factor_contributions.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# Factor contributions: association, adjustment, prediction, attribution and counts

*Phase 2 report (research questions A, F and H; `docs/research_plan_phase2.md` §5.4). Every
number is read from `outputs/tables/contributions/` (and the tables named in each section) when
this report is rendered. Estimate types are labelled: **observed** (FARS census), **estimated**
(CRSS design-based), **adjusted association** (model-based, not causal), **model-predicted**,
and **predictive** (out-of-sample prediction).*

## Summary

1. **Official counts overlap so heavily that they cannot be added.** Of
   353,706 US road deaths in
   2016–2024 (FARS, observed), 98,693
   occurred in speeding-related crashes, 105,821
   in crashes with a driver at BAC ≥ .08, at least 84,207
   in crashes with a drug-positive driver, and 96,706
   were unbelted occupants. These four counts sum to
   109%
   of all deaths, but only 65%
   of deaths involve any of them: each death in this group is counted
   1.68
   times on average. About 70%
   of speeding-related deaths also involve one of the other three factors.
2. **Statistical attribution is also non-additive.** In the severity-pathway model, removing
   speeding accounts for 8.9% (6.7–11.1%)
   of fatal crashes and removing alcohol for
   19.4% (16.3–22.5%),
   but removing both accounts for 25.7% (22.3–29.1%),
   not the sum. A Shapley allocation of the joint fraction credits
   71%
   to alcohol and 29%
   to speeding — a convention for dividing a model quantity, not a causal split.
3. **Each meaning of "contribution" ranks the factors differently** (§5). Exceeding the limit
   has the largest adjusted risk ratio and risk difference; alcohol the largest attributed burden
   and the most deaths, and the largest predictive information alone and by Shapley value (but
   not when removed last, where speeding type loses more); "too fast for conditions"
   is common but weakly associated. Police-recorded drug involvement cannot be ranked.
4. **Most predictive information is in crash configuration and environment, not behaviour.**
   On held-out years, crash configuration carries
   47% of the explained
   log-likelihood, the road/time environment 20%,
   alcohol 8% and speeding type
   6%. Behaviours are rare;
   prediction rewards common, informative variables.

## Answers to the Phase-2 questions at a glance

| | Question | Answer (details in) |
|---|---|---|
| A | How much of the speeding–fatality association is explained statistically by alcohol and other recorded factors? | For exceeding the limit, alcohol accounts for 9% of the crude log-RR on average over orderings (4%–16%); all recorded circumstances together leave 69% (`reports/speeding_confounding.md`) |
| B | Does exceeding the limit remain independently associated with fatal severity? | Yes: adjusted RR 4.9 (4.1–5.8); 6.5 (5.5–7.8) without alcohol; robust to moderate recording bias (same report) |
| C | Can alcohol and drugs be separated reliably? | Only in a narrow, selected population (tested drivers in fatal crashes, four high-testing states); not in general (`reports/alcohol_drugs_restraints.md`) |
| D | How much does restraint use change fatality associations within comparable occupants? | Within the same vehicle, belted occupants' risk is 0.34 (0.33–0.35) times unbelted occupants', unchanged by the driver's speeding or alcohol (same report) |
| E | Which combinations show interaction? | Super-additive: exceedance × alcohol, behaviour × belt non-use; sub-multiplicative at crash level, multiplicative for single-vehicle drivers; three-way terms not detected; four-way with drugs not estimable (`reports/multifactor_interactions.md`) |
| F | How much do contributions depend on units, definitions, specifications and missingness? | Strongly: crash vs driver vs passenger vs pedestrian (alcohol RR from 1.2 to 4.7); "any speeding" vs exceedance; with or without configuration; police drugs as a covariate; drug unknowns (§2–§5 below) |
| G | Can a principal cause of an individual death be identified? | No (`reports/case_comparisons.md` §3) |
| H | How should official statistics be read? | As overlapping counts of deaths *involving* circumstances, recorded with severity-dependent completeness; not additive, not causes (§6 below) |

---

## 0. Four stages, and which the data identify

*Source: `stages/identifiability`, `stages/death_timing`, `stages/ems_availability`.*

```
 A  crash occurrence      impairment, speeding, night, road, driver age     NOT identified (no exposure)
          │  selection: only police-reported crashes (CRSS) / fatal crashes (FARS) are recorded
 B  configuration/energy  posted limit, recorded speeding, crash type      associations only
          │                (travel and impact speed not observed)
 C  injury given crash    belt, age, sex, seat, vehicle, vulnerability      closest to identified
          │                                                                 (within-vehicle designs)
 D  post-crash survival   EMS notification/arrival, transport, time of death  NOT identified
```

Arrows are hypotheses about mechanisms, not relationships the data establish. Stage D is not
identifiable: EMS times exist only for fatal crashes (FARS), so there are no survivors with
comparable injuries and different response times, and CRSS has no EMS times. Descriptively,
57% of the
353,706 deaths in 2016–2024 occurred at the scene
and 65% within an hour of the crash
(at the scene included) — 65%
at the scene for unbelted and 57%
for belted occupants, 67% on rural
and 49% on urban roads. Most of the
burden is therefore fixed before post-crash care could act, but the data cannot say how many
later deaths better care would have prevented.

## 1. Ten quantities that are not the same thing

| # | Quantity | Where | Meaning |
|---|---|---|---|
| 1 | Prevalence among police-reported crashes | §5, `contributions/ranking` | how common the factor is in crashes |
| 2 | Prevalence among fatal crashes | §5 | how common it is in fatal crashes |
| 3 | Co-occurrence with other factors | `speeding/selection_by_fatality`, `contributions/fars_pairwise_overlap` | overlap, not interaction |
| 4 | Crude fatality risk given a crash | §2 | association without adjustment |
| 5 | Adjusted fatality risk (RR, RD) | §2 | association holding recorded circumstances fixed |
| 6 | Incremental predictive information | §3 | how much better fatal crashes are predicted |
| 7 | Statistical contribution to explained risk differences | `speeding/shapley`, `reports/speeding_confounding.md` | accounting of a change in a model quantity |
| 8 | Evidence for a causal interpretation | all reports | design arguments, bias analyses |
| 9 | Population burden | §4 | deaths involving or statistically attributed to the factor |
| 10 | Uncertainty and measurement | §6, `reports/alcohol_drugs_restraints.md` | intervals and what they omit |

## 2. Crude and adjusted associations on a fixed sample (adjusted association)

*Source: `contributions/nested_models`. CRSS crashes 2016–2024, n =
467,008; standardised risk ratios
(RR), risk differences per 1,000 crashes (RD) and conditional odds ratios (OR) from the same
survey logistic models; every step uses the same crashes.*

**Exceeded the limit / racing (vs no speeding):**
| Model | Standardised RR | RD per 1,000 | Conditional OR | Share of crude log-RR retained |
|---|---|---|---|---|
| crude | 10.03 (8.26–12.18) | 44.7 (36.0–53.4) | 10.50 (8.58–12.85) | 1.00 |
| environment | 7.16 (5.96–8.60) | 30.9 (24.1–37.8) | 7.64 (6.29–9.27) | 0.85 |
| + other speeding/alcohol | 5.75 (4.75–6.96) | 24.1 (18.4–29.8) | 6.16 (5.02–7.55) | 0.76 |
| + driver/vehicle mix | 5.20 (4.32–6.25) | 21.4 (16.5–26.3) | 5.69 (4.65–6.96) | 0.71 |
| + police-reported drugs | 5.07 (4.24–6.05) | 21.0 (16.5–25.6) | 5.59 (4.61–6.79) | 0.70 |
| + crash configuration | 4.77 (4.06–5.60) | 19.3 (15.1–23.4) | 5.86 (4.82–7.12) | 0.68 |

**Alcohol involved (imputed):**
| Model | Standardised RR | RD per 1,000 | Conditional OR | Share of crude log-RR retained |
|---|---|---|---|---|
| crude | 6.41 (5.48–7.49) | 24.4 (20.6–28.2) | 6.57 (5.60–7.70) | 1.00 |
| environment | 4.43 (3.69–5.31) | 15.8 (12.6–19.1) | 4.56 (3.79–5.49) | 0.80 |
| + other speeding/alcohol | 4.10 (3.42–4.92) | 14.4 (11.3–17.5) | 4.23 (3.51–5.10) | 0.76 |
| + driver/vehicle mix | 4.11 (3.45–4.90) | 14.5 (11.4–17.5) | 4.34 (3.62–5.22) | 0.76 |
| + police-reported drugs | 3.29 (2.81–3.85) | 10.9 (8.6–13.1) | 3.45 (2.92–4.06) | 0.64 |
| + crash configuration | 2.49 (2.17–2.87) | 7.3 (5.7–9.0) | 2.72 (2.33–3.17) | 0.49 |

**Other speeding types (too fast for conditions, unspecified):**
| Model | Standardised RR | RD per 1,000 | Conditional OR |
|---|---|---|---|
| crude | 1.66 (1.34–2.05) | 3.2 (1.7–4.8) | 1.66 (1.34–2.06) |
| environment | 1.45 (1.18–1.78) | 2.3 (0.9–3.6) | 1.46 (1.18–1.80) |
| + other speeding/alcohol | 1.34 (1.10–1.64) | 1.7 (0.5–2.9) | 1.35 (1.10–1.65) |
| + driver/vehicle mix | 1.31 (1.09–1.58) | 1.6 (0.5–2.7) | 1.32 (1.10–1.60) |
| + police-reported drugs | 1.23 (1.02–1.48) | 1.2 (0.1–2.3) | 1.24 (1.02–1.50) |
| + crash configuration | 1.46 (1.27–1.68) | 2.4 (1.5–3.2) | 1.51 (1.30–1.76) |

**Police-reported drug involvement (not interpretable as a drug association; shown for transparency):**
| Model | Standardised RR | Conditional OR |
|---|---|---|
| crude | 11.73 (9.51–14.46) | 12.22 (9.83–15.19) |
| environment | 8.00 (6.38–10.04) | 8.43 (6.66–10.68) |
| + other speeding/alcohol | 3.95 (3.21–4.88) | 4.11 (3.31–5.11) |
| + driver/vehicle mix | 4.05 (3.30–4.96) | 4.31 (3.48–5.34) |
| + police-reported drugs | 4.05 (3.30–4.96) | 4.31 (3.48–5.34) |
| + crash configuration | 3.71 (3.00–4.58) | 4.24 (3.34–5.38) |

*What the sequence shows.*

* **Adjusting each behaviour for the other** reduces exceedance from
  7.2 to
  5.8 and
  alcohol from 4.4 to
  4.1. Both
  remain large. `reports/speeding_confounding.md` decomposes this in every order.
* **Adding police-recorded drugs** reduces alcohol further, from
  4.11 to
  3.29, but this
  is not evidence that drugs explain the alcohol association: police record drugs mainly when
  they are already investigating alcohol (`drugs/co_occurrence`), so the drug field partly
  re-measures alcohol involvement. This step is reported separately and is not used for
  ranking.
* **Adding crash configuration** (a likely mediator) reduces alcohol to
  2.49 but leaves
  exceedance almost unchanged (4.77):
  much of alcohol's association runs through the *type* of crash (single-vehicle departures,
  head-on), whereas exceedance is associated with higher severity within crash types.
* **Odds ratios drift away from risk ratios** as covariates are added (exceedance: OR
  5.86 vs
  RR 4.77 in the
  last model), although the sample is fixed. This is non-collapsibility: conditional odds
  ratios change when outcome-predictive covariates are added even without confounding, so
  comparing ORs across models overstates or understates "how much was explained". All Phase-2
  comparisons use standardised RRs and RDs.

## 3. Predictive contribution (predictive)

*Source: `contributions/predictive`, `contributions/predictive_lattice`. Models fitted on
2016–2021 and evaluated on 2023–2024 (2022 unused); design-weighted McFadden R² on the test
years (log-likelihood gain over the training base rate) and AUROC; intervals from resampling
test-set PSUs within strata (model fixed).*

| Block | Test R² alone | R² lost when removed from the full model | Shapley R² | Shapley share | AUROC alone | Permutation log-loss increase |
|---|---|---|---|---|---|---|
| speeding_type | 0.023 (0.018–0.027) | 0.013 (0.010–0.016) | 0.016 (0.013–0.019) | 6% | 0.583 | 0.0007 |
| alcohol | 0.036 (0.028–0.045) | 0.009 (0.005–0.013) | 0.020 (0.014–0.026) | 8% | 0.602 | 0.0007 |
| drugs_police | 0.021 (0.013–0.027) | 0.006 (0.000–0.010) | 0.012 (0.006–0.016) | 4% | 0.592 | 0.0006 |
| environment | 0.061 (0.051–0.071) | 0.052 (0.045–0.058) | 0.055 (0.046–0.062) | 20% | 0.736 | 0.0053 |
| driver_vehicle_mix | 0.043 (0.037–0.050) | 0.038 (0.033–0.044) | 0.041 (0.035–0.047) | 15% | 0.622 | 0.0034 |
| configuration | 0.132 (0.121–0.144) | 0.123 (0.112–0.134) | 0.125 (0.114–0.135) | 47% | 0.805 | 0.0145 |

The full model reaches a test R² of 0.268 and
AUROC 0.905. *Interpretation.* Alcohol's
predictive value alone (0.036) is more than
four times its value once everything else is in the model
(0.009), because much of what alcohol
tells a model about severity is also told by the time, road and crash type. Shapley values split
that shared information evenly; drop-when-removed gives it to nobody. Neither is causal
importance. Police-recorded drug status has predictive value
(0.012) partly because its *recording*
depends on severity — a reason it predicts, and a reason it cannot be interpreted.

## 4. Burden: deaths involving a factor vs deaths statistically attributed to it

*Sources: `contributions/fars_overlap_summary`, `contributions/fars_pairwise_overlap`
(observed), `contributions/burden_shapley` (model-predicted, severity pathway only).*

**(a) Deaths involving a factor (FARS 2016–2024, observed; alcohol as expected counts over the
ten BAC implicates; drug positivity only where every driver's status is determinate).**

| Deaths counted under | Deaths | Share of all deaths | Also involve another listed factor |
|---|---|---|---|
| speeding-related crash | 98,693 | 27.9% | 70% |
| driver BAC >= .08 (MI) | 105,821 | 29.9% | 68% |
| driver drug-positive (determinate crashes only) | 84,207 | 23.8% | 71% |
| victim an unbelted vehicle occupant | 96,706 | 27.3% | 71% |
| sum of the four factor counts | 385,427 | 109.0% | — |
| deaths involving at least one factor (union) | 229,041 | 64.8% | — |
| deaths involving none of the four | 124,665 | 35.2% | — |
| all deaths | 353,706 | 100.0% | — |

Pairwise, 41%
of speeding-related deaths also involved a driver at BAC ≥ .08, and
38% of
alcohol-related deaths were in speeding-related crashes
(1.36
times the overlap expected if the two were independent among deaths). The drug count is a
lower bound: 222,767
deaths occurred in crashes where some driver's drug status is undetermined.

**(b) Deaths statistically attributed (severity pathway, model-predicted).** Fractions of
fatal crashes that the model predicts would not have been fatal had the factor been absent,
other recorded circumstances fixed, the crash still happening; FARS-scaled to the 2022–2024
average.

| Quantity | Estimate | FARS-scaled deaths per year |
|---|---|---|
| AF[exceeded] | 5.8% (4.6–7.0%) | 2,368 |
| AF[speeding_other] | 3.1% (1.4–4.8%) | 1,271 |
| AF[alcohol] | 19.4% (16.3–22.5%) | 7,967 |
| AF[exceeded+speeding_other] | 8.9% (6.7–11.1%) | 3,640 |
| AF[exceeded+alcohol] | 23.4% (20.2–26.5%) | 9,578 |
| AF[speeding_other+alcohol] | 21.8% (18.5–25.2%) | 8,942 |
| AF[exceeded+speeding_other+alcohol] | 25.7% (22.3–29.1%) | 10,553 |
| sum of single-factor AFs | 28.3% (24.3–32.3%) | 11,607 |
| overlap = sum of singles - joint | 2.6% (1.9–3.3%) | 1,054 |
| Shapley[exceeded] | 4.9% (3.8–5.9%) | 1,990 |
| Shapley share[exceeded] | 18.9% (14.8–22.9%) | — |
| Shapley[speeding_other] | 2.7% (1.2–4.3%) | 1,123 |
| Shapley share[speeding_other] | 10.6% (5.2–16.1%) | — |
| Shapley[alcohol] | 18.1% (15.2–21.1%) | 7,440 |
| Shapley share[alcohol] | 70.5% (64.1–76.9%) | — |

* Joint removal of speeding (all types) and alcohol: 25.7% (22.3–29.1%);
  the sum of the two single fractions double-counts
  2.6% (1.9–3.3%)
  of fatal crashes.
* The overlap in attributed burden is much smaller than the overlap in *counts* (a), because
  the model attributes to each factor only the excess risk it adds, not every death in which
  it is present.
* Consistency with Phase 1: the Phase-1 fractions (`burden/attributable_fractions_fatal`:
  speeding 9.1%, alcohol
  19.7%, joint
  26.5%) used a
  model with any-speeding instead of speeding type; the Phase-2 values above agree within their
  intervals.

**What these are not.** Not lives saved by any programme (no intervention is observed, the
crash-occurrence pathway is excluded, and no unmeasured confounding is assumed); not additive
across factors; not shares of individual deaths.

## 5. Rankings: which are stable and which are not

*Sources: `contributions/ranking`, `contributions/rank_probabilities`. Crash-level factors only;
restraint is occupant-level and police-recorded drugs are not rankable.*

| Factor | Share of crashes | Share of fatal crashes | Crude RR | Adjusted RR | Adjusted RD per 1,000 | Shapley test R² | Shapley AF | FARS deaths 2016–2024 | Note |
|---|---|---|---|---|---|---|---|---|---|
| exceeded | 0.85% | 7.3% | 10.03 | 5.20 | 21.4 | 0.016 | 4.9% | 40,036 | predictive value is that of the whole speeding-type block |
| speeding_other | 9.23% | 13.1% | 1.66 | 1.31 | 1.6 | — | 2.7% | 58,657 | shares the speeding-type predictive block with 'exceeded' |
| alcohol | 5.18% | 25.9% | 6.41 | 4.11 | 14.5 | 0.020 | 18.1% | 105,821 | — |
| drugs_police | 1.01% | 7.7% | 11.73 | 4.05 | 12.0 | 0.012 | — | 84,207 | NOT RANKED: severity association not identified (drugs/crss_bounds); FARS count is a lower bound (63% of deaths in crashes with undetermined drug status) |
| unbelted (occupant) | — | — | 46.33 | 28.05 | 25.8 | — | — | 96,706 | occupant-level quantity; not comparable with crash-level factors |

Probability of each rank (joint sampling distribution of the adjusted estimates from one model):

| Metric | Factor | Estimate | P(rank 1) | P(rank 2) | P(rank 3) |
|---|---|---|---|---|---|
| adjusted RR | exceeded | 5.197 | 0.97 | 0.03 | 0.00 |
| adjusted RR | speeding_other | 1.313 | 0.00 | 0.00 | 1.00 |
| adjusted RR | alcohol | 4.112 | 0.03 | 0.97 | 0.00 |
| adjusted RD | exceeded | 0.02142 | 0.99 | 0.01 | 0.00 |
| adjusted RD | speeding_other | 0.001598 | 0.00 | 0.00 | 1.00 |
| adjusted RD | alcohol | 0.01448 | 0.01 | 0.99 | 0.00 |

* **Stable:** on adjusted risk ratio and risk difference, exceeding the limit ranks first with
  probability ≥ 0.97,
  alcohol second, other speeding types last.
* **Reversed by the metric:** alcohol ranks first on prevalence in fatal crashes, Shapley share
  of attributed burden and deaths involved, because it is about six times as common as
  exceedance among crashes. On predictive information the order depends on the measure: alcohol
  is ahead alone and by Shapley value, speeding type when each is removed from the full model
  last, and they tie on permutation importance (intervals overlap).
* **Not rankable:** police-recorded drug involvement (unidentified association; its adjusted RR
  of 4.0 reflects selective recording
  as much as risk), and restraint, which is an occupant-level quantity: its adjusted risk ratio
  (28 across crashes after
  environment, person and the driver's own behaviour;
  19 after crash
  configuration as well; about 3 within vehicles) answers a different question (whether a person survives a crash) from the
  crash-level factors (whether a crash is fatal).

**The hypothesised ranking drugs > alcohol > seatbelt non-use > speeding is not defensible.**
Drugs cannot be placed; seat-belt non-use is not on the same scale; and whether alcohol or
speeding comes first depends on whether one asks about the risk per crash (exceeding the limit)
or the number of deaths involved and statistically attributed (alcohol). Generic "speeding"
(Phase-1 adjusted RR 1.82)
looks much weaker than alcohol only because it pools exceeding the limit with "too fast for
conditions".

## 6. Implications for interpreting official statistics and for policy (answer to H)

*The evidence ledger (`policy/evidence_ledger`, column `phase2_evidence`, and the new
"combined speed and alcohol enforcement" row) records these points with their sources. Nothing
here is an estimated effect of an intervention: the archives contain no enforcement, testing or
campaign data.*

* **Reading official counts.** "Speeding-related", "alcohol-impaired", "drug-involved" and
  "unrestrained" deaths are counts of deaths *involving* a recorded circumstance. They overlap
  (§4a), they are recorded with severity-dependent completeness, and the drug count depends on
  who is tested. They should not be added, ranked against each other, or read as deaths
  *caused* by each factor.
* **Speed enforcement.** The target with a robust association is exceeding the limit
  (adjusted RR 5.2 (4.3–6.2);
  6.5 (5.5–7.8) in crashes with
  no alcohol). Alcohol does not explain it away, so a large overlap with alcohol does not make
  speed enforcement redundant. "Too fast for conditions" — most recorded speeding — is weakly
  associated and is not a camera target.
* **Alcohol enforcement.** Alcohol carries the largest share of statistically attributed burden
  (71%
  of the joint speeding-and-alcohol fraction) and its association is not explained by speeding.
  Much of it runs through the type of crash (single-vehicle departures), which is consistent
  with acting before the crash.
* **Drug testing.** The data cannot say how much drug-involved driving contributes to deaths.
  What they do show is that drug "involvement" statistics depend on testing practice: killed
  drivers are tested three times as often as survivors, and police co-record drugs with alcohol.
  Better measurement (routine toxicology in crashes of all severities) is a precondition for
  any evidence-based drug-testing target.
* **Seat-belt enforcement.** Belt protection given a fatal crash is about two-thirds, does not
  depend on whether the driver was speeding and is only slightly larger with a drinking driver (`reports/alcohol_drugs_restraints.md`
  §6). Belts and impaired-driving or speed measures therefore act on different stages; an
  unbelted occupant of a drunk or speeding driver carries a much larger *excess* risk than either
  factor alone implies (super-additivity, `reports/multifactor_interactions.md` §4), so
  combinations matter for targeting even though the ratio-scale effects are sub-multiplicative.
* **Combined strategies.** The overlap of speeding and alcohol means that the deaths "in scope"
  of two programmes are not additive: the joint attributable fraction
  (25.7%)
  is smaller than the sum of the singles. Whether two programmes have diminishing or increasing
  returns depends on whether they change the same drivers' behaviour, which the data cannot show.
  The super-additive combinations (exceedance × alcohol, behaviour × belt non-use) indicate
  where a given reduction in one factor would remove the most excess risk, *if* the reduction
  occurred in those combinations.
* **Targeted campaigns.** Night-time and single-vehicle crashes concentrate exceedance and
  alcohol (`speeding/type_composition`), and unbelted deaths overlap with both more than
  independence would imply (`contributions/fars_pairwise_overlap`); the data identify these as
  high-risk *combinations* but not the effect of any campaign aimed at them.

## 7. What would make these quantities causal

None of the quantities above is a causal effect. Turning the adjusted associations into causal
effects would require exposure data (to address crash occurrence), measured travel speed,
toxicology for all drivers in crashes of all severities, and a design that varies a factor
independently of the others (e.g. enforcement changes over time and place, with comparison
areas). Turning burden into "preventable deaths" would additionally require the effect of an
intervention on the factor, which the archives do not contain.
