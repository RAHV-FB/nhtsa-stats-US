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
The 15 pairs were specified in advance (`docs/research_plan.md`, RQ2), with the rationale for
each recorded in the output table. p-values are Holm-adjusted across these 15 pairs, separately
for each scale. Confidence intervals are design-based (Taylor linearisation, 42 df).

## Results: pre-specified pairs, fatal outcome

{{mdtable:interactions/pairs_fatal|prespecified=True|pair:Pair (A x B):;adj_p00:Risk with neither (per 1,000):cix1000:1;adj_p11:Risk with both (per 1,000):cix1000:1;rr_A_given_B0:RR of A when B absent:ci:2;rr_A_given_B1:RR of A when B present:ci:2;ic:Additive interaction (per 1,000):cix1000:1;ic_p_holm:Holm p, additive:.2g;ratio_of_rr:Ratio of RRs (multiplicative):ci:2;ratio_of_rr_p_holm:Holm p, multiplicative:.2g;obs_exp_all:Co-occurrence O/E, all crashes:.2f;min_cell_events:Fewest events in a cell:,.0f}}

Figure: `outputs/figures/figures/interactions.png`.

### What the pattern shows

**Pedestrian crashes in unlit darkness show the clearest amplification on both scales.**
The adjusted risk that a pedestrian crash in dark, unlit conditions is fatal is
{{interactions/pairs_fatal|pair=pedestrian x dark_unlit|adj_p11|cix1000:0}} per 1,000. The
corresponding risk for a non-pedestrian crash in daylight is
{{interactions/pairs_fatal|pair=pedestrian x dark_unlit|adj_p00|cix1000:1}}. The pedestrian
risk ratio is {{interactions/pairs_fatal|pair=pedestrian x dark_unlit|rr_A_given_B0|ci:1}} in
daylight and {{interactions/pairs_fatal|pair=pedestrian x dark_unlit|rr_A_given_B1|ci:1}} in
unlit darkness: a ratio of risk ratios of
{{interactions/pairs_fatal|pair=pedestrian x dark_unlit|ratio_of_rr|ci:2}}. The additive
excess is {{interactions/pairs_fatal|pair=pedestrian x dark_unlit|ic|cix1000:0}} fatal crashes
per 1,000 such crashes.

**Pedestrian crashes on roads with limits of 50 mph or more carry the largest additive
excess.** The excess is {{interactions/pairs_fatal|pair=pedestrian x high_speed_road|ic|cix1000:0}}
per 1,000, and the adjusted fatal risk is
{{interactions/pairs_fatal|pair=pedestrian x high_speed_road|adj_p11|cix1000:0}} per 1,000. On
the ratio scale, however, the two act roughly multiplicatively
({{interactions/pairs_fatal|pair=pedestrian x high_speed_road|ratio_of_rr|ci:2}}). The two
scales answer different questions. The multiplicative scale says the speed environment raises
pedestrian risk by about the same factor as it raises other risks. The additive scale says
that, because pedestrian crashes start from a much higher baseline, that same factor produces
far more deaths.

**Motorcycle crashes involving alcohol are sub-multiplicative but have a large additive
excess.** The ratio of risk ratios is
{{interactions/pairs_fatal|pair=motorcycle x alcohol|ratio_of_rr|ci:2}}, but the additive
excess is {{interactions/pairs_fatal|pair=motorcycle x alcohol|ic|cix1000:0}} per 1,000. This
gives an adjusted fatal risk of
{{interactions/pairs_fatal|pair=motorcycle x alcohol|adj_p11|cix1000:0}} per 1,000 crashes. A
model that is "only multiplicative" would understate how many deaths concentrate in this
combination.

**Heavy trucks on high-speed roads** are super-multiplicative
({{interactions/pairs_fatal|pair=heavy_truck x high_speed_road|ratio_of_rr|ci:2}}), with an
additive excess of {{interactions/pairs_fatal|pair=heavy_truck x high_speed_road|ic|cix1000:1}}
per 1,000, which is consistent with mass incompatibility rising with speed.

**Several apparent "amplifiers" are not.** Speeding in unlit darkness
(ratio of RRs {{interactions/pairs_fatal|pair=speeding x dark_unlit|ratio_of_rr|ci:2}}) and a
young driver late at night
({{interactions/pairs_fatal|pair=young_driver x late_night|ratio_of_rr|ci:2}}) combine roughly
multiplicatively. Rural area × unlit darkness, weekend × late night and 50+ mph road × unlit
darkness are *sub*-multiplicative. Each factor matters, but their combination is not
especially severe beyond what the separate factors imply.

**Speeding on wet roads and on high-speed roads is less severe than expected — and the
reason is measurement.** Both pairs show a negative additive interaction
({{interactions/pairs_fatal|pair=speeding x wet|ic|cix1000:1}} and
{{interactions/pairs_fatal|pair=speeding x high_speed_road|ic|cix1000:1}} per 1,000). The
explanation is that police "speeding-related" is mostly "too fast for conditions", which
concentrates on wet and icy roads and carries no excess severity (`reports/findings.md`,
finding 3). The exploratory follow-up below isolates drivers who exceeded the limit.

## Follow-up (exploratory, not pre-specified): exceeding the limit

These pairs were added after the speeding-type analysis. They are not part of the Holm family
and should be read as hypothesis-generating.

{{mdtable:interactions/pairs_fatal|prespecified=False|pair:Pair:;adj_p00:Risk with neither (per 1,000):cix1000:1;adj_p11:Risk with both (per 1,000):cix1000:1;rr_A_given_B0:RR of A when B absent:ci:2;rr_A_given_B1:RR of A when B present:ci:2;ic:Additive interaction (per 1,000):cix1000:1;ratio_of_rr:Ratio of RRs:ci:2}}

For limit exceedance, the risk ratio on wet roads
({{interactions/pairs_fatal|pair=exceeded_limit x wet|rr_A_given_B1|ci:2}}) is close to that on
dry roads ({{interactions/pairs_fatal|pair=exceeded_limit x wet|rr_A_given_B0|ci:2}}). The
apparent protective interaction of speeding with wet roads therefore reflects the *mix* of
speeding types, not a lower danger of exceeding the limit in the wet.

## Stability across periods

The same models refitted separately for 2016–2019 and 2020–2024:

**2016–2019**

{{mdtable:interactions/pairs_fatal_by_period|period=2016-2019;prespecified=True|pair:Pair:;ic:Additive interaction (per 1,000):cix1000:1;ratio_of_rr:Ratio of RRs:ci:2;min_cell_events:Fewest events:,.0f}}

**2020–2024**

{{mdtable:interactions/pairs_fatal_by_period|period=2020-2024;prespecified=True|pair:Pair:;ic:Additive interaction (per 1,000):cix1000:1;ratio_of_rr:Ratio of RRs:ci:2;min_cell_events:Fewest events:,.0f}}

Where the two periods' intervals overlap widely, the interaction is stable. Fewer events per
period widen the intervals, so a pair that is significant pooled but not within each period
is not evidence of change.

## Fatal-or-serious (KA) outcome

{{mdtable:interactions/pairs_ka|prespecified=True|pair:Pair:;adj_p00:Risk with neither (per 1,000):cix1000:1;adj_p11:Risk with both (per 1,000):cix1000:1;ic:Additive interaction (per 1,000):cix1000:1;ratio_of_rr:Ratio of RRs:ci:2}}

## Three-factor combinations

These are estimated only when the fully exposed cell contains at least 20 fatal crashes.

{{mdtable:interactions/triples_fatal|outcome=fatal|combination:Combination:;p111_n_events:Fatal crashes with all three:,.0f;adj_p000:Risk with none (per 1,000):cix1000:1;adj_p111:Risk with all three (per 1,000):cix1000:1;rr_p111:RR, all three vs none:ci:1;ic3:Three-way additive contrast (per 1,000):cix1000:1;excess_over_additive_singles:Excess over sum of single excesses (per 1,000):cix1000:1}}

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
