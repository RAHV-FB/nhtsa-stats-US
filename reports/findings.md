<!-- Generated from reports/templates/findings.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

# What makes US road crashes deadly? Findings from FARS and CRSS, 2016–2024

*All empirical numbers in this report are read from `outputs/tables/` when it is rendered
(`nhtsa analyze report`). Each finding names its source table. Estimate types: **observed**
(FARS census counts), **estimated** (CRSS design-based), **adjusted association**
(model-based, conditional on a police-reported crash, not causal), **model-predicted**, and
**hypothetical**.*

## Summary

1. **How often a factor appears in fatal crashes is a poor guide to danger.** Pedestrian
   crashes are 1.2%
   of police-reported crashes but 18.6%
   of fatal crashes. Rain, wet roads, intersections and crashes involving teenage drivers are
   common in crashes but *under*-represented among fatal ones.
2. **Adjustment changes the picture.** Much of the excess severity of night-time crashes is
   accounted for by other circumstances. The lower severity of rain-crashes runs through wet
   road surfaces. Interstates reverse from riskier to safer than comparable roads. The excess
   severity of crashes involving older drivers is *unmasked*.
3. **"Speeding" is two different things.** Crashes in which a driver exceeded the limit have an
   adjusted fatal risk ratio of 5.2 (4.3–6.3).
   "Too fast for conditions" — three-quarters of police-reported speeding-related crashes —
   shows 1.06 (0.89–1.26).
4. **The most robust severity associations involve objective circumstances**: motorcycles,
   pedestrians, the speed environment, unlit darkness and heavy trucks. Alcohol is strongly
   associated with severity under every coding, although its size depends on the coding. Pedestrian survival falls steeply with the posted speed limit, and is
   worse when the striking vehicle is an SUV or pickup.
5. **Some combinations amplify each other**, notably pedestrian crashes in unlit darkness. Others
   that are often assumed to do so do not.
6. **Crash involvement and crash severity are different problems.** In two-vehicle crashes,
   teenage drivers are over-represented as the culpable party, but crashes involving them are
   less severe. Drivers aged 75+ are also over-represented as the culpable party, and crashes
   involving a driver aged 65+ are more severe.
7. **Within the same vehicle, unbelted occupants die far more often than belted ones.**
   The size of that difference is very sensitive to how accurately surviving occupants report
   belt use.
8. **The post-2020 rise in crash severity is only partly explained by the recorded crash mix.**
   Changes in the recorded circumstances of crashes account for a third to a half of the rise in
   the fatal share; the rest is a higher fatal share within the same circumstances, most clearly
   in speeding-related crashes. Separately, about half of the rise in the share reflects fewer
   non-fatal crashes being reported rather than more fatal ones.
9. **Police-recorded behaviours are measured differently by severity.** Drug and distraction
   fields cannot support severity or trend analysis at all.
10. **The database identifies no intervention effect.** It can show where deaths concentrate,
    how strongly circumstances are associated with severity, and what an intervention would
    have to achieve. It cannot show what cameras, checkpoints or tests would achieve.

---

## 1. Data and approach

FARS records every fatal crash on US public roads:
37,806 deaths in 2016,
36,355 in 2019, a peak of
43,230 in 2021, and
39,254 in 2024. CRSS is a national probability sample
of police-reported crashes of every severity (≈46,500–55,000 sampled crashes per year,
representing 5.3–6.8 million crashes). Severity rates and models use CRSS with design-based
inference: 25 strata, 67 PSUs, 42 degrees of freedom. Counts of deaths use FARS. Rows from the
two systems are never pooled. Methods: `docs/methodology.md`. Variable definitions and coding
breaks: `docs/variable_harmonization.md`.

The share of police-reported crashes that were fatal was
0.49% (0.43–0.57%) in 2019 and
0.65% (0.56–0.75%) in 2021 (estimated).

## 2. Finding 1 — Frequency is not danger

*Source: `descriptive/frequency_vs_severity`; figure `outputs/figures/figures/overrepresentation.png`.*

For each characteristic we compare its share of all police-reported crashes (CRSS, weighted)
with its share of fatal crashes (FARS, census). The ratio is the **over-representation ratio**.
A ratio near 1 means the characteristic is common in fatal crashes *because it is common in
crashes*.

| Characteristic | Share of all crashes | Share of fatal crashes | Over-representation (95% CI) | Crude fatal rate |
|---|---|---|---|---|
| Pedestrian crash | 1.2% | 18.6% | ×15.6 (13.2–18.5) | 8.3% |
| Driver exceeded the limit / racing | 0.85% | 10.9% | ×12.8 | 5.0% |
| Motorcycle involved | 1.6% | 15.5% | ×9.5 | 5.0% |
| Single vehicle, rollover first | 1.4% | 6.7% | ×4.9 | 2.7% |
| Head-on collision | 2.6% | 10.6% | ×4.1 | 2.2% |
| Dark, unlit | 10.3% | 27.2% | ×2.6 | 1.53% |
| 00:00–05:59 | 7.9% | 19.9% | ×2.5 | 1.54% |
| Speed limit 50–55 mph | 13.4% | 29.4% | ×2.2 | 1.22% |
| Speed limit 70+ mph | 4.6% | 8.5% | ×1.9 | 1.10% |
| "Too fast for conditions" | 7.9% | 11.7% | ×1.5 | 0.66% |
| Driver aged 65+ involved | 17.6% | 20.0% | ×1.1 | 0.64% |
| Wet surface | 13.6% | 11.5% | ×0.85 | 0.46% |
| Rain | 9.2% | 7.1% | ×0.77 | 0.43% |
| Intersection | 43.4% | 25.2% | ×0.58 | 0.34% |
| Driver aged 15–20 involved | 19.9% | 12.4% | ×0.62 | 0.41% |
| Rear-end collision | 30.2% | 6.9% | ×0.23 | 0.14% |

*Robustness.* The CRSS-weighted composition of fatal crashes agrees with FARS within CRSS
confidence intervals for darkness, pedestrian and motorcycle involvement, single-vehicle crashes
and young drivers (`measurement/fars_crss_fatal_composition`). This supports using CRSS
denominators with FARS numerators. *Limitation.* Ratios are descriptive; they do not adjust for
other circumstances (finding 2).

## 3. Finding 2 — Adjustment reshapes which circumstances look dangerous

*Source: `severity/fatal_crude_vs_adjusted`; figure `outputs/figures/figures/forest_fatal_crude_vs_adjusted.png`.
Method: survey-weighted logistic models; standardised risk ratios (g-computation). Model A
adjusts for all pre-crash circumstances at once (mutually adjusted), so for a factor with
downstream variables in the dependency diagram — time of day → light, weather → road surface,
driver and vehicle mix → police-reported behaviours — model A also holds those fixed; the
association without them is reported alongside. Model B adds crash configuration, a possible
mediator.*

| Circumstance (vs reference) | Crude RR | Adjusted RR, model A | Adjusted RR, model B |
|---|---|---|---|
| 00:00–05:59 (vs 10:00–15:59) | 3.97 (3.50–4.50) | 1.62 (1.46–1.79) | 1.54 (1.37–1.72) |
| Weekend | 1.61 (1.52–1.71) | 1.16 (1.09–1.23) | 1.12 (1.05–1.20) |
| Dark, unlit (vs daylight) | 3.93 (3.38–4.58) | 1.74 (1.50–2.00) | 1.45 (1.27–1.67) |
| Rain (vs clear) | 0.71 (0.65–0.78) | 1.00 (0.89–1.12) | 0.90 (0.81–1.00) |
| Wet surface (vs dry) | 0.73 (0.68–0.79) | 0.74 (0.66–0.83) | 0.69 (0.62–0.77) |
| Snow / ice surface | 0.41 (0.31–0.53) | 0.36 (0.27–0.50) | 0.28 (0.21–0.38) |
| Interstate | 1.36 (1.16–1.60) | 0.70 (0.60–0.82) | 0.82 (0.72–0.95) |
| Speed limit 50–55 (vs 30–35) | 3.08 (2.52–3.77) | 2.44 (2.08–2.87) | 2.87 (2.54–3.25) |
| Speed limit 70+ | 2.79 (2.31–3.38) | 2.30 (1.84–2.87) | 2.88 (2.37–3.49) |
| Rural area (CRSS PSU) | 1.80 (1.40–2.30) | 1.44 (1.23–1.69) | 1.43 (1.26–1.62) |
| Intersection (vs non-junction) | 0.40 (0.35–0.45) | 0.60 (0.54–0.66) | 0.43 (0.39–0.48) |
| Driver 15–20 involved | 0.65 (0.60–0.72) | 0.86 (0.78–0.94) | 0.92 (0.84–1.01) |
| Driver 65+ involved | 1.13 (1.02–1.25) | 1.66 (1.51–1.81) | 1.66 (1.54–1.80) |
| Heavy truck / bus involved | 1.60 (1.47–1.74) | 1.91 (1.72–2.13) | 2.15 (1.96–2.36) |
| Motorcycle involved | 9.77 (8.68–11.00) | 8.64 (7.76–9.61) | 7.47 (6.59–8.47) |
| Speeding-related (any type) | 2.36 (1.89–2.96) | 1.82 (1.51–2.19) | 2.07 (1.82–2.36) |
| Alcohol involved (imputed) | 6.41 (5.48–7.49) | 4.24 (3.58–5.04) | 3.09 (2.64–3.62) |

What changes, and why it matters:

* **Night.** For 00:00–05:59 against 10:00–15:59 the crude risk ratio is
  3.97 (3.50–4.50). Adjusted for the
  other pre-crash circumstances but not for light, it is
  2.46 (2.15–2.82); holding light fixed
  as well, 1.62 (1.46–1.79). Darkness is
  part of what night means, so the second figure removes part of the night effect itself. The
  night-time hazard is largely the hazard of *what happens at night*: darkness, alcohol,
  higher-speed roads and different crash types. A residual association remains.
  *How much each circumstance accounts for* (`confounding/sequential_fatal`,
  `confounding/shapley_fatal`; adjusted association). Defining night as 21:00–05:59 against
  06:00–20:59, the crude risk ratio is 2.96 (2.71–3.24). Adjusting for eight blocks of
  circumstances at once leaves 1.31 (1.20–1.42), which retains
  25% (18–32%) of the crude log risk ratio.
  Averaged over every order in which the blocks can be added (Shapley shares), light condition
  accounts for 32% (26–38%) of the crude log risk ratio, alcohol for 20% (16–24%), crash
  configuration for 14% (11–17%) and the road environment for 9% (7–11%).
  The share credited to light depends strongly on the order: from
  16% to 51%
  across orders, because light and night are nearly the same thing: at night,
  53%
  of crashes were in lit and
  37%
  in unlit darkness (`confounding/night_light_overlap`). Comparing night with day among crashes
  in darkness only, the crude ratio of
  1.92 (1.74–2.12) falls to
  1.42 (1.30–1.56) after
  adjustment (`confounding/night_within_dark`). The driver and vehicle mix works the other way:
  its share is negative,
  -5% (-6 to -4%),
  so holding it fixed widens the night–day gap.
  The same accounting for weekend crashes takes the crude ratio of 1.61 (1.52–1.71) to
  1.12 (1.05–1.20), mostly through time of day and alcohol; for crashes in rural sampling
  areas (an area-level measure, not the crash site), 1.80 (1.40–2.30) becomes 1.43 (1.26–1.62).
  For crashes involving a driver aged 65+, adjustment *strengthens* the association, from
  1.13 (1.02–1.25) to 1.66 (1.54–1.80), so shares of it are not meaningful.
  Under the strict complete-case outcome the fully adjusted night ratio is
  1.30 (1.20–1.40)
  (`confounding/outcome_definition_sensitivity`), the same as under the imputed outcome; only
  the crude ratio moves
  (3.17 (2.88–3.50)).
  These shares are statistical accounting, not causal mediation. The order of the blocks cannot
  be verified, several blocks are plausible mediators, the behaviours are police-recorded, and
  there are no exposure data, so they do not support statements such as "a third of the night
  effect is caused by darkness".
* **Rain** looks protective in the raw data (crude RR
  0.71 (0.65–0.78)). Adjusted for the
  other circumstances but not for road surface, rain-crashes remain less severe
  (0.76 (0.70–0.82)); holding the
  surface fixed as well, the difference disappears
  (1.00 (0.89–1.12)). Rain's lower
  severity therefore runs through wet and icy surfaces, which remain associated with lower
  severity (wet 0.74 (0.66–0.83)),
  plausibly because drivers slow down (speed is not observed).
* **Interstates reverse.** Crude crashes on interstates are more often fatal, but compared with
  other roads *with the same speed limit* they are less severe. This is consistent with divided,
  access-controlled design.
* **Older drivers are unmasked.** Their crashes happen in low-severity settings (daytime, lower
  speeds), which hides a substantial excess severity once those settings are held constant. The
  likely mechanism is greater physical frailty of older occupants (see finding 7 for
  within-vehicle evidence).
* **Teenage drivers' crashes are *less* severe** even after adjustment. Their problem is crash
  *involvement*, not severity (finding 6).

*Robustness.* Fatal-or-serious (KA) outcome: `severity/ka_crude_vs_adjusted`. Year effects are
included in every model. *Limitations.* Residual confounding is likely: travel speed, vehicle
mass and occupant health are not recorded.

## 4. Finding 3 — "Speeding" mixes a strong and a null association

*Sources: `severity/fatal_speeding_type`, `descriptive/frequency_vs_severity`,
`burden/attributable_fractions_fatal`, `interactions/pairs_fatal` (follow-up pairs).*

Police code a crash as speeding-related when a driver exceeded the limit, was racing, was "too
fast for conditions", or was speeding of unspecified type. Separating the types changes the
conclusion:

| Speeding type | Sample crashes | Fatal | Crude fatal rate | Crude RR | Adjusted RR (model A) | Share on wet roads | Share on snow/ice |
|---|---|---|---|---|---|---|---|
| no | 399,777 | 7,289 | 0.49% | 1.00 (1.00–1.00) | 1.00 (1.00–1.00) | 13% | 2% |
| exceeded_limit_or_racing | 5,884 | 871 | 4.96% | 10.03 (8.26–12.19) | 5.22 (4.34–6.27) | 14% | 2% |
| too_fast_for_conditions | 36,451 | 886 | 0.66% | 1.34 (1.09–1.65) | 1.06 (0.89–1.26) | 24% | 12% |
| speeding_unspecified | 7,075 | 401 | 1.77% | 3.58 (2.77–4.63) | 2.62 (1.91–3.59) | 19% | 8% |
| unknown | 17,821 | 511 | 0.85% | 1.72 (1.37–2.14) | 1.84 (1.48–2.29) | 12% | 3% |

* Crashes involving a driver who **exceeded the limit or was racing** are
  0.85%
  of police-reported crashes but
  10.9%
  of fatal crashes. Their adjusted fatal risk ratio is
  5.2 (4.3–6.3).
* **"Too fast for conditions"** — most of the police-reported category — has no detectable
  excess severity (1.06 (0.89–1.26)).
  It is concentrated on wet and icy roads, where crashes are less severe.
* The severity-pathway attributable fraction is
  5.8% (4.6–7.0%) of fatal
  crashes for limit exceedance and
  0.5% (-1.0 to 2.0%) for
  "too fast for conditions" (model-predicted, finding 10).
* This helps explain the apparently protective "speeding × wet" interaction: for limit
  exceedance, the risk ratio on wet roads
  (4.8 (3.4–6.7)) is compared with
  that on dry roads (5.3 (4.4–6.3))
  in an exploratory pair (`reports/interactions.md`).

*Measurement caveat.* Speeding is a police judgement made after the crash. FARS (fuller
investigation) records speeding in
27% of fatal
crashes; CRSS records it in
20% of the
same population. Recording is therefore more complete when crashes are investigated more
thoroughly. If speeding in non-fatal crashes were recorded with sensitivity 0.5 rather than 0.8,
the crude aggregate risk ratio would fall from
2.47
to 1.41
(`measurement/qba_grid`). The large association for limit exceedance is less exposed to this:
it would need an implausibly large recording gap to vanish.

*Policy relevance.* Automated speed enforcement acts on exceeding the posted limit — the
component with the strong association. The much larger "too fast for conditions" category is
not a camera target and shows no excess severity.

## 5. Finding 4 — The most robust severity associations

*Sources: `severity/fatal_crude_vs_adjusted`, `measurement/alcohol_coding_sensitivity`, `vulnerable/*`.*

* **Motorcycle involvement**: adjusted RR
  8.6 (7.8–9.6).
* **Speed environment**: roads posted 50–55 mph,
  2.44 (2.08–2.87), are as
  severe as 70+ mph roads, 2.30 (1.84–2.87)
  (vs 30–35 mph). 50–55 mph roads are typically undivided rural highways, where head-on crashes
  are possible.
* **Unlit darkness**: 1.74 (1.50–2.00)
  (lit darkness 1.45 (1.28–1.65)).
* **Heavy trucks and buses**: 1.91 (1.72–2.13).
* **Alcohol** is strongly associated with severity under every coding, but the size depends on
  the coding. The adjusted RR is
  4.2 (3.6–5.0)
  using NHTSA's imputation — 5.4 (4.5–6.5)
  in 2016–2018 but 3.8 (3.2–4.7)
  in 2019–2024, after the coding break, when the imputation fills far more unknowns —
  5.9 (5.0–6.8)
  among crashes with known police-reported alcohol, and
  2.8 (2.4–3.3)
  if unknown is treated as "no" (a coding known to attenuate). The complete-case estimate is
  stable across the 2019 coding break:
  6.1
  in 2016–2018 and 5.8
  in 2019–2024.

**Pedestrians** (`vulnerable/pedestrian_killed_contrasts`; figure `pedestrians.png`). Given that a
pedestrian is struck, the adjusted risk of death rises steeply with the posted limit. Relative to
roads posted ≤25 mph, the RR is
2.4 (1.7–3.2)
at 30–35 mph,
4.0 (2.9–5.5)
at 40–45 mph and
6.6 (4.8–9.0)
at 50–55 mph. Compared with a passenger car, the adjusted RR is
1.25 (1.09–1.44)
when the striking vehicle is an SUV,
1.32 (1.18–1.48)
for a pickup and
2.12 (1.72–2.62)
for a large truck or bus. The SUV/pickup excess is relatively largest on roads posted ≤35 mph
(RR 1.62,
1.25–2.10).
SUVs' share of pedestrian deaths rose from
18.9% in 2016 to
24.7% in 2024
(FARS, observed). Unlit darkness
(2.6 (2.1–3.3)),
mid-block crossing
(2.3 (1.9–2.9)
vs crossing in a crosswalk) and age 75+
(3.4 (2.9–4.1)
vs 25–34) are also strongly associated with pedestrian death. *Limitations*: impact speed, vehicle
mass and front-end geometry are not separately observed. Exposure to being struck is not
measured, so these ratios describe severity *given* a pedestrian crash.

## 6. Finding 5 — Which combinations amplify risk

See `reports/interactions.md`. In brief: among the 13 registered pairs, pedestrian crashes in
unlit darkness are the clearest case of amplification on both scales, and motorcycle crashes
involving alcohol carry a large *additive* excess (deaths) although on the ratio scale they are
multiplicative or less. Pedestrian crashes on 50+ mph roads show the largest additive excess of
all, in an exploratory pair. The widely assumed amplifications of speeding by darkness and of
young drivers by night are not supported. The protective-looking speeding × wet interaction
reflects the mix of speeding types ("too fast for conditions" concentrates on wet roads) and the
lower wet-road baseline.

## 7. Finding 6 — Crash involvement is not crash severity

*Sources: `exposure/relative_involvement` (quasi-induced exposure), `severity/fatal_crude_vs_adjusted`;
figure `relative_involvement_age.png`.*

The data contain no measure of how much people drive, so crash *rates* per mile cannot be
estimated. Quasi-induced exposure compares each driver group's share among culpable drivers in
two-vehicle crashes with its share among non-culpable drivers (a proxy for drivers on the road).
Culpability uses pre-crash actions (speeding, critical pre-crash event, driver-error codes), not
charges. Crashes with a hit-and-run vehicle
(12%
of two-vehicle crashes) are excluded, because fleeing drivers are almost always coded culpable
and their age and sex are unknown. Relative involvement ratios (RIR), all qualifying crashes:

| Driver age | Drivers | RIR (95% CI) | Adjusted ratio vs 35–44 |
|---|---|---|---|
| 35-44 | 78,315 | 0.79 (0.78–0.80) | 1.00 |
| 15-20 | 49,283 | 1.92 (1.87–1.97) | 2.47 |
| 21-24 | 44,910 | 1.35 (1.32–1.38) | 1.71 |
| 25-34 | 97,196 | 1.01 (0.99–1.02) | 1.27 |
| 45-54 | 66,745 | 0.72 (0.70–0.73) | 0.90 |
| 55-64 | 55,969 | 0.78 (0.76–0.79) | 0.98 |
| 65-74 | 33,386 | 0.95 (0.92–0.98) | 1.21 |
| 75+ | 18,111 | 1.65 (1.60–1.71) | 2.11 |
| 0-14 | 230 | 2.85 (2.32–3.49) | 3.94 |
| unknown | 3,579 | 1.05 (0.97–1.14) | 1.35 |

* Drivers aged 15–20 are over-represented as the culpable party
  (RIR 1.92 (1.87–1.97)), yet
  crashes involving them are *less* severe
  (0.86 (0.78–0.94)).
* Drivers aged 75+ are also over-represented as the culpable party
  (RIR 1.65 (1.60–1.71)), while
  drivers aged 65–74 are not
  (0.95 (0.92–0.98)). Crashes
  involving a driver aged 65+ are more severe
  (1.66 (1.51–1.81)).
* Alcohol-involved drivers are strongly over-represented, but the size depends on how alcohol
  is measured. With NHTSA's imputed alcohol field the RIR falls from
  6.5 (5.2–8.1) in
  2016–2018 to 2.5 (2.0–3.2)
  in 2020–2024. The fall tracks the 2019–2020 coding break, when the imputation began filling
  a third of drivers' alcohol status almost independently of who was at fault; it is not
  evidence of a change in behaviour. Police-reported alcohol ("yes" vs anything else) gives a
  stable 8.5 (6.6–11.0)
  and 10.1 (8.6–11.9)
  in the same periods, an upper bound if police look for alcohol more in the driver at fault.
  With charge-based culpability (impairment charges excluded) the imputed estimate is
  3.7 (2.6–5.3).
* In two-vehicle crashes, teenage drivers' over-representation is lower at night
  (RIR 1.53 (1.43–1.64)) than
  by day (1.97 (1.91–2.02)),
  relative to the other drivers on the road at each time. Single-vehicle crashes, where
  young and night-time drivers' crashes concentrate, are outside this design.

*Assumptions (untestable here):* non-culpable drivers represent drivers on the road — but the
non-culpable pool is dominated by drivers struck from behind, so it reflects congested traffic
more than all driving, and drivers less able to avoid other drivers' errors (possibly older
drivers) may be over-represented in it, which would push their RIR down; police code pre-crash
actions without bias by group. QIE says nothing about crash rates per mile, and crash-level
conditions (light, weather) cannot be assessed with it.

## 8. Finding 7 — Restraint use

*Sources: `matched/belt_effect`, `matched/double_pair_comparison`, `matched/clogit_coefficients`
(FARS, within the same vehicle); `person/lpv_killed_crude_vs_adjusted`,
`person/lpv_killed_interaction_restraint_x_age` (CRSS, design-based).*

Comparisons between people in different crashes cannot separate belt use from crash energy:
unbelted occupants are, on average, in more violent crashes. FARS allows a comparison **within
the same vehicle**, which holds fixed everything the occupants share — impact speed, vehicle,
road, weather.

* **Double-pair comparison** (drivers and right-front passengers; 45,805 pairs with at least one
  death). Given a crash severe enough to kill someone in the vehicle, a belted occupant's risk of
  dying was
  65.8% (64.5–67.0%)
  lower than an unbelted occupant's (crash-cluster bootstrap CI). The four component comparisons
  agree closely.
* **Conditional logistic regression** with the vehicle as the matched set, adjusted for age, sex
  and seat: odds ratio of death, unbelted vs belted,
  5.07 (4.84–5.31). Deaths are common
  in these vehicles, so this odds ratio overstates the risk ratio.
* **The estimate depends on truthful reporting by survivors.** Belt use of surviving occupants
  is largely what they tell police. If 10% of "belted" survivors were in fact unbelted, the
  reduction would be
  37.9% (36.2–39.4%);
  at 20%, 4.4% (2.0–6.4%).
  The association would vanish at about
  21%
  misreporting. The size is therefore uncertain; the direction is not, unless misreporting is
  very large.
* **Frailty.** Within the same vehicle, belted occupants aged 65+ died more often than belted
  occupants aged 25–44 of the same sex
  (2.81 (2.39–3.35)
  times the risk). Women and men of similar age differed little
  (1.03 (1.00–1.07)).
* **Motorcycle helmets** (operator and passenger on the same motorcycle): risk ratio of death,
  helmeted vs unhelmeted,
  0.69 (0.60–0.80);
  few motorcycles have riders who differ in helmet use, so this is imprecise.

Across crashes (CRSS), unbelted light-vehicle occupants were far more likely to die than belted
ones: crude RR 46.2 (41.0–52.1),
24.0 (21.3–27.0) after
adjusting for person and pre-crash circumstances. These figures are several times the
within-vehicle estimate, as expected if unbelted occupants are in more severe crashes and
survivors over-report belt use. **They must not be read as belt effectiveness.** The *excess*
risk of being unbelted rises steeply with age on the additive scale: the risk difference is
1.5% at 25–34 but
6.6% at 75+, although the
risk ratio is lower at 75+
(0.60 (0.48–0.75) times the
25–34 ratio).

*Limitations.* All within-vehicle estimates are conditional on a fatal crash and assume that
occupants of the same vehicle differ only in belt use, age, sex and seat; belt use is recorded
by police, partly from survivors' statements.

## 9. Finding 8 — The post-2020 rise in severity

*Sources: `trends/numerator_denominator`, `trends/decomposition`, `trends/annual_shares`,
`trends/within_by_subgroup`, `trends/outcome_definitions_by_year`, `trends/fars_changes`.
Method: survey-weighted Oaxaca–Blinder-type decomposition with standardised margins: the
2016–19 model applied to 2020–24 crashes gives the fatal share expected from the change in
recorded circumstances alone. Labels: estimated (shares), adjusted association (composition and
within-circumstance parts), observed (FARS).*

**How large the rise is.** The fatal share of police-reported crashes rose from
0.51% (0.45–0.58%) in 2016–19 to 0.64% (0.56–0.73%)
in 2020–24, a risk ratio of 1.25 (1.14–1.37). Under the strict
complete-case outcome the rise is larger: 1.31 (1.20–1.44).
The fatal-or-serious (KA) share shows no clear rise
(0.15 (-0.08 to 0.37) percentage points).

**Numerator and denominator.** Fatal crashes rose
(1.109 (1.022–1.204), matching the FARS census ratio of
1.107), but the
number of police-reported crashes fell (0.887 (0.839–0.938)).
The fall in reported crashes accounts for 54% (29–78%)
of the rise in the fatal share. It is not only a fall in property-damage-only reports: deaths
also rose as a share of injury crashes (1.28 (1.19–1.38)).

**Composition accounts for a third to a half.** This is a second, separate accounting of the
same rise, not an addition to the first. Changes in the recorded circumstances of crashes
(time, road, light, weather, alcohol, speeding, driver and vehicle mix, crash configuration)
account for 49% (25–73%) of the rise
when the 2016–19 model is the reference and
37% (-3 to 77%) with the 2020–24 model.
Without crash configuration the share is 34% (10–58%);
without the three variables whose "unknown" coding drifted over the period (junction, weather,
road surface) it is 36% (18–54%);
under the complete-case outcome it is 47% (28–66%).
Within the same recorded circumstances the fatal share was higher by a factor of
1.11 (1.04–1.20). The largest within-circumstance
increase is in speeding-related crashes (1.38 (1.20–1.58)); there is none in
alcohol-involved crashes (1.01 (0.87–1.17)).

**Year by year, the two outcome definitions disagree about 2023–24.** Observed fatal share
against the share expected from the recorded crash mix under the 2016–19 model (model B):

| Year | Fatal share, imputed outcome | Observed ÷ expected, imputed | Fatal share, complete case | Observed ÷ expected, complete case |
|---|---|---|---|---|
| 2019 | 0.49% (0.43–0.57%) | 0.99 (0.94–1.05) | 0.47% (0.41–0.55%) | 0.96 (0.91–1.01) |
| 2020 | 0.68% (0.59–0.79%) | 1.16 (1.06–1.26) | 0.67% (0.58–0.77%) | 1.10 (1.00–1.21) |
| 2021 | 0.65% (0.56–0.75%) | 1.13 (1.03–1.25) | 0.69% (0.59–0.81%) | 1.17 (1.08–1.28) |
| 2022 | 0.66% (0.57–0.78%) | 1.16 (1.04–1.29) | 0.69% (0.59–0.81%) | 1.18 (1.08–1.28) |
| 2023 | 0.61% (0.53–0.71%) | 1.08 (0.97–1.20) | 0.67% (0.57–0.79%) | 1.15 (1.04–1.26) |
| 2024 | 0.59% (0.51–0.69%) | 1.05 (0.96–1.14) | 0.64% (0.54–0.75%) | 1.12 (1.04–1.21) |

Under NHTSA's imputed outcome the 2023–24 fatal share is close to what the crash mix predicts;
under the complete case an excess persists. The imputed CRSS fatal total matches FARS every
year, but by construction (CRSS weights are calibrated to FARS through the imputed severity),
so this is not independent corroboration (`trends/outcome_definitions_by_year`).

**What FARS shows (observed).** Between 2019 and 2021 fatal crashes rose
18.8%. Crashes with police-recorded speeding rose
29.7% and crashes with a driver at BAC ≥ 0.08
(NHTSA's multiple imputation) 33.4%; these
overlapping groups account for 41%
and 49% of the rise. Motorcyclist
deaths kept rising to 2024 (5,044 →
6,137 → 6,227), while total
deaths fell back from 43,230 to 39,254.

*Limitations.* The within-circumstance part is a residual: it contains unmeasured circumstances
(travel speed above all), changes in recording, and changes in which crashes are reported to
the police. The split between composition and within-circumstance depends on the reference
model, and the variance of NHTSA's single imputation of severity is not in the intervals. There
are no exposure, speed or enforcement data, so the rise cannot be attributed to the pandemic or
any other cause.

## 10. Finding 9 — Measurement: what the data can and cannot measure

*Sources: `measurement/*`.*

* **Alcohol testing is selective.** In 2016,
  74% of
  killed drivers were tested, against
  28%
  of surviving drivers; in 2024 the figures were
  59% and
  21%.
  Survivors are tested mainly on suspicion.
* **Police reports miss alcohol in killed drivers.** Among tested FARS drivers with a known
  police report, the report identifies BAC ≥ 0.08 in
  87% of killed
  and 98% of
  surviving drivers.
* **CRSS alcohol coding broke in 2019.** "Unknown" rose from
  11% to
  30% of non-fatal
  crashes in one year. Models use NHTSA's imputed field, and the alcohol association is reported
  under three codings (finding 4).
* **Restraint is self-reported by survivors.** Reported belt use among occupants with known
  status is 98.7% among the
  uninjured but 50.8% among the
  killed. Some of that gap is real protection, and some is likely over-reporting by survivors.
* **Drug involvement and distraction cannot be used.** Their "unknown" shares rose sharply in
  2017–2020 (drugs: 16% →
  58% of non-fatal
  crashes). Drug testing is selective, and a positive test shows presence, not impairment. No
  severity association or prevalence is reported for drugs or distraction.

## 11. Finding 10 — Burden and what can be said about interventions

*Sources: `burden/attributable_fractions_fatal`, `policy/evidence_ledger`; details in
`reports/policy_analysis.md`.*

Severity-pathway attributable fractions are model-predicted shares of fatal crashes that would
not have been fatal had a circumstance been absent, holding everything else fixed and assuming
the crash still happened:

| Hypothetical shift | Share of fatal crashes (95% CI) | Deaths per year, FARS-scaled |
|---|---|---|
| Speeding-related crashes as if not speeding-related | 9.1% (6.9–11.3%) | 3,736 |
| Alcohol-involved crashes as if alcohol-free | 19.7% (16.6–22.8%) | 8,072 |
| Crashes in dark, unlit conditions as if the road were lit | 4.4% (1.7–7.1%) | 1,789 |
| Crashes on 50+ mph roads as if on 40-45 mph roads (speed-environment contrast) | 17.6% (12.9–22.3%) | 7,213 |
| Both speeding and alcohol removed (joint) | 26.5% (23.2–29.8%) | 10,861 |
| Crashes with a driver exceeding the limit / racing as if not speeding-related (model with speeding type) | 5.8% (4.6–7.0%) | 2,371 |
| 'Too fast for conditions' crashes as if not speeding-related (model with speeding type) | 0.5% (-1.0 to 2.0%) | 202 |

These are **not** lives saved by any programme. They omit any effect on crash occurrence. They
assume no unmeasured confounding and correct measurement, and they say nothing about whether an
intervention can actually change the circumstance. Under plausible under-recording of speeding in
non-fatal crashes, the speeding fraction shrinks towards zero; the alcohol fraction does not
(`burden/bias_sensitivity`).

## 12. Prediction models

*Sources: `ml/metrics_test`, `ml/paired_differences`, `ml/calibration_by_risk_tier`,
`ml/temporal_stability`, `ml/pattern_confirmation`; full validation report and model cards in
`docs/model_validation.md`. Labels: model-predicted; the metrics are design-weighted estimates
on held-out years.*

Prediction models were trained on 2016–2021, tuned and selected on 2022, and evaluated once on
2023–2024, years used for no modelling choice. Inputs exclude anything recorded after the crash
and the calendar year, enforced by the same leakage gate as the statistical models. There are
two input stages: pre-crash circumstances only, and pre-crash circumstances plus crash
configuration. The outcome is a fatal crash among police-reported crashes; prevalence in the
test years was 0.60% (0.53–0.68%).

* **Discrimination.** With crash configuration, gradient-boosted trees reach an AUROC of
  0.921 (0.912–0.929) against 0.903 (0.893–0.912) for a
  main-effects survey logistic model. From pre-crash circumstances alone the figures are
  0.835 (0.820–0.849) and 0.815 (0.795–0.832). Adding crash
  configuration raises the boosted model's AUROC by
  0.086 (0.075–0.096).
* **Usefulness for picking out fatal crashes is limited.** Average precision is
  0.165 against a base rate of
  0.006: even among the crashes ranked riskiest, most are not fatal.
* **Calibration.** Overall, observed ÷ predicted fatal crashes is
  1.04 (0.97–1.11), but this hides miscalibration by risk level: among the half
  of crashes with the lowest predicted risk it is 0.47 (0.32–0.63)
  (predictions about twice the observed share), and among the riskiest fifth
  1.09 (1.03–1.17). Logistic models show the same pattern.
* **Drift.** A model trained on 2016–2019 under-predicts fatal crashes after 2020
  (observed ÷ predicted 1.11 (1.02–1.20) in 2020, 1.15 (1.06–1.25) in 2022, 1.04 (0.95–1.14) in 2024), in line
  with finding 8.
* **Interactions.** The 13 pre-specified interaction terms of finding 5 add almost nothing to
  prediction (AUROC +0.001). Screening the boosted
  model on 2016–2022 suggested two further interactions that were then confirmed on 2023–2024
  (survey-weighted, Holm-adjusted): intersection × head-on collision (ratio of odds ratios
  0.17)
  and speeding × angle collision
  (2.11). Both are
  exploratory and non-causal.

*Limitations.* Predictive accuracy is not evidence that any input causes fatal outcomes.
Several "unknown" inputs mostly mark hit-and-run crashes, and imputed alcohol may carry
information about severity (`docs/limitations.md` §2–3); excluding the hit-and-run proxies
changes test discrimination only slightly (`docs/model_validation.md`). Intervals reflect
test-set sampling only, not model selection or training-sample variability.

## 13. What is not supported by these data

* Crash rates per mile, trip or driver, and therefore any statement that a factor "causes crashes".
* The effect of speed cameras, sobriety checkpoints, roadside drug tests, belt enforcement or
  campaigns. No such programme is recorded in the archives.
* Drug-impairment prevalence or severity effects, and distraction trends.
* Causal effects of behaviours on severity. All severity associations are conditional on a
  reported crash and on recorded covariates.

## 14. Exploratory vs confirmatory

The pre-specified analyses are: crude versus adjusted severity (RQ1), the 13 registered interaction pairs,
the measurement analyses (RQ3), within-vehicle restraint (RQ6), QIE (RQ7), the post-2020
decomposition (RQ5) and burden (RQ9). These are confirmatory within their stated assumptions. The
speeding-type split, the two interaction pairs added at implementation and the three
limit-exceedance follow-ups were motivated by the audit and by earlier results, and are
exploratory. Machine-learning importance rankings are descriptive of
the model, not findings about the world.
