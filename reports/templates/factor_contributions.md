# Factor contributions: association, adjustment, prediction, attribution and counts

*Phase 2 report (research questions A, F and H; `docs/research_plan_phase2.md` §5.4). Every
number is read from `outputs/tables/contributions/` (and the tables named in each section) when
this report is rendered. Estimate types are labelled: **observed** (FARS census), **estimated**
(CRSS design-based), **adjusted association** (model-based, not causal), **model-predicted**,
and **predictive** (out-of-sample prediction).*

## Summary

1. **Official counts overlap so heavily that they cannot be added.** Of
   {{contributions/fars_overlap_summary|factor=all deaths|deaths|,.0f}} US road deaths in
   2016–2024 (FARS, observed), {{contributions/fars_overlap_summary|factor=speeding-related crash|deaths|,.0f}}
   occurred in speeding-related crashes, {{contributions/fars_overlap_summary|factor=driver BAC >= .08 (MI)|deaths|,.0f}}
   in crashes with a driver at BAC ≥ .08, at least {{contributions/fars_overlap_summary|factor=driver drug-positive (determinate crashes only)|deaths|,.0f}}
   in crashes with a drug-positive driver, and {{contributions/fars_overlap_summary|factor=victim an unbelted vehicle occupant|deaths|,.0f}}
   were unbelted occupants. These four counts sum to
   {{contributions/fars_overlap_summary|factor=sum of the four factor counts|share_of_all_deaths|pct:0}}
   of all deaths, but only {{contributions/fars_overlap_summary|factor=deaths involving at least one factor (union)|share_of_all_deaths|pct:0}}
   of deaths involve any of them: each death in this group is counted
   {{contributions/fars_overlap_summary|factor=all deaths|overcount_ratio_sum_over_union|.2f}}
   times on average. About {{contributions/fars_overlap_summary|factor=speeding-related crash|share_also_involving_another_factor|pct:0}}
   of speeding-related deaths also involve one of the other three factors.
2. **Statistical attribution is also non-additive.** In the severity-pathway model, removing
   speeding accounts for {{contributions/burden_shapley|player_set=speeding_alcohol;quantity=AF[speeding]|estimate|cipct:1}}
   of fatal crashes and removing alcohol for
   {{contributions/burden_shapley|player_set=speeding_alcohol;quantity=AF[alcohol]|estimate|cipct:1}},
   but removing both accounts for {{contributions/burden_shapley|player_set=speeding_alcohol;quantity=AF[speeding+alcohol]|estimate|cipct:1}},
   not the sum. A Shapley allocation of the joint fraction credits
   {{contributions/burden_shapley|player_set=speeding_alcohol;quantity=Shapley share[alcohol]|estimate|pct:0}}
   to alcohol and {{contributions/burden_shapley|player_set=speeding_alcohol;quantity=Shapley share[speeding]|estimate|pct:0}}
   to speeding — a convention for dividing a model quantity, not a causal split.
3. **Each meaning of "contribution" ranks the factors differently** (§5). Exceeding the limit
   has the largest adjusted risk ratio and risk difference; alcohol the largest attributed burden
   and the most deaths, and the largest predictive information alone and by Shapley value (but
   not when removed last, where speeding type loses more); "too fast for conditions"
   is common but weakly associated. Police-recorded drug involvement cannot be ranked.
4. **Most predictive information is in crash configuration and environment, not behaviour.**
   On held-out years, crash configuration carries
   {{contributions/predictive|block=configuration|shapley_share|pct:0}} of the explained
   log-likelihood, the road/time environment {{contributions/predictive|block=environment|shapley_share|pct:0}},
   alcohol {{contributions/predictive|block=alcohol|shapley_share|pct:0}} and speeding type
   {{contributions/predictive|block=speeding_type|shapley_share|pct:0}}. Behaviours are rare;
   prediction rewards common, informative variables.

## Answers to the Phase-2 questions at a glance

| | Question | Answer (details in) |
|---|---|---|
| A | How much of the speeding–fatality association is explained statistically by alcohol and other recorded factors? | For exceeding the limit, alcohol accounts for {{speeding/shapley|exposure=exceeded;outcome=fatal;variant=all_blocks;block=alcohol|shapley_share_of_crude|pct:0}} of the crude log-RR on average over orderings ({{speeding/shapley|exposure=exceeded;outcome=fatal;variant=all_blocks;block=alcohol|min_share_any_order|pct:0}}–{{speeding/shapley|exposure=exceeded;outcome=fatal;variant=all_blocks;block=alcohol|max_share_any_order|pct:0}}); all recorded circumstances together leave {{speeding/shapley|exposure=exceeded;outcome=fatal;variant=all_blocks;block=retained_after_all_blocks|shapley_share_of_crude|pct:0}} (`reports/speeding_confounding.md`) |
| B | Does exceeding the limit remain independently associated with fatal severity? | Yes: adjusted RR {{speeding/key_models|exposure=exceeded;outcome=fatal;model=all_blocks|rr|ci:1}}; {{speeding/strata|exposure=exceeded;outcome=fatal;stratum=no alcohol|rr|ci:1}} without alcohol; robust to moderate recording bias (same report) |
| C | Can alcohol and drugs be separated reliably? | Only in a narrow, selected population (tested drivers in fatal crashes, four high-testing states); not in general (`reports/alcohol_drugs_restraints.md`) |
| D | How much does restraint use change fatality associations within comparable occupants? | Within the same vehicle, belted occupants' risk is {{restraint_behaviour/dpc_by_driver_behaviour|split=all|rr_belted_vs_unbelted|ci:2@rr}} times unbelted occupants', unchanged by the driver's speeding or alcohol (same report) |
| E | Which combinations show interaction? | Super-additive: exceedance × alcohol, behaviour × belt non-use; sub-multiplicative at crash level, multiplicative for single-vehicle drivers; three-way terms not detected; four-way with drugs not estimable (`reports/multifactor_interactions.md`) |
| F | How much do contributions depend on units, definitions, specifications and missingness? | Strongly: crash vs driver vs passenger vs pedestrian (alcohol RR from {{multifactor/victims|victim=pedestrian killed (striking driver's behaviour)|rr_alcohol_only|.1f}} to {{multifactor/victims|victim=crash fatal (any driver's behaviour)|rr_alcohol_only|.1f}}); "any speeding" vs exceedance; with or without configuration; police drugs as a covariate; drug unknowns (§2–§5 below) |
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
{{stages/death_timing|group=all deaths|share_died_at_scene|pct:0}} of the
{{stages/death_timing|group=all deaths|deaths|,.0f}} deaths in 2016–2024 occurred at the scene
and {{stages/death_timing|group=all deaths|share_within_1_hour|pct:0}} within an hour of the crash
(at the scene included) — {{stages/death_timing|group=vehicle occupant, unbelted|share_died_at_scene|pct:0}}
at the scene for unbelted and {{stages/death_timing|group=vehicle occupant, belted|share_died_at_scene|pct:0}}
for belted occupants, {{stages/death_timing|group=rural road|share_died_at_scene|pct:0}} on rural
and {{stages/death_timing|group=urban road|share_died_at_scene|pct:0}} on urban roads. Most of the
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
{{contributions/nested_models|factor=alcohol;step=crude|n|,.0f}}; standardised risk ratios
(RR), risk differences per 1,000 crashes (RD) and conditional odds ratios (OR) from the same
survey logistic models; every step uses the same crashes.*

**Exceeded the limit / racing (vs no speeding):**
{{mdtable:contributions/nested_models|factor=exceeded|step:Model:;rr:Standardised RR:ci:2;rd:RD per 1,000:cix1000:1;odds_ratio:Conditional OR:ci:2;share_logrr_retained:Share of crude log-RR retained:.2f}}

**Alcohol involved (imputed):**
{{mdtable:contributions/nested_models|factor=alcohol|step:Model:;rr:Standardised RR:ci:2;rd:RD per 1,000:cix1000:1;odds_ratio:Conditional OR:ci:2;share_logrr_retained:Share of crude log-RR retained:.2f}}

**Other speeding types (too fast for conditions, unspecified):**
{{mdtable:contributions/nested_models|factor=speeding_other|step:Model:;rr:Standardised RR:ci:2;rd:RD per 1,000:cix1000:1;odds_ratio:Conditional OR:ci:2}}

**Police-reported drug involvement (not interpretable as a drug association; shown for transparency):**
{{mdtable:contributions/nested_models|factor=drugs_police|step:Model:;rr:Standardised RR:ci:2;odds_ratio:Conditional OR:ci:2}}

*What the sequence shows.*

* **Adjusting each behaviour for the other** reduces exceedance from
  {{contributions/nested_models|factor=exceeded;step=environment|rr|.1f}} to
  {{contributions/nested_models|factor=exceeded;step=+ other speeding/alcohol|rr|.1f}} and
  alcohol from {{contributions/nested_models|factor=alcohol;step=environment|rr|.1f}} to
  {{contributions/nested_models|factor=alcohol;step=+ other speeding/alcohol|rr|.1f}}. Both
  remain large. `reports/speeding_confounding.md` decomposes this in every order.
* **Adding police-recorded drugs** reduces alcohol further, from
  {{contributions/nested_models|factor=alcohol;step=+ driver/vehicle mix|rr|.2f}} to
  {{contributions/nested_models|factor=alcohol;step=+ police-reported drugs|rr|.2f}}, but this
  is not evidence that drugs explain the alcohol association: police record drugs mainly when
  they are already investigating alcohol (`drugs/co_occurrence`), so the drug field partly
  re-measures alcohol involvement. This step is reported separately and is not used for
  ranking.
* **Adding crash configuration** (a likely mediator) reduces alcohol to
  {{contributions/nested_models|factor=alcohol;step=+ crash configuration|rr|.2f}} but leaves
  exceedance almost unchanged ({{contributions/nested_models|factor=exceeded;step=+ crash configuration|rr|.2f}}):
  much of alcohol's association runs through the *type* of crash (single-vehicle departures,
  head-on), whereas exceedance is associated with higher severity within crash types.
* **Odds ratios drift away from risk ratios** as covariates are added (exceedance: OR
  {{contributions/nested_models|factor=exceeded;step=+ crash configuration|odds_ratio|.2f}} vs
  RR {{contributions/nested_models|factor=exceeded;step=+ crash configuration|rr|.2f}} in the
  last model), although the sample is fixed. This is non-collapsibility: conditional odds
  ratios change when outcome-predictive covariates are added even without confounding, so
  comparing ORs across models overstates or understates "how much was explained". All Phase-2
  comparisons use standardised RRs and RDs.

## 3. Predictive contribution (predictive)

*Source: `contributions/predictive`, `contributions/predictive_lattice`. Models fitted on
2016–2021 and evaluated on 2023–2024 (2022 unused); design-weighted McFadden R² on the test
years (log-likelihood gain over the training base rate) and AUROC; intervals from resampling
test-set PSUs within strata (model fixed).*

{{mdtable:contributions/predictive||block:Block:;r2_alone:Test R² alone:ci:3@r2_alone;r2_drop_when_removed:R² lost when removed from the full model:ci:3@r2_drop_when_removed;shapley_r2:Shapley R²:ci:3@shapley_r2;shapley_share:Shapley share:pct:0;auc_alone:AUROC alone:.3f;logloss_increase:Permutation log-loss increase:.4f}}

The full model reaches a test R² of {{contributions/predictive|block=alcohol|full_r2|.3f}} and
AUROC {{contributions/predictive|block=alcohol|full_auc|.3f}}. *Interpretation.* Alcohol's
predictive value alone ({{contributions/predictive|block=alcohol|r2_alone|.3f}}) is more than
four times its value once everything else is in the model
({{contributions/predictive|block=alcohol|r2_drop_when_removed|.3f}}), because much of what alcohol
tells a model about severity is also told by the time, road and crash type. Shapley values split
that shared information evenly; drop-when-removed gives it to nobody. Neither is causal
importance. Police-recorded drug status has predictive value
({{contributions/predictive|block=drugs_police|shapley_r2|.3f}}) partly because its *recording*
depends on severity — a reason it predicts, and a reason it cannot be interpreted.

## 4. Burden: deaths involving a factor vs deaths statistically attributed to it

*Sources: `contributions/fars_overlap_summary`, `contributions/fars_pairwise_overlap`
(observed), `contributions/burden_shapley` (model-predicted, severity pathway only).*

**(a) Deaths involving a factor (FARS 2016–2024, observed; alcohol as expected counts over the
ten BAC implicates; drug positivity only where every driver's status is determinate).**

{{mdtable:contributions/fars_overlap_summary||factor:Deaths counted under:;deaths:Deaths:,.0f;share_of_all_deaths:Share of all deaths:pct:1;share_also_involving_another_factor:Also involve another listed factor:pct:0}}

Pairwise, {{contributions/fars_pairwise_overlap|pair=speeding & alcohol|share_of_a_also_b|pct:0}}
of speeding-related deaths also involved a driver at BAC ≥ .08, and
{{contributions/fars_pairwise_overlap|pair=speeding & alcohol|share_of_b_also_a|pct:0}} of
alcohol-related deaths were in speeding-related crashes
({{contributions/fars_pairwise_overlap|pair=speeding & alcohol|observed_over_expected|.2f}}
times the overlap expected if the two were independent among deaths). The drug count is a
lower bound: {{contributions/fars_overlap_summary|factor=all deaths|deaths_undetermined_drug_status|,.0f}}
deaths occurred in crashes where some driver's drug status is undetermined.

**(b) Deaths statistically attributed (severity pathway, model-predicted).** Fractions of
fatal crashes that the model predicts would not have been fatal had the factor been absent,
other recorded circumstances fixed, the crash still happening; FARS-scaled to the 2022–2024
average.

{{mdtable:contributions/burden_shapley|player_set=exceeded_other_alcohol|quantity:Quantity:;estimate:Estimate:cipct:1@estimate;fars_deaths_per_year:FARS-scaled deaths per year:,.0f}}

* Joint removal of speeding (all types) and alcohol: {{contributions/burden_shapley|player_set=speeding_alcohol;quantity=AF[speeding+alcohol]|estimate|cipct:1@estimate}};
  the sum of the two single fractions double-counts
  {{contributions/burden_shapley|player_set=speeding_alcohol;quantity=overlap = sum of singles - joint|estimate|cipct:1@estimate}}
  of fatal crashes.
* The overlap in attributed burden is much smaller than the overlap in *counts* (a), because
  the model attributes to each factor only the excess risk it adds, not every death in which
  it is present.
* Consistency with Phase 1: the Phase-1 fractions (`burden/attributable_fractions_fatal`:
  speeding {{burden/attributable_fractions_fatal|shift=speeding_removed|af|pct:1}}, alcohol
  {{burden/attributable_fractions_fatal|shift=alcohol_removed|af|pct:1}}, joint
  {{burden/attributable_fractions_fatal|shift=speeding_and_alcohol_removed|af|pct:1}}) used a
  model with any-speeding instead of speeding type; the Phase-2 values above agree within their
  intervals.

**What these are not.** Not lives saved by any programme (no intervention is observed, the
crash-occurrence pathway is excluded, and no unmeasured confounding is assumed); not additive
across factors; not shares of individual deaths.

## 5. Rankings: which are stable and which are not

*Sources: `contributions/ranking`, `contributions/rank_probabilities`. Crash-level factors only;
restraint is occupant-level and police-recorded drugs are not rankable.*

{{mdtable:contributions/ranking||factor:Factor:;prevalence_all_crashes:Share of crashes:pct:2;prevalence_fatal_crashes:Share of fatal crashes:pct:1;crude_rr:Crude RR:.2f;adjusted_rr:Adjusted RR:.2f;adjusted_rd:Adjusted RD per 1,000:x1000:1;shapley_test_r2_of_block:Shapley test R²:.3f;shapley_share_joint_af:Shapley AF:pct:1;fars_deaths_in_crashes_with_factor:FARS deaths 2016–2024:,.0f;note:Note:}}

Probability of each rank (joint sampling distribution of the adjusted estimates from one model):

{{mdtable:contributions/rank_probabilities||metric:Metric:;factor:Factor:;estimate:Estimate:.4g;p_rank_1:P(rank 1):.2f;p_rank_2:P(rank 2):.2f;p_rank_3:P(rank 3):.2f}}

* **Stable:** on adjusted risk ratio and risk difference, exceeding the limit ranks first with
  probability ≥ {{contributions/rank_probabilities|metric=adjusted RR;factor=exceeded|p_rank_1|.2f}},
  alcohol second, other speeding types last.
* **Reversed by the metric:** alcohol ranks first on prevalence in fatal crashes, Shapley share
  of attributed burden and deaths involved, because it is about six times as common as
  exceedance among crashes. On predictive information the order depends on the measure: alcohol
  is ahead alone and by Shapley value, speeding type when each is removed from the full model
  last, and they tie on permutation importance (intervals overlap).
* **Not rankable:** police-recorded drug involvement (unidentified association; its adjusted RR
  of {{contributions/ranking|factor=drugs_police|adjusted_rr|.1f}} reflects selective recording
  as much as risk), and restraint, which is an occupant-level quantity: its adjusted risk ratio
  ({{contributions/ranking|factor=unbelted (occupant)|adjusted_rr|.0f}} across crashes after
  environment, person and the driver's own behaviour;
  {{restraint_behaviour/crss_unbelted_nested|step=+ crash configuration|rr|.0f}} after crash
  configuration as well; about 3 within vehicles) answers a different question (whether a person survives a crash) from the
  crash-level factors (whether a crash is fatal).

**The hypothesised ranking drugs > alcohol > seatbelt non-use > speeding is not defensible.**
Drugs cannot be placed; seat-belt non-use is not on the same scale; and whether alcohol or
speeding comes first depends on whether one asks about the risk per crash (exceeding the limit)
or the number of deaths involved and statistically attributed (alcohol). Generic "speeding"
(Phase-1 adjusted RR {{severity/fatal_crude_vs_adjusted|factor=speeding;level=yes|A_adj_rr|.2f}})
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
  (adjusted RR {{contributions/nested_models|factor=exceeded;step=+ driver/vehicle mix|rr|ci:1}};
  {{speeding/strata|exposure=exceeded;outcome=fatal;stratum=no alcohol|rr|ci:1}} in crashes with
  no alcohol). Alcohol does not explain it away, so a large overlap with alcohol does not make
  speed enforcement redundant. "Too fast for conditions" — most recorded speeding — is weakly
  associated and is not a camera target.
* **Alcohol enforcement.** Alcohol carries the largest share of statistically attributed burden
  ({{contributions/burden_shapley|player_set=speeding_alcohol;quantity=Shapley share[alcohol]|estimate|pct:0}}
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
  ({{contributions/burden_shapley|player_set=speeding_alcohol;quantity=AF[speeding+alcohol]|estimate|pct:1}})
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
