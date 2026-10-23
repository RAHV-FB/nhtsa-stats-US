# Policy simulation and cost model: assumptions, structure and interpretation (RQ10)

Code: `src/nhtsa_stats/simulation/engine.py` (simulator), `src/nhtsa_stats/simulation/costs.py`
(cost model), `src/nhtsa_stats/simulation/evidence.py` (evidence ledger, RQ9).
Outputs: `outputs/tables/simulation/` (baseline, overlap, threshold tables, `SUMMARY.md`).
Tests: `tests/test_simulation.py`, `tests/test_costs.py`.

> **Status of every simulated number: hypothetical.** The simulator does not estimate the
> effect of any intervention. It applies arithmetic to (a) empirical quantities from FARS and
> CRSS and (b) assumptions that *you* supply. If the assumptions are wrong, the outputs are
> wrong. The project ships no default effect sizes, no default prices, no default discount rate
> and no monetary value of a statistical life.

## 1. What the database can and cannot identify

### 1.1 The inventory check

The 36 FARS/CRSS archives were searched for any field that records an intervention or a cost:
`engine.enforcement_field_search()` scans the column inventory
(`outputs/audit/column_inventory.csv`; 1,712 source-table-column combinations in 67
source-tables, label `*NAME` columns excluded) for the patterns *camera, enforcement,
citation, checkpoint, cost, price, dollar, ticket, fine, penalty, violation, police, test,
alcohol/drug test status, result and determination method, drug toxicology, special use,
emergency use, prior convictions and their dates, special jurisdiction, licence status /
compliance / restrictions / endorsements, budget, patrol, radar/lidar, sobriety, breath,
campaign, work/school zone*. The 53 matching column names and their meaning are in
`outputs/tables/simulation/inventory_enforcement_cost_fields.csv` (every match is
interpreted; a test fails if one is left unclassified):

| Matched fields | What they are | Why they cannot measure an intervention |
|---|---|---|
| `ALC_STATUS`, `ATST_TYP`, `ALC_RES`, `A_ALCTES`, `DRUGTST1-3`, `DSTATUS`, `DRUGRES*`, FARS `drugs` table (`DRUGSPEC`, `DRUGMETHOD`, `DRUGQTY`, `DRUGACTQTY`, `DRUGUOM`) | alcohol/drug tests and results of persons *involved in the crash* | post-crash; testing depends on injury severity and state; says nothing about roadside screening of drivers who did not crash |
| `ALC_DET`, `DRUG_DET`, `DRUGS` | how police determined alcohol/drug involvement; police-reported drug involvement | describe the crash-involved person (an exposure), not enforcement |
| `MVIOLATN`, `VIOLATION` | violations charged to a crash-involved driver | a consequence of the crash, not enforcement intensity |
| `PREV_ACC`, `PREV_DWI`, `PREV_SPD`, `PREV_SUS*`, `PREV_OTH`, `FIRST_MO/YR`, `LAST_MO/YR` (FARS) | prior crashes / convictions / suspensions of crash-involved drivers and their dates | driver history without an exposure denominator; no information on enforcement levels |
| `L_STATUS`, `L_COMPL`, `L_RESTRI`, `L_ENDORS`, `CDL_STAT`, `A_LIC_C`, `A_LIC_S` | licence status/compliance/restrictions of the driver | driver attribute |
| `SPEC_USE`, `EMER_USE` | vehicle in special use (e.g. police car) / emergency use | describes the crashed vehicle, not enforcement activity |
| `SP_JUR`, `WRK_ZONE`, `PBSZONE` | special jurisdiction, work zone, school zone (pedestrian/cyclist crashes) of the crash site | location attributes; no enforcement presence or intensity |
| `BASEPRICE` (vPIC) | vehicle base price decoded from the VIN | vehicle attribute, not a programme cost |
| `BACKUPCAMERA*`, `*AUTOEMERGENCYBRAKING*` (vPIC) | vehicle equipment | not enforcement cameras |

**Conclusion:** no field measures camera deployment, enforcement intensity, checkpoints,
roadside testing of the driving population, publicity campaigns, or any programme cost.
There is no pre/post or treated/untreated contrast for any intervention.

### 1.2 By intervention

| Intervention | What the data identify (Layer A) | What they cannot identify (must be assumed) |
|---|---|---|
| Automated speed enforcement | Observed deaths/fatal crashes in speeding-related and limit-exceeding crashes (FARS census); CRSS estimated all/KA crashes in those segments; adjusted severity association *conditional on a crash* | Camera coverage of exposure; behavioural response; halo; effect on crash occurrence; causal effect on severity; costs |
| Roadside alcohol checks | Expected deaths in crashes with a driver BAC ≥ .08 (FARS multiple imputation); CRSS alcohol-involved (imputed police report) crashes; adjusted severity association | Checks → coverage; detection probability; deterrence; effects on occurrence and severity; costs |
| Roadside drug testing | Deaths in crashes with police-reported drug involvement — **LOW reliability** (status unknown in crashes with about half of all deaths; selective testing; presence ≠ impairment) | Everything about impairment prevalence, risk, testing and deterrence; no severity association is estimated |
| Seat-belt enforcement | Deaths of unbelted LPV occupants (police-reported restraint); FARS within-vehicle belt effectiveness given a fatal crash (closest to causal in this project, misreporting-sensitive) | Share of unbelted occupants who would buckle up; whether converters benefit as much as others |
| Generic (lighting, speed limits, campaigns, ...) | Observed deaths in any segment | The relative reduction itself |

Crash *occurrence* is not identifiable from these data (no exposure: trips, miles, hours), so
every occurrence effect is an assumption. Severity associations are conditional on a
police-reported crash and are not causal effects (see `docs/research_plan.md` RQ1, RQ3).

## 2. Layer structure

```
 Layer A  EmpiricalBaseline      observed / estimated / adjusted_association, with sources
    |        deaths, fatal crashes, KA crashes per segment; overlap partitions; RRs; belt estimate
    v
 Layer B  Mechanism              explicit causal chain per intervention type
    |        units -> coverage -> behaviour change -> occurrence & severity -> target outcomes
    v
 Layer C  Param / Timing         every coverage, response, effect, deterrence and timing input
    |        point or low/central/high, fixed / uniform / triangular; ramp-up and decay
    v
 Layer D  Outcomes (hypothetical) evaluate, project, combine, tornado, corner_range,
             monte_carlo, solve_scenario_parameter; costs.* for economics and break-even
```

## 3. Layer A — the empirical baseline

`engine.build_baseline(window=(2022, 2024))` reads `data/processed` (FARS census and CRSS
sample, via `nhtsa_stats.analysis.data`) and two output tables:
`outputs/tables/severity/fatal_crude_vs_adjusted.csv` (required: a clear `MissingInputError`
is raised if absent; `require_severity=False` builds without it) and
`outputs/tables/matched/belt_effect.csv` (optional). Every number is a `Quantity` carrying
`kind` (`observed` | `estimated` | `adjusted_association`), `source`, `unit`, CI or SE where
applicable, `n`, `reliability` and a flag (`suppressed` if n < 30 sampled records,
`unstable` if RSE > 30%). `run()` saves it to `outputs/tables/simulation/baseline.csv` and
(with the full structure) `baseline.json`; `EmpiricalBaseline.load()` rebuilds it without the
data.

Segments (definitions in `engine.SEGMENTS`):

| Segment | FARS definition | CRSS definition | Reliability |
|---|---|---|---|
| `speeding` | any in-transport vehicle with SPEEDREL 2–5 | same | moderate |
| `speeding_exceeded_limit` | any vehicle coded exceeded limit / racing | same | moderate (lower bound) |
| `alcohol` | expected value over 10 BAC implicates of 1[driver BAC ≥ .08] | imputed police-reported involvement (`ALCHL_IM`) | moderate; definitions differ |
| `drugs` | any driver with police-reported drug involvement | same | **low** |
| `unrestrained_lpv` | killed LPV drivers/passengers (LPV = `harmonize.LPV_BODY_GROUPS`, including BODY_TYP 49 "light vehicle, unknown type"), aged ≥ 13, front or 2nd row, restraint "none" (population of the belt estimate) | same, persons; age is NHTSA's imputed age (`age_im`) | moderate (FARS), low (CRSS) |

Unknown status is never counted as "no" *or* "yes": deaths in crashes with unknown status are
outside the segment and reported separately (`fars.deaths_per_year.<segment>.status_unknown`),
so segment counts are lower bounds. (For `speeding_exceeded_limit`, "speeding, specifics
unknown" is reported with the unknowns.)

**Freshness of the imported associations.** If an upstream table
(`severity/*.csv`, `matched/belt_effect.csv`) is older than the processed data file it is
computed from, the association is flagged `stale_upstream` in `baseline.csv`, a `STALE` note
is added to the baseline and `SUMMARY.md` shows a warning: re-run the upstream module and then
`engine.run()`.

**Overlap.** Segments overlap (e.g. 4,912 deaths/yr are in crashes that are both
speeding-related and alcohol-involved, 2022–2024; `segment_overlap.csv`). Layer A therefore
stores *partitions*: deaths, fatal crashes (FARS) and KA/all crashes (CRSS) cross-classified
by membership of every segment (32 or 16 cells; `baseline_partitions.csv`). With the
probabilistic alcohol membership, a cell is the expected count over the imputations. CRSS
cells carry a design-based SE; in the published CSV a cell based on fewer than 30 sampled
records is suppressed (value blank), one with RSE > 30% is flagged `unstable`, and an empty
cell (e.g. limit-exceeding but not speeding-related, which cannot occur) is flagged
`no_sample_records`. The engine itself uses every cell (from `baseline.json`), so that the
cells reproduce the segment totals.

## 4. Layer B — mechanisms

All mechanisms return a relative reduction *within their target segment*; Layer D converts it
into counts using the partition.

### 4.1 Coverage functions — why doubling units does not double the effect

* `LinearCappedCoverage(per_unit, cap=1)`: c(u) = min(cap, per_unit · u). Proportional until
  the cap binds, then flat.
* `SaturatingCoverage(rate, max_coverage=1)`: c(u) = max_coverage · (1 − e^(−rate·u)).
  Diminishing returns from the first unit: c(2u)/c(u) = 1 + e^(−rate·u) < 2.

`outputs/tables/simulation/coverage_doubling_demo.csv` shows (in dimensionless units) that
doubling from rate·u = 0.5 to 1 raises saturating coverage by a factor 1.61, from 1 to 2 by
1.37 and from 2 to 4 by 1.14; the capped linear form doubles until the cap and then stops.
Because the effect is (approximately) proportional to coverage, doubling units does not
double deaths prevented (worked example 1: ×1.37).

### 4.2 `SpeedEnforcement` (cameras)

```
c_cur = c(units_current), c_new = c(units_proposed)
E     = min(1, (1 + halo) · c)                         effective share of target exposure affected
S(u)  = S0 · (1 − response · E(u))                     speeding prevalence
B     = 1 − (1 − response·E_new) / (1 − response·E_cur) share of target speeding removed vs baseline
share of target deaths prevented = B · [1 − (1 − occurrence_effect)(1 − severity_effect)]
```

The observed baseline already reflects current deployment, hence the ratio form of B. Crashes
whose speeding is removed are not all prevented: they occur (1 − occurrence_effect) times as
often and are fatal (1 − severity_effect) times as often; the remainder stay in the death
count as non-speeding deaths. Fatal crashes fall by the same share (deaths per fatal crash in
the segment assumed unchanged). KA crashes are computed only if `severity_effect_ka` is given.
The default target is `speeding_exceeded_limit`, the part of speeding cameras act on.

### 4.3 `ImpairedDrivingEnforcement` (alcohol or drug checks)

```
r   = detection_probability · c(checks)                perceived detection risk
B   = 1 − exp(−deterrence_elasticity · (r_new − r_cur))  share of target impaired driving removed
share of target deaths prevented = B · [1 − (1 − occurrence_effect)(1 − severity_effect)]
```

`deterrence_elasticity` is a semi-elasticity: −d ln(prevalence)/d(perceived risk). Fewer checks
than now give a negative "prevented" count (an increase), which is not clipped. Target
`drugs` is allowed but every output carries the LOW-reliability note.

### 4.4 `RestraintEnforcement`

```
share of unbelted deaths prevented = conversion_share · min(1, belt_effectiveness · converter_benefit_ratio)
```

`belt_effectiveness` defaults to the Layer A within-vehicle estimate (FARS double-pair
comparison, proportional reduction in P(death) given a fatal crash: 0.658, 95% CI
0.645–0.670, `matched/belt_effect.csv`), passed as a triangular parameter over its CI and
labelled with its source; misreporting variants are available through
`belt_effectiveness_param(baseline, "misreport_f10")` etc. If neither the estimate nor a user
value exists, a `MissingAssumptionError` is raised. The double-pair estimate comes from
driver / right-front-passenger pairs in multi-occupant vehicles; applying it to other front
and second-row occupants (who are in the target segment) is an extrapolation. Fatal and KA
crashes prevented are not defined (a prevented death need not prevent the crash).

### 4.5 `GenericIntervention`

A user-specified relative reduction in deaths (optionally fatal and KA crashes) in any segment
or `all`.

### 4.6 Converting associations into assumptions (opt-in only)

`severity_effect_from_association(baseline, segment)` turns an adjusted RR into
`severity_effect = 1 − 1/RR` (triangular over the CI). This treats an association conditional
on a crash as a causal, fully reversible effect of removing the factor; the returned
parameter's `source` says so ("ASSUMES the adjusted association is causal"). It is never
applied by default.

## 5. Layer C — the parameters, and why none has a default

| Parameter | Meaning | Domain | Default | Why no default / what could inform it |
|---|---|---|---|---|
| `coverage.per_unit`, `coverage.rate` | share of target exposure covered per unit / saturation rate | [0,1] / > 0 | **required** | Depends on site selection, road network, hours of operation; needs local deployment and traffic data, absent here |
| `coverage.cap`, `coverage.max_coverage` | maximum attainable coverage | [0,1] | 1 (neutral: no cap below 100%) | Neutral value; set lower when sites are limited |
| `behavioural_response` | relative reduction in speeding within covered exposure | [0,1] | **required** | Requires speed measurements before/after deployment; none in FARS/CRSS |
| `halo` | exposure affected outside coverage, as a multiple of covered exposure | [0,10] | 0 (neutral: no spillover) | Spillover is contested; zero is the no-assumption value |
| `detection_probability` | P(impaired driver passing a check is detected), as perceived | [0,1] | **required** | Depends on screening technology and protocol |
| `deterrence_elasticity` | −d ln(impaired-driving prevalence)/d(perceived risk) | ≥ 0 | **required** | Requires prevalence surveys over enforcement changes; none here |
| `occurrence_effect` | relative reduction in crash frequency for exposure whose behaviour changes | [−1,1] | **required** | Not identifiable without exposure data |
| `severity_effect` | relative reduction in P(fatal \| crash) for those crashes | [−1,1] | **required** | Adjusted RRs are associations, not effects (opt-in conversion in 4.6) |
| `severity_effect_ka` | same for P(KA \| crash) | [−1,1] | none → KA not computed | As above |
| `conversion_share` | share of unbelted occupants who would buckle up | [0,1] | **required** | Requires observational belt-use surveys; reported belt use of survivors is unreliable |
| `belt_effectiveness` | proportional reduction in P(death \| crash), belted vs not | [0,1] | Layer A estimate if available, else required | Within-vehicle estimate exists but is conditional on a fatal crash and misreporting-sensitive |
| `converter_benefit_ratio` | converters' benefit relative to average unbelted occupant | [0,10] | 1 (neutral) | Converters may be lower-risk drivers or similar; unknown |
| `relative_reduction_*` (generic) | relative reduction in target outcomes | [−1,1] | **required** | Intervention-specific |
| `timing.ramp_years`, `timing.decay_per_year` | years to full effect; yearly proportional decline after | [0,50], [0,1] | **required for projections** (`Timing.immediate()` is an explicit choice) | Implementation-specific |

Any parameter can be a point value or `Param(central, low, high, "triangular" | "uniform")`.
Ranges feed the tornado, corner range and Monte Carlo. Parameters are drawn independently in
the Monte Carlo; correlated assumptions (e.g. a high response *and* a high halo) are not
modelled and corner ranges should be consulted for the extremes.

## 6. Layer D — outcomes

* `evaluate(scenario, baseline)` — steady-state annual deaths, fatal crashes and KA crashes
  prevented at full implementation, % change vs the baseline, the causal-chain intermediates
  (`chain`), the parameter list (`assumptions`) and `structural_assumptions`; `kind =
  "hypothetical"`.
* `project(scenarios, baseline, horizon_years)` — year-by-year with ramp-up and decay
  (Timing required).
* `combine(scenarios, baseline, overlap=...)` — several interventions without double
  counting. For each partition cell C (a set of segments), with e_i the relative reduction of
  intervention i on its target segment:

  * `multiplicative` (default): prevented = Σ_C D_C · [1 − Π_{i targets C}(1 − e_i)] —
    a shared death survives each intervention independently;
  * `max`: Σ_C D_C · max_i e_i — interventions fully redundant on shared deaths (lower
    bound);
  * `naive_sum`: Σ_i D_target(i) · e_i — what adding separate projections implies; reported
    as `deaths_prevented_naive_sum` with `double_counting_avoided` = naive − combined.

  The overlap counts come from the data (Layer A); the *within-cell* rule is an assumption
  and is reported in every output. Interventions without a crash-level effect (restraint)
  are excluded from combined fatal/KA crash counts and listed in `fatal_crashes_excludes`.
* `tornado`, `corner_range` — one-way and all-corner sensitivity (steady state, or cumulative
  over `horizon_years`, which brings in timing parameters).
* `monte_carlo` — independent draws (seed `config.RANDOM_SEED`), summaries (mean, SD,
  2.5/5/50/95/97.5th percentiles). It reflects assumption uncertainty only: FARS counts are a
  census; CRSS sampling error is reported in Layer A.
* `solve_scenario_parameter` — the parameter value at which an outcome reaches a target.

Structural assumptions attached to every output: static baseline (the window mean, no
secular trend); relative effects homogeneous within the target segment, including deaths
shared with other segments; unknown-status deaths outside segments; no displacement, risk
compensation or exposure change beyond what the parameters encode.

## 7. Cost model (`costs.py`)

* `ProgrammeCosts(initial_investment, annual_operating, service_life_years, discount_rate)` —
  all required. Capital at t = 0 and renewed every service life within the horizon;
  operating costs at the end of years 1..H.
  * capital recovery factor CRF(r, n) = r(1+r)^n / ((1+r)^n − 1) (1/n at r = 0);
  * equivalent annual cost EAC = investment × CRF + annual operating;
  * `present_value(H)`, optional straight-line residual credit; `total_undiscounted(H)`;
    `cash_flows(H)`.
* `SpeedCameraCosts(acquisition_per_unit, installation_per_unit, maintenance_per_unit_year,
  operations_per_unit_year, service_life_years, discount_rate[, admin_per_citation,
  citations_per_unit_year])` → `.programme(units)`, `.incremental(current, proposed)`. The
  admin pair is optional *together*; when omitted the admin component is excluded (shown as
  NaN in the breakdown), not priced at zero.
* `RoadsideCheckCosts(staff_hours_per_check, cost_per_staff_hour, tests_per_check,
  materials_per_test, confirmed_tests_per_check, lab_cost_per_confirmed_test,
  equipment_capital, equipment_life_years, recurring_fixed_per_year, discount_rate)` →
  `.programme(checks)`, `.incremental(current, proposed, new_programme=...)` (whether fixed
  costs are incurred must be stated).
* Missing monetary inputs raise `MissingCostInputError` naming every missing field. Fines are
  transfers and are not modelled as costs or savings. No value of a statistical life is
  assumed; `net_benefit` requires the user's value.
* Cost-effectiveness: `cost_effectiveness` (EAC / annual outcomes, point or Monte Carlo
  arrays), `cost_effectiveness_over_horizon` (PV costs / PV outcomes; the outcome discount rate
  is a required value judgement), `marginal_cost_effectiveness` and `incremental_analysis`
  (frontier with strong and extended dominance, ICERs vs the next less effective
  non-dominated option, a cost-0/effect-0 status quo included by default).

## 8. Break-even outputs and how to read them

1. **Minimum deaths prevented** — `breakeven_deaths(C, T)` = C / T for annualised cost C and
   the user's maximum acceptable cost per death prevented T. Only the ratio R = C/T matters;
   `threshold_breakeven_grid.csv` converts any R into the share of each segment's deaths that
   must be prevented, with no prices or effect sizes.
2. **Minimum effectiveness parameter** — `breakeven_parameter(scenario, baseline, parameter,
   programme, T)` solves numerically through the engine for the parameter value at which
   outcome = C/T (steady state) or PV(outcomes) = PV(costs)/T (with `horizon_years`, timing and
   an outcome discount rate). Other parameters stay at their central values. Status:
   * `solved` with `interpretation = "minimum value required"` (outcome increases in the
     parameter) or `"maximum value allowed"` (it decreases, e.g. decay);
   * `not_achievable` — no value in the search bounds suffices (the programme cannot break
     even under the other assumptions); `max_outcome_in_bounds` shows how far short it falls;
   * `met_throughout_bounds` — the threshold is met even at the least favourable value.
   A break-even value is a *requirement*, not a prediction: the question it answers is "is
   it plausible that the intervention achieves at least x?", which must be judged from
   evidence outside this database.
3. **Equal-budget indifference** — `equal_budget_indifference(budget, cost_x, build_x,
   param_x, ..., cost_y, build_y, param_y, ...)` deploys each intervention at the scale the
   same annual budget buys (EAC = budget), then for each value of X's uncertain parameter
   finds the value of Y's at which both prevent the same deaths. Above the curve Y
   outperforms X; below it X does. The curve, not a single "winner", is the output.

## 9. Worked HYPOTHETICAL examples

> **Every input below is invented for illustration. None is an estimate, a recommendation or
> a claim about any real programme. Prices are in abstract currency units (CU).** The
> baseline is the saved 2022–2024 Layer A (`EmpiricalBaseline.load()`); the outputs quoted
> change whenever the baseline is rebuilt, and those using an adjusted RR also when the
> severity module is re-run.

### Example 1 — speed cameras on limit-exceeding crashes

```python
from nhtsa_stats.simulation import engine as e
from nhtsa_stats.simulation.engine import Param

base = e.EmpiricalBaseline.load()
cams = e.Scenario(
    "cameras",
    e.SpeedEnforcement(
        units_current=0, units_proposed=500,
        coverage=e.SaturatingCoverage(rate=Param(0.002, 0.001, 0.004)),
        behavioural_response=Param(0.3, 0.1, 0.5),
        occurrence_effect=Param(0.2, 0.0, 0.4),
        severity_effect=e.severity_effect_from_association(base, "speeding_exceeded_limit"),
        target_segment="speeding_exceeded_limit",
    ),
    e.Timing(ramp_years=Param(2, 1, 3), decay_per_year=Param(0.0, 0.0, 0.05)),
)
e.evaluate(cams, base); e.tornado(cams, base); e.monte_carlo(cams, base, horizon_years=5)
```

* Target segment: 4,702 deaths/yr (observed). Coverage at 500 units 0.632; share of target
  speeding removed B = 0.190; severity effect imported from the adjusted RR 5.38 (4.50–6.44)
  = 0.814 (0.778–0.845) — note how strong this imported assumption is.
* Central result: 16.1% of target deaths, **759 deaths/yr** (1.85% of all deaths), 671 fatal
  crashes/yr — *hypothetical*.
* Doubling to 1,000 units: coverage 0.865, 1,039 deaths/yr (×1.37, not ×2).
* Tornado (steady state): behavioural response 253–1,265; coverage rate 473–1,039;
  occurrence effect 726–792; severity effect 733–781. Corner range 144–1,844.
* Monte Carlo (10,000 draws): mean 809, 5th–95th percentile 413–1,257 deaths/yr; 5-year
  cumulative (2-year ramp) 1,796–5,521. Over 5 years the ramp-up assumption matters
  (ramp 1 vs 3 years: 3,796 vs 3,037 cumulative deaths).

### Example 2 — adding alcohol checks, without double counting

`ImpairedDrivingEnforcement(0, 20000, SaturatingCoverage(rate=Param(5e-5, 2.5e-5, 1e-4)),
detection_probability=Param(0.5, 0.3, 0.7), deterrence_elasticity=Param(1.0, 0.5, 2.0),
occurrence_effect=Param(0.3, 0.1, 0.5), severity_effect=Param(0.3, 0.1, 0.5))`: perceived
risk 0.316, impaired driving removed 0.271, 1,739 of the 12,581 alcohol deaths/yr.
`combine([cams, checks])`: **2,452 deaths/yr** vs a naive sum of 2,498 — 45.5 deaths of double
counting avoided on the 2,039 deaths/yr that are both limit-exceeding and alcohol-involved
(expected value over BAC imputations). Under the `max` rule: 2,216.

### Example 3 — costs and break-even (CU)

`SpeedCameraCosts(acquisition_per_unit=100, installation_per_unit=20,
maintenance_per_unit_year=10, operations_per_unit_year=15, service_life_years=8,
discount_rate=0.03).programme(500)`: investment 60,000 CU, operating 12,500 CU/yr, CRF 0.1425,
**EAC 21,047 CU/yr**; 10-year total 245,000 CU (renewal at year 8), PV 213,992 CU. Central
cost per death prevented 27.7 CU (Monte Carlo 5th–95th: 16.7–50.9 CU) — meaningful only
relative to a user threshold.

Break-even on the behavioural response (other parameters central), by R = EAC / threshold:

| R (deaths/yr required) | Share of target deaths | Minimum behavioural response |
|---|---|---|
| 100 | 2.1% | 0.040 |
| 500 | 10.6% | 0.198 |
| 1,000 | 21.3% | 0.395 |
| 2,000 | 42.5% | 0.790 |
| 3,000 | 63.8% | not achievable (max 2,531 at response = 1) |

For R = 500 at the central response, the minimum coverage rate is 0.00108 per unit.

Equal budget (21,047 CU/yr) spent on checks priced with `RoadsideCheckCosts` (18 CU per check,
1,000 CU equipment, 500 CU/yr fixed; illustrative) buys 1,129 checks/yr. Indifference curve:
cameras with response 0.1 / 0.2 / 0.3 / 0.4 / 0.5 are matched by checks with deterrence
elasticity 1.47 / 2.99 / 4.59 / 6.25 / 8.00; checks outperform cameras for this budget only
above those values.

### Example 4 — seat-belt enforcement

`RestraintEnforcement(conversion_share=Param(0.1, 0.05, 0.2))` with the Layer A belt estimate:
669 deaths/yr (corner range 328–1,361); with the 10% misreporting variant of the belt
estimate (0.379): 385. The answer is driven by the conversion share (an assumption) and by
survivor misreporting of belt use (a measurement question).

## 10. Assumption-free thresholds produced by `run()`

`outputs/tables/simulation/threshold_required_share.csv` (2022–2024; all deaths 41,000/yr;
1% = 410 deaths/yr). Share of each segment's deaths that would have to be prevented:

| Segment | Deaths/yr | for −1% of all deaths | −5% | −10% |
|---|---|---|---|---|
| speeding | 11,786 | 3.5% | 17.4% | 34.8% |
| speeding_exceeded_limit | 4,702 | 8.7% | 43.6% | 87.2% |
| alcohol (BAC ≥ .08, expected) | 12,581 | 3.3% | 16.3% | 32.6% |
| drugs (LOW reliability) | 4,998 | 8.2% | 41.0% | 82.0% |
| unrestrained_lpv | 10,155 | 4.0% | 20.2% | 40.4% |

These are arithmetic on observed counts (static baseline) and need no effect sizes.
`threshold_conditional_on_empirical_estimates.csv` adds the behaviour change required per 1%
of all deaths *if* the Layer A estimates were causal (belt estimate; severity pathway
`1 − 1/RR` with no occurrence effect), e.g. 6.1% of unbelted occupants would have to buckle
up at the primary belt estimate, 10.7% under 10% misreporting and 93% under 20%.

## 11. Misuse to avoid

* Quoting a simulated number without its assumptions, or as an estimate of what a programme
  "will save".
* Treating adjusted severity RRs (conditional on a crash) as intervention effects without
  saying so, or using them for crash occurrence.
* Adding separately simulated interventions (double counting on shared deaths).
* Using the drug segment as if drug involvement were reliably measured.
* Reading a break-even value as a prediction rather than a requirement.
* Interpreting a cost per death prevented without the user threshold and cost inputs it
  depends on (all of which are user-supplied).
