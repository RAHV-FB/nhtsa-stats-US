<!-- Generated from reports/templates/case_comparisons.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

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
| CRSS sample drivers with exactly this combination | 176 |
| …of whom died | 52 |
| Observed weighted death rate | 19.3% |
| Mean model prediction for these drivers (calibration check) | 19.3% |
| Standardised probability (all drivers' road/time/person mix) | 15.9% (11.8–21.2%) |
| RR vs a belted, sober, non-speeding driver in a daytime multi-vehicle crash | 308 (210–453) |
| FARS: light-vehicle drivers killed per year with this combination (observed; alcohol as expected count) | 312 |

With one factor absent and the others kept:

| Factor set to reference | Standardised probability without it | RR, case vs without | Comparison supported |
|---|---|---|---|
| speeding | 5.4% | 2.95 (2.07–4.22) | True |
| alcohol | 11.3% | 1.41 (0.84–2.35) | True |
| unbelted | 2.9% | 5.47 (3.44–8.72) | True |
| night | 12.6% | 1.26 (0.70–2.27) | True |
| single_vehicle | — | — | False |

*Reading.* The comparison that changes the modelled probability most is the belt: the same
case with the driver belted has
5.5 (3.4–8.7)
times lower modelled risk. Removing exceedance divides it by
3.0 (2.1–4.2);
removing alcohol, given the other factors, changes it by
1.41 (0.84–2.35)
— not distinguishable from no change *for a driver already unbelted, speeding and alone on the
road at night*, even though alcohol is strongly associated with death on its own. Single-factor
contrasts depend on which other factors are present: this is what non-additivity means for an
individual case. The single-vehicle comparison is unsupported (too few multi-vehicle crashes with
the same other four factors). Because an intermediate combination is unsupported, no allocation
of the risk difference among the factors is shown for this case.

*Calibration and standardisation.* Three numbers describe "the risk" of this case. The observed
rate (19.3%,
from 52
deaths, itself imprecise) and the model's mean prediction for the same drivers
(19.3%)
agree because the model is saturated in the case factors (a first version with only pairwise
products did not, `docs/model_validation.md`). The standardised probability
(15.9%)
is somewhat lower because such crashes occur disproportionately in rural areas and involve
younger drivers (both in the model); standardisation answers "what if this combination occurred in the
average crash setting". None of the three is a forensic probability for one driver.

**(b) With police-reported drugs** (drivers with known drug status; night not in this grid) —
exceeded limit + alcohol + drugs + unbelted + single-vehicle crash:

| Quantity | Value |
|---|---|
| CRSS sample drivers / deaths | 51 / 12 |
| Standardised probability | 10.0% (4.0–22.6%) |
| Same case without police-recorded drugs | 10.7% (RR 0.93 (0.32–2.67)) |

The drug contrast for this case is compatible with no difference, its interval is wide, and the
subset of drivers with recorded drug status is itself selected. Removing alcohol or the belt
from this case leads to combinations with too little support, so those contrasts are withheld.

## 2. A supported case: what allocations look like, and why they are not causes

Alcohol + unbelted + night + single-vehicle crash (no speeding recorded) is supported in every
intermediate combination:

| Quantity | Value |
|---|---|
| CRSS sample drivers / deaths | 1,017 / 159 |
| Observed rate / model prediction in cell | 6.2% / 6.2% |
| Standardised probability | 5.4% (4.1–7.1%) |

| Factor | RR, case vs without | Shapley share (risk difference) | Shapley share (log RR) | Share if considered first | Share if considered last |
|---|---|---|---|---|---|
| alcohol | 1.47 (1.10–1.96) | 31% | 28% | 13% | 32% |
| unbelted | 14.89 (8.69–25.50) | 82% | 66% | 35% | 94% |
| night | 0.97 (0.75–1.25) | 4% | 6% | 2% | -3% |
| single_vehicle | 0.68 (0.44–1.03) | -16% | -0% | 1% | -48% |

Four statements about "how much of this risk is due to the belt" are all arithmetically correct
and all different: 82%
(Shapley, risk scale), 66%
(Shapley, log scale), 35%
(belt considered first) and 94%
(belt considered last). Negative shares arise because the single-vehicle factor has a point
estimate below 1 in this combination (its interval includes 1) (RR 0.68 (0.44–1.03)
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

| Case | Drivers | Deaths | Observed rate | Standardised probability | Status |
|---|---|---|---|---|---|
| speeding=none, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes | 1,017 | 159 | 6.2% | 5.4% | supported |
| speeding=exceeded_limit, alcohol=no, unbelted=yes, night=night, single_vehicle=yes | 228 | 57 | 11.4% | 11.3% | supported |
| speeding=exceeded_limit, alcohol=yes, unbelted=no, night=night, single_vehicle=yes | 237 | 22 | 2.7% | 2.9% | supported |
| speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=day, single_vehicle=yes | 90 | 22 | 16.6% | 12.6% | supported |
| speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=no | 55 | 9 | — | — | insufficient support: no model estimate shown |
| speeding=exceeded_limit, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes | 176 | 52 | 19.3% | 15.9% | supported |
| speeding=other_speeding, alcohol=no, unbelted=yes, night=night, single_vehicle=yes | 449 | 65 | 6.0% | 5.5% | supported |
| speeding=other_speeding, alcohol=yes, unbelted=no, night=night, single_vehicle=yes | 760 | 27 | 0.9% | 1.1% | supported |
| speeding=other_speeding, alcohol=yes, unbelted=yes, night=day, single_vehicle=yes | 190 | 41 | 11.5% | 9.4% | supported |
| speeding=other_speeding, alcohol=yes, unbelted=yes, night=night, single_vehicle=no | 73 | 11 | 11.0% | 7.4% | supported |
| speeding=other_speeding, alcohol=yes, unbelted=yes, night=night, single_vehicle=yes | 312 | 66 | 11.7% | 8.8% | supported |

The full grid (96 cases in the main model, 48 in the drug model) is in
`outputs/tables/cases/scenarios.csv` and the interface.
