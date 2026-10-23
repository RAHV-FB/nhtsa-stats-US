# Case comparisons: what the records can and cannot say about a particular combination

*Phase 2 report (research question G; `docs/research_plan_phase2.md` §5.5). CRSS 2016–2024
drivers of light passenger vehicles; outcome: the driver dies, given a police-reported crash.
Every number is read from `outputs/tables/cases/` when this report is rendered. Model risks are
**adjusted associations** (standardised over all such drivers), not causal effects. The same
tables drive the "Case comparison" page of the research interface.*

## Summary

* On the grid of cases (speeding type × alcohol × belt × night × single/multi-vehicle, and a
  second grid with police-recorded drugs), many combinations cannot be estimated because too few
  drivers have exactly that combination; the explorer withholds them instead of extrapolating.
* For a supported case, the records give: how many comparable drivers there are, how many died,
  the observed rate, a standardised probability with a confidence interval, and how much lower
  that probability is with each factor absent.
* They do **not** give the share of a particular death "caused" by each factor. Even inside one
  fitted model, the share credited to a factor changes with the scale and the order in which
  factors are considered, can be negative, and requires combinations that may not exist in the
  data.

## 1. The user's example: exceeded limit, alcohol, drugs, no belt, at night

Phase 2 was asked to examine a case like *a driver exceeding the limit, alcohol involved, drug
involvement recorded, no seatbelt, a night-time collision*. Night cannot be combined with drugs
in one grid: to keep enough drivers in each cell, the drug grid (restricted to drivers with a
known police drug code) omits night. The case is therefore examined in two models.

**(a) Without drugs** — exceeded limit + alcohol + unbelted + night + single-vehicle crash:

| Quantity | Value |
|---|---|
| CRSS sample drivers with exactly this combination | {{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|crss_n|,.0f}} |
| …of whom died | {{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|crss_deaths|,.0f}} |
| Observed weighted death rate | {{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|observed_rate|pct:1}} |
| Mean model prediction for these drivers (calibration check) | {{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|predicted_in_cell|pct:1}} |
| Standardised probability (all drivers' road/time/person mix) | {{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|model_risk|cipct:1}} |
| RR vs a belted, sober, non-speeding driver in a daytime multi-vehicle crash | {{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|rr_vs_reference|ci:0}} |
| FARS: light-vehicle drivers killed per year with this combination (observed; alcohol as expected count) | {{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|fars_drivers_killed_per_year|,.0f}} |

With one factor absent and the others kept:

{{mdtable:cases/scenario_contrasts|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|factor:Factor set to reference:;risk_without_factor:Standardised probability without it:pct:1;rr_case_vs_without:RR, case vs without:ci:2@rr_case_vs_without;without_factor_supported:Comparison supported:}}

*Reading.* The comparison that changes the modelled probability most is the belt: the same
case with the driver belted has
{{cases/scenario_contrasts|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes;factor=unbelted|rr_case_vs_without|ci:1@rr_case_vs_without}}
times lower modelled risk. Removing exceedance divides it by
{{cases/scenario_contrasts|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes;factor=speeding|rr_case_vs_without|ci:1@rr_case_vs_without}};
removing alcohol, given the other factors, changes it by
{{cases/scenario_contrasts|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes;factor=alcohol|rr_case_vs_without|ci:2@rr_case_vs_without}}
— not distinguishable from no change *for a driver already unbelted, speeding and alone on the
road at night*, even though alcohol is strongly associated with death on its own. Single-factor
contrasts depend on which other factors are present: this is what non-additivity means for an
individual case. The single-vehicle comparison is unsupported (too few multi-vehicle crashes with
the same other four factors). Because an intermediate combination is unsupported, no allocation
of the risk difference among the factors is shown for this case.

*Calibration and standardisation.* Three numbers describe "the risk" of this case. The observed
rate ({{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|observed_rate|pct:1}},
from {{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|crss_deaths|,.0f}}
deaths, itself imprecise) and the model's mean prediction for the same drivers
({{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|predicted_in_cell|pct:1}})
agree because the model is saturated in the case factors (a first version with only pairwise
products did not, `docs/model_validation.md`). The standardised probability
({{cases/scenarios|model=main (no drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|model_risk|pct:1}})
is somewhat lower because such crashes occur disproportionately in rural areas and involve
younger drivers (both in the model); standardisation answers "what if this combination occurred in the
average crash setting". None of the three is a forensic probability for one driver.

**(b) With police-reported drugs** (drivers with known drug status; night not in this grid) —
exceeded limit + alcohol + drugs + unbelted + single-vehicle crash:

| Quantity | Value |
|---|---|
| CRSS sample drivers / deaths | {{cases/scenarios|model=drug-known subset (police-reported drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, single_vehicle=yes, drugs=yes|crss_n|,.0f}} / {{cases/scenarios|model=drug-known subset (police-reported drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, single_vehicle=yes, drugs=yes|crss_deaths|,.0f}} |
| Standardised probability | {{cases/scenarios|model=drug-known subset (police-reported drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, single_vehicle=yes, drugs=yes|model_risk|cipct:1}} |
| Same case without police-recorded drugs | {{cases/scenario_contrasts|model=drug-known subset (police-reported drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, single_vehicle=yes, drugs=yes;factor=drugs|risk_without_factor|pct:1}} (RR {{cases/scenario_contrasts|model=drug-known subset (police-reported drugs);case=speeding=exceeded_limit, alcohol=yes, unbelted=yes, single_vehicle=yes, drugs=yes;factor=drugs|rr_case_vs_without|ci:2@rr_case_vs_without}}) |

The drug contrast for this case is compatible with no difference, its interval is wide, and the
subset of drivers with recorded drug status is itself selected. Removing alcohol or the belt
from this case leads to combinations with too little support, so those contrasts are withheld.

## 2. A supported case: what allocations look like, and why they are not causes

Alcohol + unbelted + night + single-vehicle crash (no speeding recorded) is supported in every
intermediate combination:

| Quantity | Value |
|---|---|
| CRSS sample drivers / deaths | {{cases/scenarios|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|crss_n|,.0f}} / {{cases/scenarios|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|crss_deaths|,.0f}} |
| Observed rate / model prediction in cell | {{cases/scenarios|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|observed_rate|pct:1}} / {{cases/scenarios|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|predicted_in_cell|pct:1}} |
| Standardised probability | {{cases/scenarios|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|model_risk|cipct:1}} |

{{mdtable:cases/scenario_contrasts|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes|factor:Factor:;rr_case_vs_without:RR, case vs without:ci:2@rr_case_vs_without;shapley_share_risk_difference:Shapley share (risk difference):pct:0;shapley_share_log_rr:Shapley share (log RR):pct:0;share_if_added_first:Share if considered first:pct:0;share_if_added_last:Share if considered last:pct:0}}

Four statements about "how much of this risk is due to the belt" are all arithmetically correct
and all different: {{cases/scenario_contrasts|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes;factor=unbelted|shapley_share_risk_difference|pct:0}}
(Shapley, risk scale), {{cases/scenario_contrasts|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes;factor=unbelted|shapley_share_log_rr|pct:0}}
(Shapley, log scale), {{cases/scenario_contrasts|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes;factor=unbelted|share_if_added_first|pct:0}}
(belt considered first) and {{cases/scenario_contrasts|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes;factor=unbelted|share_if_added_last|pct:0}}
(belt considered last). Negative shares arise because the single-vehicle factor has a point
estimate below 1 in this combination (its interval includes 1) (RR {{cases/scenario_contrasts|model=main (no drugs);case=speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes;factor=single_vehicle|rr_case_vs_without|ci:2@rr_case_vs_without}}
for the case vs the same driver in a multi-vehicle crash), so the "parts" do not partition a
positive whole and the other factors' shares must exceed it. None of these is the cause of
anyone's death.

## 3. Why individual attribution is not identifiable (answer to G)

1. **Counterfactuals are unobserved.** Whether a particular driver would have died had they been
   belted, sober or slower is never observed; the data contain only one outcome per person.
2. **The model describes averages.** A standardised probability averages over the road, time and
   person mix of many crashes; the same combination occurs in crashes of very different violence.
3. **Factors are recorded after the crash, by police,** with severity-dependent completeness
   (Phase 1 and `reports/speeding_confounding.md`); travel speed and crash forces are not
   measured.
4. **Interaction makes contributions undefined.** With non-additive risks, a factor's effect
   depends on the others present, so "x% due to alcohol" has no unique meaning; any allocation
   rule (Shapley, sequential, scale) imposes a convention that the data do not choose.
5. **Support.** Many extreme combinations have too few records for any estimate; filling them
   with a model is extrapolation, which the explorer refuses to do.

What *can* be said about a case: how common the combination is, how often comparable drivers
died, what a model standardised over many crashes predicts, and which single changes are
associated with the largest differences — all conditional on a reported crash and as
associations.

## 4. Grid coverage

{{mdtable:cases/scenarios|model=main (no drugs);n_factors_present=4~5|case:Case:;crss_n:Drivers:,.0f;crss_deaths:Deaths:,.0f;observed_rate:Observed rate:pct:1;model_risk:Standardised probability:pct:1;status:Status:}}

The full grid (96 cases in the main model, 48 in the drug model) is in
`outputs/tables/cases/scenarios.csv` and the interface.
