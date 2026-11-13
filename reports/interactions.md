<!-- Generated from reports/templates/interactions.md by `nhtsa analyze report`; every number is looked up in outputs/tables. Edit the template, not this file. -->

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
intervals are design-based (Taylor linearisation, 42 df).

## Results: registered pairs, fatal outcome

| Pair (A x B) | Risk with neither (per 1,000) | Risk with both (per 1,000) | RR of A when B absent | RR of A when B present | Additive interaction (per 1,000) | Holm p, additive | Ratio of RRs (multiplicative) | Holm p, multiplicative | Co-occurrence O/E, all crashes | Fewest events in a cell |
|---|---|---|---|---|---|---|---|---|---|---|
| speeding x dark_unlit | 4.1 (3.5–4.7) | 12.5 (10.3–14.7) | 1.86 (1.49–2.31) | 1.74 (1.39–2.16) | 1.8 (-0.7 to 4.3) | 0.45 | 0.93 (0.73–1.20) | 1 | 1.35 | 587 |
| speeding x wet | 5.3 (4.6–6.1) | 5.7 (4.8–6.6) | 1.91 (1.56–2.34) | 1.33 (1.09–1.63) | -3.4 (-5.1 to -1.8) | 0.0012 | 0.70 (0.56–0.87) | 0.014 | 1.74 | 276 |
| speeding x alcohol | 4.0 (3.4–4.6) | 28.0 (22.4–33.5) | 1.97 (1.61–2.41) | 1.53 (1.22–1.92) | 5.8 (0.8–10.8) | 0.099 | 0.78 (0.64–0.94) | 0.078 | 1.67 | 713 |
| alcohol x dark_unlit | 3.8 (3.3–4.3) | 27.5 (22.7–32.2) | 4.35 (3.64–5.19) | 4.08 (3.29–5.06) | 8.0 (4.8–11.1) | 8.2e-05 | 0.94 (0.78–1.13) | 1 | 2.78 | 782 |
| high_speed_road x dark_unlit | 3.6 (3.2–4.1) | 12.1 (10.0–14.3) | 2.35 (2.02–2.73) | 1.46 (1.26–1.69) | -1.1 (-2.7 to 0.5) | 0.45 | 0.62 (0.53–0.72) | 1.2e-06 | 1.82 | 1,007 |
| motorcycle x speeding | 4.4 (3.8–5.1) | 68.6 (58.8–78.5) | 8.63 (7.74–9.62) | 8.51 (7.12–10.18) | 26.7 (16.8–36.7) | 2.7e-05 | 0.99 (0.84–1.16) | 1 | 1.53 | 409 |
| motorcycle x alcohol | 4.0 (3.5–4.5) | 110.5 (87.9–133.0) | 9.74 (8.52–11.14) | 6.16 (5.19–7.31) | 57.8 (36.6–79.0) | 2.2e-05 | 0.63 (0.51–0.79) | 0.0013 | 1.42 | 319 |
| young_driver x late_night | 5.2 (4.5–5.9) | 8.1 (6.4–9.7) | 0.83 (0.75–0.91) | 0.99 (0.82–1.19) | 0.8 (-0.8 to 2.3) | 0.45 | 1.19 (0.97–1.46) | 0.45 | 0.82 | 270 |
| older_driver x angle | 1.1 (0.9–1.3) | 12.1 (10.0–14.3) | 1.72 (1.57–1.89) | 1.74 (1.53–1.99) | 4.4 (2.9–5.9) | 6.3e-06 | 1.01 (0.88–1.17) | 1 | 1.18 | 215 |
| heavy_truck x high_speed_road | 4.7 (4.0–5.3) | 19.1 (15.7–22.5) | 1.66 (1.43–1.93) | 2.07 (1.80–2.38) | 6.8 (4.0–9.6) | 0.00014 | 1.24 (1.02–1.51) | 0.18 | 1.50 | 327 |
| rural x dark_unlit | 3.9 (3.3–4.5) | 8.8 (7.2–10.3) | 1.66 (1.41–1.95) | 1.04 (0.83–1.30) | -2.3 (-4.0 to -0.6) | 0.053 | 0.63 (0.51–0.77) | 0.00034 | 1.65 | 1,053 |
| weekend x late_night | 4.7 (4.1–5.3) | 7.8 (6.8–8.9) | 1.26 (1.17–1.34) | 0.91 (0.80–1.02) | -2.0 (-3.1 to -0.9) | 0.0028 | 0.72 (0.63–0.82) | 0.00014 | 1.53 | 648 |
| pedestrian x dark_unlit | 4.8 (4.2–5.5) | 178.5 (156.0–201.0) | 17.26 (14.86–20.06) | 28.03 (24.46–32.11) | 93.8 (73.0–114.6) | 2.3e-10 | 1.62 (1.39–1.89) | 1.3e-06 | 1.45 | 318 |

Figure: `outputs/figures/summary/interactions.png`.

### What the pattern shows

**Pedestrian crashes in unlit darkness are super-multiplicative, and so also carry a large additive excess.**
The standardised risk that a crash is fatal when it is a pedestrian crash in unlit darkness is
179 (156–201) per 1,000, against
4.8 (4.2–5.5) for a
non-pedestrian crash in daylight. The pedestrian risk ratio is
17.3 (14.9–20.1) in daylight and
28.0 (24.5–32.1) in unlit darkness:
a ratio of risk ratios of 1.62 (1.39–1.89)
(Holm p 1.3e-06), that is,
the two risks combine by more than multiplying. Because an additive excess is expected whenever two
risks multiply, the additive excess of 94 (73–115) fatal
crashes per 1,000 (Holm p 2.3e-10)
follows from it and is not separate evidence.

**Motorcycle crashes involving alcohol: a large additive excess.** The ratio of risk ratios is
0.63 (0.51–0.79), but the additive
excess is 58 (37–79) per 1,000
(Holm p 2.2e-05), giving a
standardised fatal risk of 110 (88–133)
per 1,000. The two scales answer different questions. On the ratio scale, alcohol involvement is
associated with a *smaller* relative excess in motorcycle crashes than in other crashes (the
combination is sub-multiplicative), but because motorcycle crashes start from a much higher
baseline, the absolute excess associated with alcohol is far larger.
The additive excess shows where excess deaths concentrate (burden): it is expected whenever two
factors each raise risk, even if they combine multiplicatively or less, so it is not evidence
of a special mechanism.

**Heavy trucks on 50+ mph roads.** The additive excess is
6.8 (4.0–9.6) per 1,000
(Holm p 0.00014). The ratio
of risk ratios is 1.24 (1.02–1.51)
(Holm p 0.18).
The multiplicative excess counts as supported only if its Holm-adjusted p-value is small and
the interval for the ratio of risk ratios excludes 1; the additive excess alone shows where
deaths concentrate, not why.

**Several commonly assumed amplifiers are not detected for the fatal outcome.** Speeding in
unlit darkness (ratio of RRs 0.93 (0.73–1.20))
and a young driver late at night
(1.19 (0.97–1.46)) show no detectable
excess on the ratio scale; the intervals do not exclude a moderate one, so this is absence of
evidence, not evidence of absence. For fatal-or-serious (KA) crashes, speeding in unlit darkness
shows an additive excess of
15.4 (8.7–22.2) per 1,000 (Holm p
0.0003) and a ratio of risk ratios of
1.24 (1.05–1.45) (Holm p
0.063). A young driver late
at night has a ratio of risk ratios of
1.14 (1.02–1.28) for KA crashes (Holm p
0.13). Behavioural
factors are recorded differently by severity, which can bias associations in either direction
(the police-recorded alcohol, drug, distraction and speeding fields are more often unknown in
fatal crashes, while killed drivers are tested far more often), and can create such patterns. Rural area × unlit darkness
(0.63 (0.51–0.77)), weekend × late night
(0.72 (0.63–0.82)) and 50+ mph road ×
unlit darkness (0.62 (0.53–0.72))
have ratios of risk ratios below 1. Each factor matters on its own, but the combination is not
more severe than the separate factors imply.

**Speeding on wet roads is less severe than expected.** The additive interaction is
-3.4 (-5.1 to -1.8) per 1,000. Police
"speeding-related" is mostly "too fast for conditions", which concentrates on wet and icy roads
and carries little excess fatal risk (`reports/findings.md`, finding 3), so the pair mixes two
different exposures; a mix of speeding types is one possible reason for the deficit, not an
established one. The exploratory analysis below separates drivers who exceeded the limit, and
the deficit persists there.

## Exploratory pairs (not in the registered family)

Two pairs were added when the analysis was implemented (speeding × 50+ mph road, pedestrian ×
50+ mph road), and three after the speeding-type analysis (drivers who exceeded the limit).
They are outside the Holm family and are hypothesis-generating; p-values are unadjusted.

| Pair | Risk with neither (per 1,000) | Risk with both (per 1,000) | RR of A when B absent | RR of A when B present | Additive interaction (per 1,000) | p, additive | Ratio of RRs | p, multiplicative |
|---|---|---|---|---|---|---|---|---|
| speeding x high_speed_road | 3.9 (3.3–4.5) | 11.7 (10.3–13.0) | 2.47 (1.98–3.09) | 1.26 (1.07–1.48) | -3.3 (-4.7 to -1.9) | 1.7e-05 | 0.51 (0.44–0.60) | 5.2e-11 |
| pedestrian x high_speed_road | 4.1 (3.5–4.6) | 225.4 (200.2–250.7) | 19.39 (16.71–22.49) | 23.80 (20.54–27.57) | 141.4 (116.0–166.8) | 3.1e-14 | 1.23 (1.01–1.49) | 0.04 |
| exceeded_limit x wet | 5.3 (4.6–6.1) | 20.0 (13.1–26.9) | 5.25 (4.38–6.29) | 4.76 (3.37–6.70) | -7.0 (-12.2 to -1.7) | 0.011 | 0.91 (0.68–1.20) | 0.48 |
| exceeded_limit x dark_unlit | 4.1 (3.5–4.8) | 29.6 (23.0–36.2) | 5.97 (4.85–7.36) | 4.03 (3.12–5.20) | 1.7 (-5.4 to 8.9) | 0.62 | 0.67 (0.51–0.89) | 0.0064 |
| exceeded_limit x high_speed_road | 4.1 (3.5–4.7) | 34.4 (26.6–42.2) | 6.32 (5.28–7.56) | 3.86 (3.01–4.94) | 3.8 (-3.6 to 11.1) | 0.31 | 0.61 (0.48–0.77) | 0.00012 |

* **Pedestrian crashes on 50+ mph roads** have the largest additive excess of any pair,
  141 (116–167) per 1,000, with a
  standardised fatal risk of 225 (200–251)
  per 1,000. On the ratio scale the combination is
  1.23 (1.01–1.49): the speed
  environment multiplies pedestrian risk by a somewhat larger factor than other risks
  (exploratory, unadjusted p 0.04; KA
  1.14 (1.02–1.27)), and from a much higher baseline.
* **Exceeding the limit on wet roads keeps its deficit.** The risk ratio for limit exceedance
  is 4.76 (3.37–6.70) on wet roads and
  5.25 (4.38–6.29) on dry roads. The
  additive interaction (the excess for exceedance on wet roads relative to dry roads) is
  -7.0 (-12.2 to -1.7) per 1,000 fatal crashes
  (unadjusted p 0.011), and for
  fatal-or-serious crashes -26.5 (-44.3 to -8.8) per
  1,000. The ratio-scale estimate, 0.91 (0.68–1.20)
  for fatal crashes (0.78 (0.62–0.98) for KA),
  is imprecise for fatal crashes. The deficit on the additive scale therefore does not depend on
  the mix of speeding types, so the registered speeding × wet pattern is not explained by that
  mix alone; the lower baseline risk on wet roads and the unobserved impact speed remain
  candidate explanations that these data cannot separate.
* **Exceeding the limit on 50+ mph roads**: ratio of RRs
  0.61 (0.48–0.77); below 1
  means the relative excess of exceeding the limit is smaller on roads that are already fast.

## Stability across periods

The same models refitted separately for 2016–2019 and 2020–2024:

**2016–2019**

| Pair | Additive interaction (per 1,000) | Ratio of RRs | Fewest events |
|---|---|---|---|
| speeding x dark_unlit | 0.6 (-1.8 to 3.0) | 0.91 (0.67–1.23) | 210 |
| speeding x wet | -1.5 (-3.4 to 0.5) | 0.86 (0.61–1.22) | 109 |
| speeding x alcohol | 3.3 (-2.4 to 9.1) | 0.76 (0.59–0.98) | 251 |
| alcohol x dark_unlit | 8.1 (3.8–12.4) | 0.95 (0.72–1.24) | 317 |
| high_speed_road x dark_unlit | -1.0 (-2.7 to 0.8) | 0.63 (0.51–0.78) | 405 |
| motorcycle x speeding | 18.4 (6.8–30.0) | 1.05 (0.82–1.34) | 140 |
| motorcycle x alcohol | 59.7 (28.9–90.5) | 0.57 (0.43–0.77) | 124 |
| young_driver x late_night | 0.4 (-2.2 to 3.1) | 1.12 (0.75–1.67) | 101 |
| older_driver x angle | 5.1 (2.6–7.6) | 1.17 (0.92–1.48) | 79 |
| heavy_truck x high_speed_road | 6.4 (3.9–9.0) | 1.29 (1.02–1.63) | 113 |
| rural x dark_unlit | -2.2 (-3.8 to -0.6) | 0.61 (0.48–0.77) | 417 |
| weekend x late_night | -3.3 (-4.8 to -1.8) | 0.58 (0.47–0.73) | 252 |
| pedestrian x dark_unlit | 88.0 (61.2–114.9) | 1.77 (1.44–2.18) | 122 |

**2020–2024**

| Pair | Additive interaction (per 1,000) | Ratio of RRs | Fewest events |
|---|---|---|---|
| speeding x dark_unlit | 2.8 (-0.6 to 6.1) | 0.94 (0.71–1.24) | 377 |
| speeding x wet | -5.2 (-7.6 to -2.7) | 0.61 (0.47–0.78) | 167 |
| speeding x alcohol | 7.5 (1.2–13.9) | 0.80 (0.63–1.01) | 462 |
| alcohol x dark_unlit | 7.6 (2.8–12.4) | 0.92 (0.71–1.19) | 465 |
| high_speed_road x dark_unlit | -1.3 (-3.1 to 0.6) | 0.61 (0.53–0.72) | 602 |
| motorcycle x speeding | 33.0 (18.8–47.2) | 0.94 (0.75–1.17) | 269 |
| motorcycle x alcohol | 57.4 (33.4–81.3) | 0.68 (0.53–0.87) | 195 |
| young_driver x late_night | 1.0 (-0.7 to 2.7) | 1.24 (1.01–1.53) | 161 |
| older_driver x angle | 3.9 (2.1–5.7) | 0.93 (0.77–1.12) | 136 |
| heavy_truck x high_speed_road | 7.1 (3.1–11.1) | 1.21 (0.93–1.58) | 214 |
| rural x dark_unlit | -2.3 (-4.7 to 0.0) | 0.64 (0.51–0.81) | 636 |
| weekend x late_night | -0.8 (-2.3 to 0.7) | 0.84 (0.71–0.99) | 396 |
| pedestrian x dark_unlit | 96.6 (64.2–129.1) | 1.51 (1.24–1.82) | 196 |

Where the two periods' intervals overlap widely, the interaction is stable. Fewer events per
period widen the intervals, so a pair that is significant pooled but not within each period
is not evidence of change.

## Fatal-or-serious (KA) outcome

| Pair | Risk with neither (per 1,000) | Risk with both (per 1,000) | Additive interaction (per 1,000) | Ratio of RRs |
|---|---|---|---|---|
| speeding x dark_unlit | 28.1 (24.9–31.2) | 63.9 (57.2–70.6) | 15.4 (8.7–22.2) | 1.24 (1.05–1.45) |
| speeding x wet | 30.1 (27.0–33.1) | 39.1 (34.7–43.5) | -7.2 (-13.6 to -0.7) | 0.87 (0.75–1.00) |
| speeding x alcohol | 26.8 (23.9–29.6) | 112.4 (96.6–128.2) | 23.0 (12.4–33.7) | 0.97 (0.85–1.10) |
| alcohol x dark_unlit | 27.1 (24.3–29.9) | 105.3 (95.5–115.0) | 28.8 (21.0–36.6) | 1.22 (1.07–1.39) |
| high_speed_road x dark_unlit | 25.6 (22.8–28.3) | 48.1 (40.1–56.2) | -6.7 (-12.0 to -1.4) | 0.77 (0.68–0.86) |
| motorcycle x speeding | 25.8 (23.2–28.5) | 352.1 (318.7–385.6) | 90.3 (60.3–120.3) | 0.90 (0.79–1.02) |
| motorcycle x alcohol | 24.7 (22.3–27.1) | 409.7 (369.9–449.6) | 108.2 (76.1–140.3) | 0.55 (0.50–0.60) |
| young_driver x late_night | 31.1 (27.8–34.4) | 39.5 (34.0–45.0) | 3.5 (-0.9 to 7.9) | 1.14 (1.02–1.28) |
| older_driver x angle | 12.1 (9.9–14.3) | 46.2 (40.8–51.7) | 3.5 (0.6–6.4) | 0.93 (0.86–1.01) |
| heavy_truck x high_speed_road | 27.8 (24.9–30.8) | 62.2 (55.5–68.9) | 18.6 (14.0–23.1) | 1.41 (1.26–1.57) |
| rural x dark_unlit | 27.7 (24.1–31.3) | 39.0 (31.7–46.3) | -9.7 (-17.4 to -1.9) | 0.74 (0.61–0.91) |
| weekend x late_night | 29.0 (25.8–32.1) | 42.7 (38.7–46.6) | -2.3 (-4.9 to 0.3) | 0.91 (0.85–0.97) |
| pedestrian x dark_unlit | 28.7 (25.8–31.5) | 448.6 (420.0–477.1) | 159.7 (127.6–191.8) | 1.38 (1.24–1.55) |

## Three-factor combinations

These are estimated only when the fully exposed cell contains at least 20 fatal crashes.

| Combination | Fatal crashes with all three | Risk with none (per 1,000) | Risk with all three (per 1,000) | RR, all three vs none | Three-way additive contrast (per 1,000) | Excess over sum of single excesses (per 1,000) |
|---|---|---|---|---|---|---|
| speeding x alcohol x dark_unlit | 252 | 3.3 (2.8–3.9) | 37.2 (26.9–47.4) | 11.1 (7.8–15.8) | -0.9 (-11.4 to 9.7) | 16.1 (5.6–26.5) |
| motorcycle x speeding x alcohol | 95 | 3.5 (3.0–4.0) | 148.9 (110.4–187.4) | 42.4 (31.0–58.1) | 4.2 (-42.3 to 50.8) | 98.6 (59.9–137.2) |
| speeding x high_speed_road x dark_unlit | 316 | 3.0 (2.5–3.5) | 17.7 (14.8–20.6) | 5.9 (4.7–7.5) | 4.0 (0.5–7.4) | 0.0 (-3.7 to 3.7) |

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
