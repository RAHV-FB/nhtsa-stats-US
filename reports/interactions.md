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
   targeting.
3. **Multiplicative interaction**: whether the risk ratio of A differs when B is present,
   reported as RR11 / (RR10 × RR01).

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
| speeding x dark_unlit | 4.1 (3.5–4.8) | 12.6 (10.4–14.9) | 1.86 (1.50–2.32) | 1.74 (1.40–2.17) | 1.8 (-0.7 to 4.3) | 0.44 | 0.94 (0.73–1.20) | 1 | 1.34 | 587 |
| speeding x wet | 5.3 (4.6–6.1) | 5.7 (4.8–6.6) | 1.92 (1.57–2.35) | 1.33 (1.09–1.63) | -3.5 (-5.2 to -1.8) | 0.0012 | 0.70 (0.56–0.86) | 0.013 | 1.74 | 276 |
| speeding x alcohol | 4.1 (3.5–4.7) | 28.2 (22.5–33.8) | 1.98 (1.62–2.42) | 1.54 (1.23–1.93) | 5.9 (0.8–10.9) | 0.094 | 0.78 (0.64–0.94) | 0.079 | 1.67 | 713 |
| alcohol x dark_unlit | 3.8 (3.3–4.3) | 27.6 (22.9–32.4) | 4.35 (3.64–5.20) | 4.09 (3.30–5.06) | 8.1 (4.9–11.3) | 7e-05 | 0.94 (0.78–1.13) | 1 | 2.78 | 782 |
| high_speed_road x dark_unlit | 3.7 (3.2–4.2) | 12.2 (10.1–14.3) | 2.35 (2.02–2.73) | 1.45 (1.25–1.68) | -1.2 (-2.7 to 0.4) | 0.44 | 0.62 (0.53–0.72) | 1.1e-06 | 1.82 | 1,007 |
| motorcycle x speeding | 4.4 (3.8–5.1) | 69.9 (59.7–80.0) | 8.67 (7.79–9.66) | 8.64 (7.25–10.29) | 27.6 (17.4–37.9) | 2.5e-05 | 1.00 (0.85–1.17) | 1 | 1.53 | 409 |
| motorcycle x alcohol | 4.0 (3.5–4.5) | 111.8 (88.4–135.2) | 9.81 (8.58–11.20) | 6.21 (5.21–7.40) | 58.7 (36.7–80.7) | 3e-05 | 0.63 (0.51–0.79) | 0.0018 | 1.42 | 319 |
| young_driver x late_night | 5.2 (4.5–5.9) | 8.1 (6.4–9.7) | 0.83 (0.75–0.91) | 0.99 (0.82–1.19) | 0.8 (-0.8 to 2.3) | 0.44 | 1.19 (0.97–1.46) | 0.45 | 0.82 | 270 |
| older_driver x angle | 1.1 (0.9–1.3) | 12.2 (10.0–14.3) | 1.72 (1.57–1.89) | 1.74 (1.52–1.99) | 4.4 (2.9–5.9) | 6.9e-06 | 1.01 (0.88–1.17) | 1 | 1.18 | 215 |
| heavy_truck x high_speed_road | 4.7 (4.0–5.3) | 19.2 (15.8–22.7) | 1.66 (1.43–1.93) | 2.07 (1.80–2.38) | 6.8 (4.0–9.7) | 0.00014 | 1.24 (1.02–1.51) | 0.18 | 1.50 | 327 |
| rural x dark_unlit | 3.9 (3.3–4.6) | 8.8 (7.3–10.3) | 1.66 (1.41–1.96) | 1.04 (0.83–1.30) | -2.3 (-4.0 to -0.6) | 0.052 | 0.62 (0.51–0.77) | 0.00034 | 1.65 | 1,053 |
| weekend x late_night | 4.7 (4.1–5.4) | 7.9 (6.8–8.9) | 1.25 (1.17–1.34) | 0.91 (0.80–1.02) | -2.0 (-3.1 to -0.9) | 0.003 | 0.72 (0.63–0.83) | 0.00016 | 1.53 | 648 |
| pedestrian x dark_unlit | 5.0 (4.3–5.7) | 179.2 (149.7–208.8) | 16.91 (13.58–21.04) | 27.30 (22.31–33.42) | 93.6 (70.1–117.1) | 6.7e-09 | 1.62 (1.39–1.88) | 1.8e-06 | 1.45 | 318 |

Figure: `outputs/figures/figures/interactions.png`.

### What the pattern shows

**Pedestrian crashes in unlit darkness show amplification on both scales.**
The standardised risk that a crash is fatal when it is a pedestrian crash in unlit darkness is
179 (150–209) per 1,000, against
5.0 (4.3–5.7) for a
non-pedestrian crash in daylight. The pedestrian risk ratio is
16.9 (13.6–21.0) in daylight and
27.3 (22.3–33.4) in unlit darkness:
a ratio of risk ratios of 1.62 (1.39–1.88)
(Holm p 1.8e-06). The
additive excess is 94 (70–117) fatal
crashes per 1,000 (Holm p 6.7e-09).

**Motorcycle crashes involving alcohol: a large additive excess.** The ratio of risk ratios is
0.63 (0.51–0.79), but the additive
excess is 59 (37–81) per 1,000
(Holm p 3e-05), giving a
standardised fatal risk of 112 (88–135)
per 1,000. The two scales answer different questions: on the ratio scale alcohol raises the
risk of a motorcycle crash by no more than it raises other crashes' risk, but because
motorcycle crashes start from a much higher baseline, that same factor adds far more deaths.
A model that is "only multiplicative" would understate how many deaths concentrate in this
combination.

**Heavy trucks on 50+ mph roads.** The additive excess is
6.8 (4.0–9.7) per 1,000
(Holm p 0.00014). The ratio
of risk ratios is 1.24 (1.02–1.51)
(Holm p 0.18).
The multiplicative excess counts as supported only if its Holm-adjusted p-value is small; the
pattern would be consistent with mass incompatibility growing with speed.

**Several commonly assumed amplifiers are not supported.** Speeding in unlit darkness
(ratio of RRs 0.94 (0.73–1.20)) and a
young driver late at night
(1.19 (0.97–1.46)) show no excess on
the ratio scale. Rural area × unlit darkness
(0.62 (0.51–0.77)), weekend × late night
(0.72 (0.63–0.83)) and 50+ mph road ×
unlit darkness (0.62 (0.53–0.72))
have ratios of risk ratios below 1. Each factor matters on its own, but the combination is not
more severe than the separate factors imply.

**Speeding on wet roads is less severe than expected.** The additive interaction is
-3.5 (-5.2 to -1.8) per 1,000. Police
"speeding-related" is mostly "too fast for conditions", which concentrates on wet and icy roads
and carries no excess severity (`reports/findings.md`, finding 3), so the pair mixes two
different exposures. The exploratory analysis below separates drivers who exceeded the limit.

## Exploratory pairs (not in the registered family)

Two pairs were added when the analysis was implemented (speeding × 50+ mph road, pedestrian ×
50+ mph road), and three after the speeding-type analysis (drivers who exceeded the limit).
They are outside the Holm family and are hypothesis-generating; p-values are unadjusted.

| Pair | Risk with neither (per 1,000) | Risk with both (per 1,000) | RR of A when B absent | RR of A when B present | Additive interaction (per 1,000) | p, additive | Ratio of RRs | p, multiplicative |
|---|---|---|---|---|---|---|---|---|
| speeding x high_speed_road | 3.9 (3.3–4.6) | 11.8 (10.4–13.1) | 2.48 (1.98–3.10) | 1.27 (1.08–1.49) | -3.4 (-4.8 to -2.0) | 2e-05 | 0.51 (0.44–0.60) | 6.1e-11 |
| pedestrian x high_speed_road | 4.2 (3.6–4.8) | 221.1 (190.6–251.5) | 18.35 (14.34–23.48) | 22.54 (18.43–27.56) | 138.1 (113.0–163.2) | 4.5e-14 | 1.23 (1.01–1.50) | 0.043 |
| exceeded_limit x wet | 5.4 (4.6–6.1) | 20.0 (13.1–26.9) | 5.26 (4.39–6.32) | 4.75 (3.37–6.69) | -7.1 (-12.3 to -1.8) | 0.0093 | 0.90 (0.68–1.20) | 0.47 |
| exceeded_limit x dark_unlit | 4.1 (3.5–4.8) | 29.8 (23.1–36.5) | 5.98 (4.85–7.37) | 4.04 (3.13–5.21) | 1.8 (-5.4 to 9.0) | 0.61 | 0.68 (0.51–0.89) | 0.0064 |
| exceeded_limit x high_speed_road | 4.1 (3.5–4.7) | 34.6 (26.6–42.6) | 6.33 (5.29–7.58) | 3.86 (3.01–4.96) | 3.7 (-3.8 to 11.1) | 0.33 | 0.61 (0.48–0.77) | 0.00012 |

* **Pedestrian crashes on 50+ mph roads** have the largest additive excess of any pair,
  138 (113–163) per 1,000, with a
  standardised fatal risk of 221 (191–252)
  per 1,000. On the ratio scale the combination is
  1.23 (1.01–1.50): the speed
  environment multiplies pedestrian risk by roughly the factor it multiplies other risks, but
  from a much higher baseline.
* **Exceeding the limit on wet roads.** On the ratio scale, the risk ratio for limit
  exceedance on wet roads (4.75 (3.37–6.69))
  is compared with that on dry roads (5.26 (4.39–6.32)).
  On the additive scale the excess on wet roads is
  -7.1 (-12.3 to -1.8) per 1,000; crashes on wet
  roads start from a lower baseline. The apparently protective speeding × wet pattern therefore
  reflects the mix of speeding types and the lower wet-road baseline, not a lower danger of
  exceeding the limit in the wet.
* **Exceeding the limit on 50+ mph roads**: ratio of RRs
  0.61 (0.48–0.77); below 1
  means the relative excess of exceeding the limit is smaller on roads that are already fast.

## Stability across periods

The same models refitted separately for 2016–2019 and 2020–2024:

**2016–2019**

| Pair | Additive interaction (per 1,000) | Ratio of RRs | Fewest events |
|---|---|---|---|
| speeding x dark_unlit | 0.7 (-1.7 to 3.1) | 0.92 (0.68–1.24) | 210 |
| speeding x wet | -1.5 (-3.4 to 0.4) | 0.86 (0.61–1.21) | 109 |
| speeding x alcohol | 3.4 (-2.3 to 9.2) | 0.76 (0.59–0.98) | 251 |
| alcohol x dark_unlit | 8.3 (4.0–12.7) | 0.95 (0.72–1.24) | 317 |
| high_speed_road x dark_unlit | -1.0 (-2.8 to 0.7) | 0.63 (0.50–0.78) | 405 |
| motorcycle x speeding | 19.3 (7.7–30.9) | 1.06 (0.83–1.35) | 140 |
| motorcycle x alcohol | 60.4 (29.0–91.7) | 0.57 (0.43–0.77) | 124 |
| young_driver x late_night | 0.5 (-2.2 to 3.1) | 1.12 (0.75–1.68) | 101 |
| older_driver x angle | 5.1 (2.6–7.6) | 1.16 (0.92–1.47) | 79 |
| heavy_truck x high_speed_road | 6.4 (3.9–9.0) | 1.29 (1.02–1.63) | 113 |
| rural x dark_unlit | -2.2 (-3.8 to -0.6) | 0.61 (0.48–0.77) | 417 |
| weekend x late_night | -3.3 (-4.7 to -1.8) | 0.59 (0.47–0.73) | 252 |
| pedestrian x dark_unlit | 89.3 (54.5–124.0) | 1.76 (1.43–2.17) | 122 |

**2020–2024**

| Pair | Additive interaction (per 1,000) | Ratio of RRs | Fewest events |
|---|---|---|---|
| speeding x dark_unlit | 2.8 (-0.6 to 6.2) | 0.94 (0.71–1.24) | 377 |
| speeding x wet | -5.2 (-7.6 to -2.8) | 0.61 (0.47–0.78) | 167 |
| speeding x alcohol | 7.6 (1.2–14.0) | 0.80 (0.63–1.01) | 462 |
| alcohol x dark_unlit | 7.6 (2.8–12.4) | 0.92 (0.71–1.19) | 465 |
| high_speed_road x dark_unlit | -1.3 (-3.2 to 0.5) | 0.61 (0.52–0.72) | 602 |
| motorcycle x speeding | 33.9 (19.1–48.6) | 0.95 (0.76–1.18) | 269 |
| motorcycle x alcohol | 58.5 (33.5–83.4) | 0.68 (0.53–0.88) | 195 |
| young_driver x late_night | 1.0 (-0.7 to 2.7) | 1.24 (1.01–1.52) | 161 |
| older_driver x angle | 3.9 (2.1–5.7) | 0.93 (0.77–1.12) | 136 |
| heavy_truck x high_speed_road | 7.1 (3.1–11.2) | 1.22 (0.93–1.58) | 214 |
| rural x dark_unlit | -2.4 (-4.7 to 0.0) | 0.64 (0.51–0.81) | 636 |
| weekend x late_night | -0.8 (-2.3 to 0.6) | 0.84 (0.71–0.99) | 396 |
| pedestrian x dark_unlit | 95.5 (61.4–129.5) | 1.50 (1.24–1.82) | 196 |

Where the two periods' intervals overlap widely, the interaction is stable. Fewer events per
period widen the intervals, so a pair that is significant pooled but not within each period
is not evidence of change.

## Fatal-or-serious (KA) outcome

| Pair | Risk with neither (per 1,000) | Risk with both (per 1,000) | Additive interaction (per 1,000) | Ratio of RRs |
|---|---|---|---|---|
| speeding x dark_unlit | 28.1 (24.9–31.2) | 63.9 (57.2–70.6) | 15.5 (8.7–22.2) | 1.24 (1.05–1.45) |
| speeding x wet | 30.1 (27.1–33.1) | 39.1 (34.8–43.5) | -7.1 (-13.5 to -0.7) | 0.87 (0.76–1.00) |
| speeding x alcohol | 26.8 (24.0–29.6) | 112.4 (96.6–128.3) | 23.1 (12.5–33.7) | 0.97 (0.85–1.10) |
| alcohol x dark_unlit | 27.1 (24.3–29.9) | 105.3 (95.5–115.0) | 28.7 (20.9–36.5) | 1.22 (1.07–1.39) |
| high_speed_road x dark_unlit | 25.6 (22.8–28.4) | 48.2 (40.2–56.2) | -6.7 (-12.0 to -1.4) | 0.77 (0.68–0.86) |
| motorcycle x speeding | 25.8 (23.2–28.5) | 352.1 (318.6–385.6) | 90.3 (60.3–120.4) | 0.90 (0.79–1.02) |
| motorcycle x alcohol | 24.7 (22.3–27.1) | 409.7 (369.8–449.5) | 108.2 (76.1–140.3) | 0.55 (0.50–0.60) |
| young_driver x late_night | 31.1 (27.8–34.4) | 39.5 (34.0–45.0) | 3.5 (-0.9 to 8.0) | 1.14 (1.02–1.28) |
| older_driver x angle | 12.1 (9.9–14.3) | 46.2 (40.8–51.7) | 3.5 (0.6–6.4) | 0.93 (0.86–1.01) |
| heavy_truck x high_speed_road | 27.9 (24.9–30.8) | 62.2 (55.5–68.9) | 18.6 (14.0–23.1) | 1.41 (1.26–1.57) |
| rural x dark_unlit | 27.7 (24.1–31.3) | 39.0 (31.8–46.3) | -9.7 (-17.5 to -2.0) | 0.74 (0.61–0.91) |
| weekend x late_night | 29.0 (25.9–32.2) | 42.7 (38.7–46.6) | -2.3 (-4.9 to 0.3) | 0.91 (0.85–0.97) |
| pedestrian x dark_unlit | 29.0 (26.3–31.8) | 469.4 (425.4–513.5) | 162.2 (127.7–196.7) | 1.36 (1.22–1.52) |

## Three-factor combinations

These are estimated only when the fully exposed cell contains at least 20 fatal crashes.

| Combination | Fatal crashes with all three | Risk with none (per 1,000) | Risk with all three (per 1,000) | RR, all three vs none | Three-way additive contrast (per 1,000) | Excess over sum of single excesses (per 1,000) |
|---|---|---|---|---|---|---|
| speeding x alcohol x dark_unlit | 252 | 3.4 (2.8–3.9) | 37.6 (27.1–48.1) | 11.2 (7.9–15.9) | -0.7 (-11.4 to 10.0) | 16.4 (5.8–27.0) |
| motorcycle x speeding x alcohol | 95 | 3.5 (3.0–4.0) | 152.9 (111.0–194.8) | 43.4 (31.4–60.1) | 6.9 (-41.5 to 55.3) | 102.2 (60.2–144.1) |
| speeding x high_speed_road x dark_unlit | 316 | 3.0 (2.5–3.5) | 17.8 (14.9–20.7) | 5.9 (4.6–7.5) | 3.9 (0.3–7.4) | 0.0 (-3.7 to 3.7) |

## What these results do and do not justify

* **Justified:** "Among police-reported crashes, the excess fatality risk of a pedestrian crash
  is larger in unlit darkness, beyond the separate excesses, after adjusting for the recorded
  circumstances."
* **Not justified:** that darkness *causes* additional pedestrian deaths by a given amount
  (crash occurrence, exposure and unrecorded factors such as impact speed are not observed),
  or that two factors which co-occur in fatal crashes interact.
* Behavioural factors (speeding, alcohol) are recorded more thoroughly in severe crashes
  (`reports/findings.md`, finding 9). This can create or exaggerate apparent interactions
  involving them. Interactions among objectively recorded circumstances (light, speed limit,
  crash type, vehicle type) are the most trustworthy.
