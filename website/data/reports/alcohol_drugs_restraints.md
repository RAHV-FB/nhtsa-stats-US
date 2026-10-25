<!-- Generated from reports/templates/alcohol_drugs_restraints.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# Alcohol, drugs and restraint use: what can be separated, and what cannot

*Phase 2 report (research question C and D; `docs/research_plan_phase2.md`). Every number is read
from `outputs/tables/drugs/`, `outputs/tables/restraint_behaviour/` and
`outputs/tables/multifactor/` when this report is rendered. Estimate types: **observed** (FARS
census counts and shares), **estimated** (CRSS design-based), **adjusted association**
(model-based, not causal).*

## Summary

1. **Drug involvement is measured selectively, and the selection follows exactly the outcomes
   one would want to compare.** FARS tested
   62% of killed drivers
   for drugs but 19%
   of surviving drivers; among survivors, testing follows police suspicion
   (83%
   tested when police noted drugs vs
   18%
   when they did not) and injury severity. CRSS contains no drug test results at all.
2. **The police record alcohol and drugs together far more often than toxicology finds them
   together.** Among tested killed drivers, the odds ratio between BAC ≥ .08 and a psychoactive
   drug is 1.23 (1.20–1.26);
   in police reports for the same population it is
   5.0 (4.9–5.2),
   and among survivors 13.8 (13.2–14.4)
   against 1.84 (1.74–1.94).
   Police-recorded "drug involvement" is therefore partly a marker of an impaired-driving
   investigation, not an independent measurement.
3. **A CRSS severity association for drugs is not identified.** The crude fatal risk ratio of
   police-reported drug involvement in 2019–2024 ranges from
   1.7 to 73
   depending only on how the
   54% of
   crashes with unknown drug status are allocated. No defensible point estimate exists, so no
   drug contribution is reported anywhere in Phase 2.
4. **Where both are measured most completely, alcohol is the stronger correlate of dying.** In
   the 4
   states that test at least half of both killed and surviving drivers for both alcohol and
   drugs, a driver in a fatal crash with BAC ≥ .08 had
   2.17 (1.82–2.58)
   times the odds of being the one who died, and a driver with any psychoactive drug
   1.28 (1.13–1.44)
   times, mutually adjusted. This is the comparison of the two in this project made where testing is least
   selective (drug-tested: 69%–88% of killed and 51%–80% of surviving drivers in these states) — and
   it is conditional on a fatal crash, on being tested, and on four small states.
5. **Restraint acts at a different stage from the behaviours.** Within the same vehicle, belted
   front-seat occupants' risk of death relative to unbelted ones is
   0.34 (0.32–0.36)
   when the driver was not speeding and
   0.34 (0.32–0.36)
   when the driver was speeding — the driver's speeding does not change it — and only slightly
   more protective with a driver at BAC ≥ .08
   (0.32 (0.30–0.34)).
   It does differ by *kind of impact* (single- vs multi-vehicle crash).
   Across crashes, by contrast, the unbelted risk ratio in CRSS falls from
   46 to
   19 as crash
   circumstances, the driver's own behaviour and configuration are added: unbelted occupants are
   concentrated in the most violent crashes.

---

## 1. Why these three factors need separate treatment

Alcohol, drugs and belt non-use appear together in official tallies of fatal crashes, but they
are measured differently and plausibly act at different stages (`docs/research_plan_phase2.md`
§2): impairment is a candidate cause of the crash and of its violence (Stages A–B), restraint
of whether an occupant survives the forces of a crash that has happened (Stage C). Two
questions follow. Can alcohol and drug involvement be compared at all, given how each is
measured? And does the restraint association look like an independent Stage-C mechanism, or
like a marker of the crashes in which impaired drivers are involved?

## 2. How drug involvement is measured (observed, FARS drivers 2016–2024)

*Source: `drugs/testing_rates`, `drugs/positivity`, `drugs/selection_gradient`.*

| | Killed drivers | Surviving drivers |
|---|---|---|
| Drivers | 222,856 | 263,511 |
| Drug-tested | 61.6% | 18.5% |
| BAC-tested | 65.2% | 23.0% |
| Drug-tested if police noted drugs | 94.0% | 82.5% |
| Drug-tested if police noted no drugs | 58.2% | 17.7% |
| Drug-tested if BAC ≥ .08 measured | 85.4% | 57.3% |
| Drug-tested in 2016 / 2024 | 63.7% / 55.1% | 20.8% / 14.7% |
| "Unknown if tested", 2024 | 21.7% | 4.9% |

**Testing follows severity even among survivors.** Surviving drivers with a serious (A)
injury were drug-tested in
26%
of cases, uninjured ones in
16%.
Any comparison of drug prevalence between killed and surviving drivers, or between severity
levels, therefore compares differently selected samples.

**The selection signature.** If testing is targeted at suspected drivers, the share positive
among the tested should fall as testing widens. Grouping states by their survivor drug-test
rate (tertiles), drug positivity among tested survivors is
42%
where only 9%
are tested and
37%
where 39%
are tested. For alcohol the same signature is much stronger (BAC ≥ .08 among BAC-tested
survivors 27%
vs 12%),
which is consistent with suspicion-based BAC testing; the weaker drug gradient may also reflect
that drug panels are run when blood is already drawn for alcohol.

**What a positive test means.** Among drug-tested killed drivers with a determinate result,
46.3%
had at least one psychoactive drug detected in 2016–2021 and
52.0%
in 2022–2024 (cannabinoids 26.9%,
stimulants 18.0%,
narcotics 10.0%).
These are **detections, not impairment**: in 2022–2024,
8%
of cannabinoid-positive killed drivers had only the inactive metabolite carboxy-THC, and
6%
of positives were positive only through presumptive screens. The coding scheme changed in 2022
(depressants roughly double), so classes are compared only within periods. Positivity among
tested survivors (41.1%
in 2022–2024) is not comparable with killed drivers' because survivors are tested on suspicion.

## 3. Are alcohol and drugs recorded together? (observed)

*Source: `drugs/co_occurrence`, `drugs/police_validity`.*

| Population | Measure | n | Drug among alcohol-positive | Drug among alcohol-negative | Odds ratio |
|---|---|---|---|---|---|
| Killed drivers tested for both | toxicology | 123,991 | 51% | 46% | 1.23 (1.20–1.26) |
| Killed drivers, both police fields known | police report | 113,883 | 43% | 13% | 5.01 (4.86–5.17) |
| Surviving drivers tested for both | toxicology | 40,408 | 49% | 35% | 1.84 (1.74–1.94) |
| Surviving drivers, both police fields known | police report | 161,488 | 39% | 4% | 13.77 (13.19–14.36) |

*(Woolf intervals ignore the clustering of drivers within crashes; they are indicative.)*

By toxicology, drug detection is only modestly more common among alcohol-positive drivers. By
police report, it is several times more common. The police report is also an insensitive
measure: among killed drivers whose toxicology found a psychoactive drug, the police recorded
drug involvement for only
36%
(62% of those with a known
police code); 42% were
coded unknown. *Competing explanations:* (i) police note drugs mainly when an impaired-driving
investigation is already under way; (ii) drivers who combine alcohol with drugs show more
visible impairment. The data cannot distinguish (i) from (ii), but either way the police field
over-states the overlap between alcohol and drugs and cannot serve as an independent drug
measure in models that also contain alcohol.

## 4. Bounds on a drug severity association in CRSS (estimated)

*Source: `drugs/crss_bounds`, `drugs/crss_adjusted`. Population: CRSS police-reported crashes
with known severity; exposure: police-reported drug involvement of any driver.*

CRSS has only the police field. In 2019–2024,
66%
of fatal and 54%
of non-fatal crashes have unknown drug status. The complete-case crude risk ratio is
11.9; if the
unknown crashes were drug-positive at k_f times the known prevalence among fatal crashes and
k_n times that among non-fatal crashes (k from 0 to 3), the risk ratio would lie anywhere
between 1.7 and
73. Even the two extreme codings — all unknown
negative (7.8) and all
unknown positive (2.1) —
differ by a factor of three. Model-A adjusted ratios are
4.29 (3.07–6.01) (complete case) and
2.97 (2.23–3.96) (unknown as no); their
narrow intervals reflect sampling error only and say nothing about which allocation of the
unknowns is right. Because testing and recording depend on severity (§2), the plausible
scenarios are those with k_f ≠ k_n, which is exactly where the bounds are widest.

**Verdict.** No drug severity association, drug attributable fraction or drug position in any
ranking is reported in Phase 2. This is a finding, not an omission.

## 5. A restricted comparison of alcohol and drugs (FARS, minimal selection)

*Source: `drugs/killed_vs_survived`, `drugs/state_testing`. Population: drivers in fatal
crashes tested for both alcohol and drugs; outcome: the driver died (vs survived).
Crash-clustered sandwich CIs. Adjusted for age, sex, vehicle type, crash configuration, night
and period.*

| Sample | BAC ≥ .08 | Any psychoactive drug | Alcohol × drug (product) | Drivers |
|---|---|---|---|---|
| States testing ≥ 50% of killed and surviving drivers for both | 2.17 (1.82–2.58) | 1.28 (1.13–1.44) | 0.65 (0.47–0.89) | 7,845 |
| All states (selectively tested survivors) | 1.40 (1.35–1.46) | 1.17 (1.14–1.20) | 0.87 (0.82–0.94) | 164,399 |

*What it estimates.* Among drivers involved in a crash in which somebody died, whether the
driver was the one who died. This mixes Stage B (impaired drivers' crashes are more often
single-vehicle and more violent for themselves) with Stage C (survivability), and conditions on
a fatal crash. It is not a severity effect and says nothing about crash occurrence.

*What it shows.* Where survivors are tested almost as routinely as the dead, the alcohol
association is larger than nationally (selective testing of survivors biases the national
comparison toward the null, because tested survivors are enriched for suspected impairment).
Drug detection is also associated with dying, less strongly than alcohol, and the
combination is sub-multiplicative. *Limitations:* four states with small samples; drug
detection is not impairment; the high-testing states are rural and not representative.

**Answer to C.** Alcohol and drugs can be separated only in a narrow, explicitly selected
population (tested drivers in fatal crashes in high-testing states), where alcohol is the
stronger correlate of dying. In the general population of crashes, selective testing and the
police tendency to record the two together prevent any defensible comparison; police-recorded
drug involvement should not be used as an adjustment variable for alcohol or speeding.

## 6. Restraint: Stage C, independent of how the crash happened

*Sources: `restraint_behaviour/dpc_by_driver_behaviour` (FARS double-pair comparison,
crash-cluster bootstrap CIs), `restraint_behaviour/crss_unbelted_nested` (CRSS, design-based).*

**Within the same vehicle** (driver and right-front passenger; risk ratio of death, belted vs
unbelted):

| Split | Stratum | Pairs | RR belted vs unbelted | Ratio of RRs (2nd vs 1st stratum) | p (heterogeneity) |
|---|---|---|---|---|---|
| all | all vehicles | 90,240 | 0.34 (0.33–0.35) | — | — |
| driver speeding (any) | driver not speeding | 71,376 | 0.34 (0.32–0.36) | — | — |
| driver speeding (any) | driver speeding | 16,457 | 0.34 (0.32–0.36) | 1.01 | 0.88 |
| driver exceeded limit | driver not speeding | 71,376 | 0.34 (0.32–0.36) | — | — |
| driver exceeded limit | driver exceeded limit / racing | 6,969 | 0.36 (0.33–0.39) | 1.06 | 0.25 |
| driver BAC >= .08 (MI) | driver BAC < .08 | 77,920 | 0.35 (0.34–0.37) | — | — |
| driver BAC >= .08 (MI) | driver BAC >= .08 | 12,320 | 0.32 (0.30–0.34) | 0.90 | 0.01 |
| driver speeding and alcohol | neither | 65,111 | 0.35 (0.33–0.37) | — | — |
| driver speeding and alcohol | both | 5,597 | 0.34 (0.30–0.37) | 0.96 | 0.47 |
| vehicles in crash | multi-vehicle | 60,288 | 0.44 (0.42–0.46) | — | — |
| vehicles in crash | single vehicle | 29,952 | 0.27 (0.26–0.29) | 0.61 | 3.1e-38 |
| time | day | 61,345 | 0.35 (0.33–0.37) | — | — |
| time | night | 28,702 | 0.33 (0.31–0.35) | 0.93 | 0.059 |

The within-vehicle belt risk ratio is the same whether or not the driver was speeding or had
exceeded the limit, and only slightly more protective when the driver had a BAC ≥ .08
(p 0.01).
It *does* differ by crash type: belts are associated with a larger reduction in single-vehicle
crashes (73%)
than in multi-vehicle crashes (56%),
consistent with ejection in rollovers and roadway departures being largely prevented by belts.
The mechanism the data support is therefore: belt protection depends on the *kind of impact*,
not on the behaviour that led to it.

**Across crashes** (CRSS light-vehicle occupants aged 15+; same sample at every step):

| Model | Unbelted vs belted RR | Risk difference | Share of crude log-RR retained |
|---|---|---|---|
| crude | 46.3 (41.0–52.3) | 0.0425 (0.0380–0.0471) | 1.00 |
| + crash environment | 33.6 (29.9–37.7) | 0.0306 (0.0266–0.0346) | 0.92 |
| + person and vehicle | 36.0 (31.9–40.5) | 0.0327 (0.0282–0.0372) | 0.93 |
| + driver's own speeding and alcohol | 28.1 (24.7–31.9) | 0.0258 (0.0216–0.0299) | 0.87 |
| + crash configuration | 18.8 (17.0–20.8) | 0.0174 (0.0149–0.0199) | 0.77 |

The across-crash risk ratio falls from
46 to
28
once crash circumstances and the driver's own speeding and alcohol are held fixed (the
log-RR retains 87%),
and to 19 with crash
configuration. Unbelted occupants
are disproportionately in crashes with impaired or speeding drivers and in more violent crash
types. Even fully adjusted, the across-crash ratio is several times the within-vehicle ratio
(about 0.34,
i.e. unbelted about three times the risk), which is what one expects if unmeasured crash
energy and, possibly, survivor over-reporting of belt use inflate across-crash comparisons.

*Competing explanations tested.* (i) "Belt non-use only marks drunk or speeding drivers" —
rejected for the within-vehicle comparison, which holds the driver and crash fixed and does not
vary with the driver's behaviour. (ii) "Survivors over-report belt use" — not testable here;
Phase 1 showed the within-vehicle reduction would fall from
66% to
38%
if 10% of 'belted' survivors were unbelted (`matched/belt_effect`). The direction is robust; the size is not.

**Answer to D.** Among comparable occupants (same vehicle, same crash), belt use is associated
with roughly a two-thirds lower risk of death given a fatal crash, and this association is
unchanged by the driver's speeding and only slightly larger with a drinking driver; it is
larger in single-vehicle than in multi-vehicle crashes. Across crashes the unbelted
association is far larger and shrinks substantially under adjustment, so across-crash ratios
should not be read as belt effectiveness.

## 7. Implications for official statistics

* "Drug-involved" fatal-crash counts depend on who is tested; they rise with testing and
  cannot be compared across states, years (2022 code change, 2024 pending toxicology) or with
  alcohol counts.
* "Alcohol and drugs" combined categories built from police reports overstate how often the
  two coincide relative to toxicology.
* "Unrestrained occupant deaths" are deaths of occupants who were unbelted — not deaths caused
  by being unbelted. Within-vehicle evidence supports a large protective association that is
  independent of driver behaviour; across-crash counts mix it with crash violence.

## 8. What stronger evidence would require

Routine toxicology for every driver in a sample of crashes of all severities (not only fatal),
with impairment-relevant drug concentrations; measured belt use independent of survivors'
statements (e.g. event data recorders); and linked exposure data for crash occurrence.
