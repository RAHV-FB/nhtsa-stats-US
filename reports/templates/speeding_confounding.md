# Speeding and alcohol: how much of the speeding–fatality association survives?

*Phase 2 report (research questions A, B and F; `docs/research_plan_phase2.md` §5.1). CRSS
police-reported crashes 2016–2024 with known severity (crash level), survey-weighted; FARS for
recording checks. Every number is read from `outputs/tables/speeding/` when this report is
rendered. All risk ratios are **adjusted associations** — standardised over all police-reported
crashes, conditional on a crash having happened — not causal effects.*

## Summary

**A. How much of the speeding association is explained statistically by alcohol?** For
exceeding the limit (vs no speeding), the crude fatal risk ratio is
{{speeding/key_models|exposure=exceeded;outcome=fatal;model=crude|rr|ci:1}}. Adjusting for
alcohol alone takes it to {{speeding/key_models|exposure=exceeded;outcome=fatal;model=other_behaviour_only|rr|ci:1}};
for the road, time, light and driver/vehicle environment alone to
{{speeding/key_models|exposure=exceeded;outcome=fatal;model=environment_only|rr|ci:1}}; for
both to {{speeding/key_models|exposure=exceeded;outcome=fatal;model=environment_and_other_behaviour|rr|ci:1}}.
Averaged over every order in which the seven covariate blocks can be added, alcohol accounts
for {{speeding/shapley|exposure=exceeded;outcome=fatal;variant=all_blocks;block=alcohol|shapley_share_of_crude|cipct:0@share}}
of the crude log risk ratio — between
{{speeding/shapley|exposure=exceeded;outcome=fatal;variant=all_blocks;block=alcohol|min_share_any_order|pct:0}} and
{{speeding/shapley|exposure=exceeded;outcome=fatal;variant=all_blocks;block=alcohol|max_share_any_order|pct:0}}
depending on what is already in the model. For speeding of any type the alcohol share is
{{speeding/shapley|exposure=speeding_any;outcome=fatal;variant=all_blocks;block=alcohol|shapley_share_of_crude|cipct:0@share}}.
So alcohol accounts for a real but minority part of the speeding association; the road and
crash environment accounts for more.

**B. Does exceeding the limit remain independently associated with fatal severity?** Yes. With
all seven blocks, including crash configuration, the risk ratio is
{{speeding/key_models|exposure=exceeded;outcome=fatal;model=all_blocks|rr|ci:1}}, retaining
{{speeding/key_models|exposure=exceeded;outcome=fatal;model=all_blocks|share_logrr_retained|pct:0}}
of the crude log risk ratio. Among crashes with **no alcohol involvement** it is
{{speeding/strata|exposure=exceeded;outcome=fatal;stratum=no alcohol|rr|ci:1}} (police-reported
no alcohol: {{speeding/strata|exposure=exceeded;outcome=fatal;stratum=police: no alcohol|rr|ci:1}}).
It is present by day and by night, in single- and multi-vehicle crashes, on low- and
high-speed roads, before and after 2020, and with hit-and-run crashes excluded. It would
require an unmeasured confounder associated with both exceedance and death by a risk ratio of
{{speeding/e_values|exposure=exceeded;outcome=fatal;specification=model: all_blocks|e_value_ci|.1f}}
each (E-value for the confidence limit) to explain it away.

**The reverse hypothesis fails too.** Alcohol's association is not explained by speeding:
adjusting for speeding type changes alcohol's risk ratio only from
{{speeding/key_models|exposure=alcohol;outcome=fatal;model=crude|rr|.2f}} to
{{speeding/key_models|exposure=alcohol;outcome=fatal;model=other_behaviour_only|rr|.2f}}
(Shapley share of speeding type
{{speeding/shapley|exposure=alcohol;outcome=fatal;variant=all_blocks;block=speeding_type|shapley_share_of_crude|pct:0}}).
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
| All crashes | {{speeding/type_composition|domain=all crashes;level=all|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=all crashes;level=all|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=all crashes;level=all|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=all crashes;level=all|exceeded_share_of_speeding|pct:0}} |
| Alcohol (imputed): no | {{speeding/type_composition|domain=alcohol (imputed);level=no|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=alcohol (imputed);level=no|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=alcohol (imputed);level=no|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=alcohol (imputed);level=no|exceeded_share_of_speeding|pct:0}} |
| Alcohol (imputed): yes | {{speeding/type_composition|domain=alcohol (imputed);level=yes|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=alcohol (imputed);level=yes|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=alcohol (imputed);level=yes|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=alcohol (imputed);level=yes|exceeded_share_of_speeding|pct:0}} |
| Drugs (police): yes | {{speeding/type_composition|domain=drugs (police);level=yes|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=drugs (police);level=yes|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=drugs (police);level=yes|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=drugs (police);level=yes|exceeded_share_of_speeding|pct:0}} |
| Night (21–05) | {{speeding/type_composition|domain=time;level=night|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=time;level=night|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=time;level=night|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=time;level=night|exceeded_share_of_speeding|pct:0}} |
| Single-vehicle crash | {{speeding/type_composition|domain=crash type;level=single vehicle|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=crash type;level=single vehicle|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=crash type;level=single vehicle|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=crash type;level=single vehicle|exceeded_share_of_speeding|pct:0}} |
| Snow / ice surface | {{speeding/type_composition|domain=surface;level=snow_ice|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=surface;level=snow_ice|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=surface;level=snow_ice|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=surface;level=snow_ice|exceeded_share_of_speeding|pct:0}} |
| Limit 60+ mph | {{speeding/type_composition|domain=speed limit;level=60+|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=speed limit;level=60+|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=speed limit;level=60+|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=speed limit;level=60+|exceeded_share_of_speeding|pct:0}} |
| Severity O/C/B | {{speeding/type_composition|domain=severity;level=O/C/B (no or minor injury)|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=severity;level=O/C/B (no or minor injury)|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=severity;level=O/C/B (no or minor injury)|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=severity;level=O/C/B (no or minor injury)|exceeded_share_of_speeding|pct:0}} |
| Severity K (fatal) | {{speeding/type_composition|domain=severity;level=K (fatal)|share_any_speeding|pct:1}} | {{speeding/type_composition|domain=severity;level=K (fatal)|share_exceeded_limit_or_racing|pct:2}} | {{speeding/type_composition|domain=severity;level=K (fatal)|share_too_fast_for_conditions|pct:1}} | {{speeding/type_composition|domain=severity;level=K (fatal)|exceeded_share_of_speeding|pct:0}} |

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

{{mdtable:speeding/key_models|exposure=exceeded;outcome=fatal|model:Model:;rr:Standardised RR:ci:2;rd:RD per 1,000:cix1000:1;share_logrr_retained:Share of crude log-RR retained:.2f;odds_ratio:Conditional OR:ci:2}}

**Shapley shares of the crude log-RR (exceeded the limit, fatal), all seven blocks:**

{{mdtable:speeding/shapley|exposure=exceeded;outcome=fatal;variant=all_blocks|block:Block:;shapley_share_of_crude:Share of crude log-RR:cipct:0@share;min_share_any_order:Smallest share (any order):pct:0;max_share_any_order:Largest share (any order):pct:0}}

**The same without crash configuration (treating it as a mediator to be left out):**

{{mdtable:speeding/shapley|exposure=exceeded;outcome=fatal;variant=excluding_configuration|block:Block:;shapley_share_of_crude:Share of crude log-RR:cipct:0@share}}

*How much alcohol accounts for depends on what is already in the model.* Added to the crude
model, alcohol removes
{{speeding/behaviour_change|exposure=exceeded;outcome=fatal;blocks_already_in=crude|share_of_crude|cipct:0}}
of the crude log-RR; added after all five environment blocks and configuration, it removes
{{speeding/behaviour_change|exposure=exceeded;outcome=fatal;blocks_already_in=calendar_area+configuration+driver_vehicle_mix+light+road_environment+time|share_of_crude|cipct:0}}.
The difference arises because alcohol, night, darkness, single-vehicle crashes and young drivers
travel together: once those are held fixed, little of the alcohol–exceedance overlap remains to
remove. Neither number is "the" alcohol share; the Shapley value averages over all orders.

**Any speeding (fatal):**

{{mdtable:speeding/key_models|exposure=speeding_any;outcome=fatal|model:Model:;rr:Standardised RR:ci:2;share_logrr_retained:Share retained:.2f}}

{{mdtable:speeding/shapley|exposure=speeding_any;outcome=fatal;variant=all_blocks|block:Block:;shapley_share_of_crude:Share of crude log-RR:cipct:0@share}}

**Fatal-or-serious (KA) outcome, exceeded the limit:** crude
{{speeding/key_models|exposure=exceeded;outcome=ka;model=crude|rr|ci:2}}, all blocks
{{speeding/key_models|exposure=exceeded;outcome=ka;model=all_blocks|rr|ci:2}}; alcohol's Shapley
share {{speeding/shapley|exposure=exceeded;outcome=ka;variant=all_blocks;block=alcohol|shapley_share_of_crude|cipct:0@share}}.

**Alcohol as the exposure (fatal), speeding type as a block:**

{{mdtable:speeding/shapley|exposure=alcohol;outcome=fatal;variant=all_blocks|block:Block:;shapley_share_of_crude:Share of crude log-RR:cipct:0@share;min_share_any_order:Smallest:pct:0;max_share_any_order:Largest:pct:0}}

*Reading the decompositions.* For both behaviours the largest single block is the road and
crash environment or crash configuration, not the other behaviour. Exceedance retains more of
its crude association than alcohol does: alcohol's association runs to a large extent through
*which kind of crash* happens (configuration's share), consistent with impairment acting at
Stage A (crash occurrence: departures, head-on) and speed at Stage B (energy within a crash
type).

## 4. Stratified associations (Q2)

*Source: `speeding/strata`. Model-A blocks minus those defining the stratum; ratio of the two
strata RRs with a design-based CI and p-value.*

{{mdtable:speeding/strata|exposure=exceeded;outcome=fatal|split:Split:;stratum:Stratum:;n_exposed:Exposed crashes:,.0f;n_exposed_events:Exposed fatal:,.0f;rr:Adjusted RR:ci:2;heterogeneity_ratio:Ratio (2nd / 1st stratum):ci:2@heterogeneity_ratio;heterogeneity_p:p:.2g}}

* **Without alcohol the association is stronger, not weaker** — the relative excess of
  exceedance is larger where the baseline risk is lower. This contradicts the hypothesis that
  exceedance looks dangerous mainly because of alcohol.
* The association is weaker at night, in single-vehicle crashes and on 50+ mph roads, where the
  baseline risk is already high; on the additive scale the picture reverses (see
  `reports/multifactor_interactions.md`).
* Any speeding (pooled types), for comparison:

{{mdtable:speeding/strata|exposure=speeding_any;outcome=fatal|split:Split:;stratum:Stratum:;rr:Adjusted RR:ci:2;heterogeneity_p:p:.2g}}

## 5. Could differential recording explain the association?

*Sources: `speeding/fars_crss_recording`, `speeding/stratified_qba`, `speeding/e_values`.*

**Recording completeness by alcohol (observed vs estimated).** Among fatal crashes, police in
CRSS jurisdictions record speeding less often than FARS analysts, who use more sources:

{{mdtable:speeding/fars_crss_recording||stratum:Alcohol stratum:;measure:Measure:;fars_share:FARS share:pct:1;crss_share:CRSS share:cipct:1@crss_share;crss_over_fars:CRSS / FARS:ci:2@crss_over_fars}}

Recording is *less* complete in alcohol-involved fatal crashes than in others. If police
under-record speeding more in alcohol crashes, the alcohol-stratified analyses understate the
overlap, and speeding's association within the alcohol stratum is, if anything, understated. The
competing story — police record speeding more readily when alcohol is involved, inflating the
apparent overlap — is not supported for fatal crashes.

**Outcome-dependent recording.** If exceedance in non-fatal crashes is recorded less completely
than in fatal ones, the crude RR is inflated. Within the no-alcohol stratum the observed crude
RR of {{speeding/stratified_qba|alcohol_stratum=no;se_fatal=0.9;se_nonfatal=1.0|rr_observed|.1f}}
becomes {{speeding/stratified_qba|alcohol_stratum=no;se_fatal=0.9;se_nonfatal=0.5|rr_corrected|.1f}}
if non-fatal exceedance were recorded only half as completely (fatal sensitivity 0.9), and
{{speeding/stratified_qba|alcohol_stratum=no;se_fatal=0.9;se_nonfatal=0.2|rr_corrected|.1f}} at
a fifth. In the alcohol stratum the same scenarios give
{{speeding/stratified_qba|alcohol_stratum=yes;se_fatal=0.9;se_nonfatal=0.5|rr_corrected|.1f}}
and {{speeding/stratified_qba|alcohol_stratum=yes;se_fatal=0.9;se_nonfatal=0.2|rr_corrected|.2f}}.
The association survives moderate differential recording; only severe under-recording in
non-fatal crashes would remove it, and the alcohol-stratum association is the more fragile.

## 6. Selection by fatality: why co-occurrence among deaths misleads

*Source: `speeding/selection_by_fatality`.*

{{mdtable:speeding/selection_by_fatality||measure:Speeding measure:;population:Population:;or:Speeding–alcohol odds ratio:ci:2@or;interval:Interval:}}

Speeding and alcohol are associated in all police-reported crashes. Among fatal crashes alone
the association is weaker, because both raise the chance that a crash is fatal: a fatal crash
without alcohol is more likely to have *another* reason to be fatal, such as speeding
(collider stratification). Statistics computed only from fatal crashes therefore mis-state how
often the two co-occur in the crashes that produced the deaths, and a "speeding and alcohol"
category in FARS cannot be read as the population overlap of the behaviours. The FARS estimate
differs from CRSS-fatal because FARS records both more completely.

## 7. Interpretation

* **What survives.** A large association between exceeding the limit and fatal outcomes,
  present without alcohol, by day and night, in all crash types and road classes, robust to
  moderate recording bias. A large association for alcohol that is not explained by speeding.
* **What changes.** "Speeding" as a category: its association halves under adjustment and most
  of it belongs to exceedance. The share of the exceedance association that alcohol accounts
  for depends on the model; on average about a fifth of the crude log-RR.
* **What does not follow.** That alcohol "causes" a fifth of speeding deaths, or that speeding
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
