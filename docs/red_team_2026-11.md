# Red-team review, November 2026

The owner asked for independent subagents to attack the project's road-safety research. They
looked for data leakage, biases, missing uncertainty, broken model assumptions, misused
significance and irreproducible numbers, and a separate subagent tried to disprove each major
published finding. This record says how that was done, what held up, what did not, and which
corrections are recommended.

The review itself changed no analysis code, output table, report, website page or documented
limitation. Every recommended correction is listed in §5, with its status after a later pass that
applied them. Where
a correction needs a new number in `reports/`, that number has to come from a new output table
through the templates (CLAUDE.md). The reviewers' scripts show how to compute it.

## 1. How the review was run

* **Data.** The 36 archives were fetched from Git LFS. The Parquet cache and analytic datasets
  were rebuilt with `nhtsa ingest` (91 s) and `nhtsa features` (15 s), so every reviewer worked
  on the same datasets the project uses.
* **Reviewers.** There were 37 reviewers, all of whom reported.
  * Six attacked the whole project along one dimension each: X1 data leakage, X2 biases,
    X3 uncertainty, X4 model assumptions, X5 statistical significance and X6 reproducibility.
  * Twenty-seven attacked one published finding each: F01–F11 from `reports/findings.md`,
    P01–P07 from the Phase-2 reports, and W01–W09 from the public website and
    `reports/road_deaths.md`.
  * A coverage critic found four more major published claims that the register had missed. Each
    got its own attacker (G01–G04).
* **Independence.** Each reviewer started from a fresh context. It received only its target
  claim, the claim's sources and a set of common rules:
  * the repository is read-only;
  * every number must come from a script the reviewer ran, or from a committed table;
  * verdicts are REFUTED, WEAKENED, SURVIVES or NOT TESTABLE.

  No reviewer saw another reviewer's work or any hypothesis from the coordinator. The briefs are
  preserved in Git history at commit 7ee597e.
* **Verification.** A damaging claim was not taken on trust. Fifteen independent verifiers
  re-checked them in three ways: they re-ran the attacker's scripts, they checked what the
  published text actually says, and they tried to refute the attacker's inference. The
  coordinator also checked claims directly against committed tables and code, and re-ran some
  scripts. Each issue below carries one of these labels:
  * **re-run**: the script was re-run with identical output, or the number was recomputed
    independently;
  * **table/code**: checked against a committed table or the code;
  * **two reviewers**: two reviewers found the same number independently;
  * **attacker only**: not independently checked before the time box.
* **Models and compute.** Reviewers and verifiers used the `sonnet` tier, as CLAUDE.md requires
  for coding and checking. One `opus` fresh-context review ran before the push. All data work went
  through a shared throttle of four single-threaded jobs with a memory cap.
* **Time box.** At the owner's request the review was closed once every reviewer had returned.
  The late reviewers were asked to stop and report what they had, so several of their attacks
  are marked "not tested" in their own reports.

## 2. Verdicts at a glance

No published finding was refuted. Of the 31 findings attacked, 10 survived (some with wording
fixes) and 21 were weakened. The weakening almost always concerned magnitude, certainty or
wording, not direction. All six dimension reviewers rated the project as having minor issues;
X2 rated it as bordering on material.

| ID | Published finding | Attacker | Checked | Main issue |
|---|---|---|---|---|
| F01 | Frequency is not danger (pedestrian ×15.6) | WEAKENED | two reviewers; the verifier rated it SURVIVES with a wording fix | The ×12.8 for exceeding the limit mixes FARS and CRSS recording. Within CRSS it is ×8.6. |
| F02 | Adjustment reshapes the picture | WEAKENED | re-run (part) | The interstate 0.70 comes from 50–65 mph roads; it is 1.00 at 70+ mph. "No less severe" for rain is not shown. |
| F03 | "Speeding" is two things | WEAKENED | table/code (part) | The null for "too fast for conditions" is only bounded to about ±22%. It is exploratory but unlabelled in the README and on the site. |
| F04 | Most robust associations | WEAKENED | attacker only; two reviewers on one number | "As severe as" rests on a null. The pedestrian speed RR depends on adjusting for location, light and time. |
| F05 | Some combinations amplify | WEAKENED (minor) | table/code | The text says speeding × wet "reflects" the speeding-type mix. Exceeding the limit on wet roads keeps its deficit. |
| F06 | Involvement is not severity | SURVIVES | re-run | "Less severe even after adjustment" holds only for model A. |
| F07 | Within-vehicle belt effect, 65.8% | SURVIVES | re-run; two reviewers | The misreporting scenarios are one-sided and pooled. In angle crashes the effect vanishes at about 10% misreporting. |
| F08 | Post-2020 rise only partly the mix | WEAKENED | re-run | The composition share is about 25–56%, not 28–49%. The complete-case denominator share (46%) is not reported. |
| F09 | Measurement differs by severity | WEAKENED | table/code and re-run | "Recorded more completely in severe crashes" is misleading: CRSS fatal crashes have more unknowns. |
| F10 | Burden and interventions | WEAKENED | re-run | "The alcohol fraction does not [shrink]" is wrong on the project's own grid. The attributable fractions depend on period and coding. |
| F11 | Prediction models | WEAKENED (wording) | re-run, table/code | "Inputs exclude anything recorded after the crash … leakage gate" is false as written. |
| P01 | Factor counts overlap (109%, 65%) | WEAKENED | re-run | The 65% union and ~70% are floors. Undetermined drug status is scored as negative. |
| P02 | Alcohol does not explain away speeding | SURVIVES | re-run | "6.5 vs 3.3" leaves crash configuration out; with it the figures are 5.4 vs 3.7. |
| P03 | The unit matters | WEAKENED | attacker only | Unit-specific RRs use different adjustment sets. Under a common specification the driver RR is 6.2, not 2.7. |
| P04 | Drugs cannot be ranked | WEAKENED | attacker only | The two "same population" ORs are on different drivers. The 1.7–73 bounds are extreme corners. |
| P05 | Belts act at a different stage | WEAKENED | re-run | The "unchanged by speeding" result is a composition effect. Within crash configuration the ratio is 1.16 (1.06–1.26). |
| P06 | No defensible single ranking | WEAKENED | table/code (part) | P ≈ 0.97 covers sampling error only. The order flips if non-fatal exceedance is under-recorded by about 21%. |
| P07 | No individual attribution | SURVIVES | attacker only; two reviewers on the text error | The alcohol figure 1.41 is read as "no change" but is just imprecise. Typo in "96 cases in the main model". |
| W01 | 59.6% of deaths involve one of four behaviours | SURVIVES | re-run | 46% of these deaths involve only another driver's alcohol or speeding. |
| W02 | 39% of drunk-driving deaths were not the drunk driver | WEAKENED | two reviewers | The 39% is 27.4% with measured BAC only. 13 percentage points are the drunk driver's own passengers. |
| W03 | Drunk drivers' records (7% prior DWI) | WEAKENED | two reviewers | The prior-DWI share is 9.5% among drivers with a measured BAC. 40.5% of the group is imputed. |
| W04 | 48.6% unbelted; up to ~6,900 lives/yr | SURVIVES (wording) | attacker only | "Up to" is not a ceiling: deaths with unknown belt use are excluded. About 61% of unbelted deaths have no pair comparison. |
| W05 | Pedestrian deaths concentrated | SURVIVES | attacker only; two reviewers on one point | In CRSS, 29% of struck pedestrians have an unknown speed limit. That missingness depends on the outcome and is not disclosed. |
| W06 | Motorcycles and helmets | WEAKENED | attacker only | The helmet estimate has no misreporting sensitivity and tips at 5.6%. It rests on 455 discordant pairs. |
| W07 | Vehicle age 18+, RR 2.22 | SURVIVES | attacker only | Robust in 12 variants. Selection through crash reporting is untested. |
| W08 | 2019–21 rise steepest in risky driving | SURVIVES (framing) | table/code | Other-vehicle occupant deaths (+37.5%) rose faster than drunk-driving deaths (+33.4%). |
| W09 | States differ sharply | SURVIVES | table/code | Wording only. |
| G01 | Policy conclusions and break-even tables | WEAKENED | attacker only | "Should therefore target limit-exceeding crashes" is a prescription the severity RR cannot carry. |
| G02 | Same quantities across reports | WEAKENED | re-run | The drug-positive counts use two definitions. The "determinate crashes only" label does not match the code. |
| G03 | Model-selection verdict | WEAKENED | re-run (part); the verifier rated it SURVIVES (minor) | "Pre-specified" appears only in a docstring. "Random forest brings nothing" overstates. |
| G04 | Large-truck deaths | WEAKENED (wording) | attacker only | The 85% pools crash types: 55% in single-truck crashes, 97% in truck–car crashes. |

| ID | Dimension | Assessment | Main issue |
|---|---|---|---|
| X1 | Data leakage | MINOR ISSUES | CRSS weights are benchmarked to FARS fatal counts, so CRSS–FARS agreement is partly circular. FARS imputed BAC appears to depend on the driver's injury. |
| X2 | Biases | MINOR, bordering on MATERIAL | Mixed-source ratios. Imputation-dependent drunk-driving shares. One-sided belt misclassification. Outcome-dependent missing speed limits. |
| X3 | Uncertainty | MINOR ISSUES | A delete-one-PSU jackknife matches the published SEs within 1.3%. The imputation variance is unquantified. |
| X4 | Model assumptions | MINOR ISSUES | Effects vary by crash type (p < 0.001). One mutually adjusted model gives total-looking RRs for night and interstate. |
| X5 | Statistical significance | MINOR ISSUES | Exploratory results are unlabelled in the README and on the website. Several null claims go beyond what equivalence supports. |
| X6 | Reproducibility | MINOR ISSUES | Seven modules re-run identically and the reports and site re-render byte-for-byte. 123 sidecars cite a commit that is not in the repository. |

## 3. Issues, most consequential first

Numbers come from the reviewers' scripts (preserved in Git history at commit 7ee597e) or from
committed tables. Each issue carries the label from §1.

### Material

1. **"Recorded more completely in severe crashes" is misleading for CRSS police-recorded fields**
   (F09; table/code and re-run).
   * README 9 and `docs/limitations.md` §2 use the phrase. Yet in `measurement/unknown_by_severity`,
     CRSS fatal crashes have more unknowns than any other severity:

     | Field | Unknown in fatal crashes | Unknown at lower severities |
     |---|---|---|
     | Alcohol | 47.4% | 25–29% |
     | Drugs | 53.0% | 39–42% |
     | Distraction | 62.5% | 41–48% |
     | Speeding | 5.5% | 2.9–3.8% |

   * What is more complete in severe crashes is toxicology testing of killed drivers and speeding
     as recorded by FARS. The verifier judged the wording ambiguous ("more thoroughly
     investigated" can be true at the same time) rather than plainly contradicted.
   * The project's bias analyses assume sensitivity is higher in fatal than non-fatal crashes.
     These data do not test that.
   * The police-versus-BAC contrast (87% for killed drivers vs 98% for surviving drivers) has no
     selection caveat. Survivors are tested on suspicion, and their sensitivity falls from 0.991
     to 0.966 as testing broadens (re-run).

2. **The null for "too fast for conditions" is stronger in the text than in the data** (F03,
   X5; table/code in part).
   * README 3, the website and the policy ledger say "no detectable excess" or "no detectable
     increase". The estimate is 1.06 (0.89–1.26).
   * The 90% interval supports equivalence only within about ±22%.
   * The fatal-or-serious estimate for the same exposure is 1.18 (1.03–1.36).
   * There is no bias analysis for this type of speeding. The QBA grid's blank rows at
     specificity 0.99 are unexplained (cause confirmed: the correction is impossible there).
   * The speeding-type split is exploratory per `findings.md` §14, but the README and website do
     not say so (confirmed).
   * An attacker refit adding crash configuration gave 1.29 (1.13–1.47). That was not verified,
     and configuration is a possible mediator.
   * The exceedance association held in every variant: 3.4–6.2, with every lower limit above 2.9.

3. **The four-factor overlap headline presents floors as measurements** (P01; re-run).
   * "Only 65% of deaths involve any of them", 1.68 counts per death and the ~70% all score the
     63% of deaths with undetermined drug status as drug-negative.
   * The union is 95.4% if undetermined is scored positive, and 87.5% in determinate crashes. The
     three measured factors alone give 58%, with a ratio of 1.47.
   * "At least" is attached only to the drug count. `docs/limitations.md` says nothing about this.

4. **"The belt RR does not change with speeding" is a composition effect** (P05; re-run by the
   coordinator with identical numbers).
   * Speeding drivers are twice as often in single-vehicle crashes (62% vs 30%), where belts look
     more protective.
   * Within crash configuration, the speeding / not-speeding ratio of belt RRs is 1.16
     (1.06–1.26), p = 0.0008. Belts appear somewhat less protective with a speeding driver.
   * The "slightly more protective with a BAC ≥ .08 driver" result disappears within
     configuration: 1.03, p = 0.46.
   * The belt RR is 0.23 in rollovers and 0.43 otherwise. That contradicts "independent of how
     the crash happened".
   * This reverses a published Phase-2 conclusion: within crash configuration, belts are
     somewhat less protective with a speeding driver. It needs a configuration-stratified output
     table before the report text changes.

5. **The attributable fractions are less certain, and less one-sided, than stated** (F10; re-run).
   * The fractions come from a 2016–24 model scaled to 2022–24 deaths. A 2022–24 refit gives
     speeding 11.9% (9.1–14.8), against the published 9.1%. The intervals overlap.
   * "The alcohol fraction does not [shrink]" is contradicted by `burden/bias_sensitivity`. In its
     severe cells alcohol falls to 3–9%, so the word "plausible" carries the claim and is
     undefined.
   * Police-reported alcohol gives 12.7–15.1%, a lower-leaning figure.
   * The intervals cover sampling error only.
   * The attacker's claim that the 9.1% and 8.9% figures are unexplained was wrong:
     `factor_contributions.md` explains them.

6. **Drunk-driving victim and record shares rest on imputed BAC** (W02, W03, X2; two reviewers).
   * Restricted to measured BAC:
     * the share of drunk-driving deaths who were not the drunk driver is 27.4%, not 39.4%;
     * the prior-DWI share of drunk drivers is 9.5%, not 7.4%.
   * 40.5% of the BAC ≥ .08 driver group is imputed.
   * About a third of the "not the drunk driver" deaths are the drunk driver's own passengers,
     and two-thirds of those tested were themselves at .08 or more.
   * Prior-DWI shares range from 1.6% to 20.1% across states.
   * "Seldom had a conviction" survives.

7. **The cross-system ratios mix recording systems** (F01, X2; two reviewers: ×8.60).
   * Within CRSS the exceedance over-representation is ×8.6 (6.5–11.4), against the published
     ×12.8.
   * The verifier pointed out that CRSS under-records speeding in fatal crashes, so ×8.6 is a
     floor, and the honest statement is a range.
   * The published intervals cover only CRSS sampling of the denominator. The report does not
     say so.

8. **Belt and helmet sensitivities are incomplete** (F07, X2, W06; re-run for the belt figures,
   attacker only for helmets).
   * The belt misreporting scenarios move only belted-coded survivors.
   * Adding 5% reverse error among deaths lowers the 10% scenario from 37.9% to 28.2%. Two
     reviewers found this independently.
   * The pooled 65.8% averages very different crash types: 50.9% in angle crashes (vanishing at
     about 10% misreporting) and 84.4% in rollovers.
   * The helmet estimate (31%, 641 lives a year) has no misreporting scenario at all. Its tipping
     point is 5.6%. It rests on 455 discordant pairs. It is applied to all unhelmeted deaths,
     although only 15.7% of them were on two-up motorcycles.

9. **The post-2020 composition range is wider than "28–49%"** (F08; re-run).
   * Reasonable alternatives give about 25–56%: 25% (7–43%) with imputed alcohol and the
     coding-drift variables dropped.
   * A drift variable (surface) is the largest single contributor.
   * The denominator share is 46% (29–64%) under the complete-case outcome. The text gives only
     54%.
   * The within-circumstance rise (×1.08–1.18) survived every variant.

10. **Unit-specific alcohol RRs are not comparable** (P03; attacker only).
    * The driver, passenger and other-vehicle models use different adjustment sets. Under one
      common specification the driver RR is 6.2 (published 2.7) and the passenger RR 8.8
      (published 4.3), and the ordering changes.
    * The pedestrian contrast (much weaker in relative terms) holds under every specification.
      Its risk difference is the largest of any unit.

11. **Drug comparisons** (P04, G02; G02 re-run).
    * "1.23 vs 5.0 in police reports for the same population" compares different driver sets. On
      the same 68,755 killed drivers the figures are 1.44 vs 3.51 (attacker only).
    * The 1.7–73 range comes from the most extreme allocation corners. Non-differential
      allocation gives 7.8–19, and the RR is positive in every scenario.
    * The drug-positive count appears under two definitions about 1.9 times apart (crash-level
      police field vs any-driver toxicology).
    * The label "determinate crashes only" does not describe `contributions.py`. A crash counts
      as positive if any driver is positive, and only 52,039 of the 84,207 deaths are in fully
      determinate crashes (confirmed in code).

12. **The prediction-model leakage sentence is false as written** (F11; re-run, table/code).
    * The `speeding` registry entry is labelled `pre_crash`, but its note says "police judgement
      recorded after the crash". The gate checks only that label.
    * Dropping speeding and imputed alcohol costs 0.016 AUROC.
    * "Pre-specified" for the selection rule rests on a docstring, not on the research plan
      (G03; confirmed).

### Moderate and minor

* **Policy** (G01; attacker only).
  * "Any projection of a camera programme should therefore target limit-exceeding crashes" is a
    prescription that a crash-conditional severity RR cannot carry.
  * The exceedance segment's size depends on unknown and unspecified speeding codes: the 1%
    requirement ranges from 8.7% down to 4.0–5.9%.
  * The drug row's required share is driven by missing data.
* **P02** (re-run). The README's "6.5 vs 3.3" omits crash configuration; with it the figures are
  5.4 vs 3.7. "Every recorded circumstance" omits drugs, distraction and belt use.
* **F02** (re-run in part).
  * The interstate contrast is concentrated on 50–65 mph roads (0.57); at 70+ mph it is 1.00
    (0.67–1.48).
  * Under exposure-specific adjustment the interstate RR becomes 1.37 (X4; that adjustment set
    is the reviewer's own).
  * For rain, the KA estimate is 0.89 (0.82–0.97).
* **F04** (attacker only; the 12.2 confirmed by two reviewers).
  * The 70+ vs 50–55 mph contrast is 0.94 (0.79–1.12) and depends on adjusting for interstate.
  * The pedestrian 50–55 mph RR is 6.6 as published, but 12.2 without location, light and time
    of day.
* **X4** (attacker only). Crash type modifies the effects of speeding, alcohol, motorcycle and
  heavy truck (p < 0.001). Model A is miscalibrated by 10–25% in the middle risk deciles.
* **F06** (re-run). The teen result holds under model A (0.86) but model B gives 0.92
  (0.84–1.01). The 75+ involvement ratio is about 1.1 in rear-end crashes and about 2 in other
  crash types.
* **F05** (table/code). Exceeding the limit on wet roads keeps its deficit: −7.1 per 1,000 for
  fatal crashes, −26.3 for KA.
* **W04** (attacker only).
  * "Up to about 6,900" excludes the 21,003 deaths with unknown belt use. An ejection-based
    imputation gives about 7,500 a year.
  * 60.7% of unbelted deaths are in single-occupant vehicles, where no pair comparison exists.
  * The rear-seat transport is supported: 65.1%.
* **W05, X2** (two reviewers). 29% of struck pedestrians in CRSS have an unknown speed limit,
  29.7% of non-fatal cases against 10.8% of fatal ones. This inflates the absolute fatal shares
  by about 15–25%, but not the RR. The hit-and-run share rose from about 20.5% (2016–19) to about
  25% (2020–24).
* **G04** (attacker only). The 85% of large-truck-crash deaths who were "not the truck driver" is
  55% in single-truck crashes and 97% in truck–passenger-vehicle crashes. The text invites a fault
  reading.
* **W08** (table/code). "Steepest in risky driving" bundles hit-and-run and licence status. The
  invalid-licence rise of +44% is +40.5% without expired or cancelled licences.
* **P06** (table/code in part). P ≈ 0.97 covers sampling error only. "The hypothesised ranking …
  is not supported" conflates untestable with refuted.
* **P07** (two reviewers on the text). The single-case alcohol RR of 1.41 is imprecise; other
  specifications give 1.3–1.9. `case_comparisons.md` says "96 cases in the main model", but there
  are 48 in each model.
* **X1** (attacker only).
  * CRSS weights reproduce FARS fatal totals by calibration (99.1–100% each year), so CRSS–FARS
    agreement is partly by construction.
  * Swapping imputed for police-reported alcohol does not inflate the alcohol RR (4.24 vs 5.21).
  * Among untested FARS drivers, imputed BAC is higher for killed drivers (adjusted OR 1.62).
    That suggests the imputation uses injury.
* **X5** (verified in part). RQ5 is listed as pre-specified although the plan's change log says it
  was added after the results. Only the registered families are multiplicity-adjusted.
* **X6** (attacker only).
  * 123 provenance sidecars record commit `ef704fd`, which is not in the repository.
  * `deaths` silently skips `potential_lives` when the matched tables are missing.
  * The environment has no pinned Python version.

## 4. What held up

* **Reproduction.** Every attacked headline number reproduced exactly from the processed data or
  raw interim tables. X6 re-ran seven modules: all 45 tables were identical, and all nine reports
  and the website re-rendered byte-for-byte from the committed tables. 72 data-dependent tests
  passed.
* **Uncertainty.** X3 refitted with a stratified delete-one-PSU jackknife. It agrees with the
  published linearised SEs within 1.3%, so the design-based intervals are not anti-conservative.
  The 42 df, t quantiles and Wald F are used correctly (X5).
* **Directions.** No direction reversed under any attack:
  * exceeding the limit is strongly associated with a fatal crash;
  * alcohol explains only a minority of that association;
  * pedestrians in unlit darkness amplify on both scales (ratio of RRs 1.62–1.85 across six
    definitions);
  * belted front-seat occupants die less often than unbelted ones in the same vehicle, in every
    stratum;
  * teen and 75+ drivers are over-involved as the culpable party;
  * fatal crashes became more likely within the same recorded circumstances after 2020;
  * old vehicles carry a higher adjusted risk (lower limit 1.39 or above in 12 variants);
  * pedestrian deaths concentrate mid-block and in the dark;
  * the state ranges, behaviour overlaps and 2019–21 rises all held.
* **Prediction pipeline.** No test-year information entered any modelling choice. The selection
  rule was applied as written, on 2022 only. The leakage gate works as designed (X1, F11, G03).
* **Interventions.** No archive column measures or proxies enforcement or cost. "The database
  identifies no intervention effect" stands (F10).

## 5. Corrections: status after re-computation (November 2026)

The review itself changed nothing. A later pass computed the new output tables that the † items
needed (30 CSVs under `outputs/tables/`) and applied the corrections for
`README.md`, `reports/templates/findings.md` and `findings.json`, `reports/templates/road_deaths.md`,
the public website template, `docs/limitations.md`, `docs/model_validation.md` and
`docs/methodology.md`. The same pass applied the corrections to the Phase-2 report templates
(`alcohol_drugs_restraints`, `multifactor_interactions`, `factor_contributions`,
`speeding_confounding`, `interactions`) and reduced `policy_analysis.md` to the observed baseline
and evidence ledger. `case_comparisons.md` and the hypothetical simulator were deleted, so their
items no longer apply.
The original recommendations follow unchanged, as the record.

**Applied (in the files above).** Wording of "too fast for conditions" (models A and B, the ±22%
equivalence bound, exploratory label, explanation of blank bias-grid rows); within-CRSS speeding
ratio beside the mixed one; interstate by speed band; rain and teen wording with models A and B;
belt crash-type table, two-sided misreporting with tipping points, and the corrected Phase-2
conclusion that belts are somewhat less protective with a speeding driver within crash
configuration; helmet misreporting and coverage; post-2020 composition "roughly a quarter to a
half" and both denominator shares; the corrected severity-recording statement and the selection
caveat for 87% vs 98%; attributable-fraction variants and the withdrawn "alcohol does not shrink";
measured-BAC rows for victim roles and prior DWI; belt lives "as recorded, excluding unknown belt
use"; large-truck fault caveat; "among the steepest"; periods beside "a year" figures; pedestrian
speed-limit missingness and unadjusted ratio; the prediction leakage sentence (with the 0.016 AUROC
from `ml/feature_sensitivity`); RQ5 moved to exploratory; the seven new limitations; "pre-specified in
the module docstring" and the random-forest qualification; a pinned Python version
(`.python-version`); `deaths` now fails when its matched inputs are missing (`MatchedInputsError`).

**Red-team numbers confirmed on re-computation.** The 1.06 and 1.18 for "too fast for conditions" and
the 22% bound; the 1.29 (1.13–1.47) under model B (previously unverified); within-CRSS speeding
×8.60 against ×12.79 mixed; interstate 0.57 on 50–65 mph roads; rain KA 0.89 (0.82–0.97); teen model B
0.92 (0.84–1.01); belt reductions of 50.9% (angle) and 84.4% (rollover), the 28.2% two-sided scenario
and the helmet tipping point of 5.6% with 455 discordant pairs and 15.7% coverage; 27.4% and 9.5% on
measured BAC; 60.7% of unbelted deaths in single-occupant vehicles; 2022–24 speeding fraction 11.9%
(9.1–14.8); pedestrian 50–55 mph ratio 12.2 without location, light and time of day; union 95.4%,
87.5% and 57.7%; denominator share 46% (29–64%); AUROC cost 0.016.

**Differed from the tables.**
* Within-CRSS speeding ratio CI is 7.1–10.3 (joint linearisation), not 6.5–11.4.
* Interstate at 70+ mph is 0.94 (0.63–1.38), not 1.00 (0.67–1.48).
* Within-configuration belt ratio of RRs for speeding (exploratory follow-up) is 1.17 (1.08–1.27)
  pooling single and multi-vehicle crashes, 1.24 (1.13–1.35) with rollover also crossed, and 1.10
  to 1.24 across the four layering schemes, not 1.16 (1.06–1.26); the BAC contrast is 0.96–1.03,
  null. The CIs come from a joint crash bootstrap of both arms (an earlier version treated the
  arms as independent and gave 1.18 (1.08–1.28) and 1.23 (1.13–1.35)).
* Model-B composition share runs 24–49% across the four specifications, not up to 56%; without crash
  configuration it is 9–34%.
* 40.8% of the BAC ≥ .08 driver group is imputed (not 40.5%); 20,998 deaths have unknown belt use (not
  21,003).
* Police-reported alcohol does not give a uniformly lower attributable fraction: 13.4% with unknowns
  as a level and 10.6% with unknown as no, but 27.2% for complete cases.
* Unknown pedestrian speed limit: 29.6% non-fatal vs 10.8% fatal (not 29.7%).

**Still open.**
* No table carries: the large-truck split by single-truck and truck–passenger-vehicle crashes (55% and
  97%), the state range of prior-DWI shares, the invalid-licence +40.5% without expired or cancelled
  licences, the imputed-BAC-versus-injury odds ratio (X1), or the crash-type-interaction logistic
  comparison for `model_validation.md` §8. Those statements remain qualitative or are not made.
* Code and provenance items: a code hash per module in the sidecars.
* Attacker-only claims in §6 that this pass did not re-run.

### Original recommendations (record)

Wording-only changes can go into the templates directly. Changes marked † need a new output table
first, because every number in `reports/` comes from `outputs/tables/`.

* **README.md**
  * Finding 3: "a small or no association for 'too fast for conditions' (1.06, 0.89–1.26;
    fatal-or-serious 1.18); exploratory".
  * Finding 9: "recorded differently by severity. Killed drivers are tested far more often, but
    police-recorded alcohol, drug and distraction fields are more often unknown in fatal crashes."
  * Phase-2 finding 1: "sum to at least 109% … at least 65% involve any of them".
  * Phase-2 finding 2: say that 6.5 and 3.3 exclude crash configuration.
  * Phase-2 finding 5: hold until the configuration-stratified belt contrast is checked †.
* **`reports/templates/findings.md`**
  * §2: say the CIs reflect CRSS denominator sampling only. Add the CRSS-internal ratio for
    speeding †.
  * §3: interstate speed-band heterogeneity †. Rain and teen wording.
  * §4: the "too fast for conditions" wording, plus model B † and a bias analysis † for it.
    Explain the blank QBA rows.
  * §6: "partly reflects".
  * §8: say the misreporting scenarios are one-sided and pooled. Add a crash-type table †.
  * §9: composition "roughly a quarter to a half". Give the complete-case denominator share 46%.
  * §10: add the selection caveat for 87% vs 98%.
  * §11: correct "the alcohol fraction does not [shrink]". Give period and coding variants †.
    Say the intervals are sampling-only.
  * §12: replace the leakage sentence.
  * §14: move RQ5 and the subgroup table to exploratory.
* **`reports/templates/alcohol_drugs_restraints.md`**
  * Same-driver ORs for the co-recording contrast †.
  * Non-differential drug bounds †.
  * Configuration-stratified belt contrasts †.
  * Retitle §6.
* **`reports/templates/multifactor_interactions.md`**: a common-specification row for the unit
  RRs †, the risk differences, and "in relative terms".
* **`reports/templates/factor_contributions.md`**
  * Fix the "determinate crashes only" label, or the code.
  * Reconcile the two drug definitions.
  * Say P ≈ 0.97 covers sampling error only.
  * Replace "not supported" with "cannot be evaluated".
* **`reports/templates/policy_analysis.md`**
  * §6: replace "should therefore target" with "projections should report limit-exceeding
    crashes separately".
  * §4: add an unknown/unspecified sensitivity column †. Flag the drugs row.
* **`reports/templates/case_comparisons.md`**: "48 cases in each model". Describe alcohol 1.41 as
  imprecise.
* **`reports/templates/road_deaths.md` and `website/templates/index.html`**
  * Give measured-BAC rows for victim roles and driver records †.
  * Belts: "about 6,900 as recorded, excluding unknown belt use".
  * Helmets: misreporting scenarios † and a caveat on transporting the estimate to all
    unhelmeted deaths.
  * Large trucks: add a "does not show fault" sentence.
  * Say "among the steepest" for the 2019–21 rise.
  * State the period beside each "a year" figure.
* **`docs/limitations.md`** (additions only):
  * the union depends on undetermined drug status;
  * the belt and helmet misreporting scenarios are one-sided and pooled;
  * FARS imputed BAC may use injury;
  * CRSS weights are benchmarked to FARS;
  * the CRSS pedestrian speed limit is missing in an outcome-dependent way;
  * driver-record completeness varies by state;
  * only the registered families are multiplicity-adjusted.
* **`docs/model_validation.md` §8**
  * Add the crash-type-interaction logistic comparison.
  * Say "pre-specified in the module docstring".
  * Qualify "random forest brings nothing".
* **Code and provenance**
  * Align the `speeding` registry label with its note.
  * Make `deaths` fail when its matched inputs are missing.
  * Record a code hash per module in the sidecars.
  * Pin the Python version.

## 6. Limits of this review and open items

* **Attacker-only claims.** Claims marked "attacker only" were not independently checked before
  the time box. Treat their numbers as leads to confirm before changing a published figure. In
  priority order:
  * P03: common-specification unit RRs;
  * P04: same-driver ORs and non-differential bounds;
  * W06: helmet tipping point;
  * G01.
* **Stopped early.** Several late reviewers were stopped and reported partial work. Their reports
  list what they did not test, for example X1's belt-ejection check, X3's interaction-contrast
  jackknife, X4's lives-saved heterogeneity and X6's seed-sensitivity run. Partial scripts
  without results are not evidence.
* **Reviewers are model-based.** The verifiers corrected attacker overreach:
  * F08's 6% and 60% came from arbitrary year windows;
  * F07's simulation is not a validation;
  * the attacker's "9.1 vs 8.9 unexplained" in F10 was wrong;
  * the verifiers rated G03 and F01 lower than their attackers did.

  Some overreach may remain.
* **Not identifiable.** No reviewer could settle what these data cannot identify: the true belt
  or helmet misreporting rate, the sensitivity of police speeding records in non-fatal crashes,
  or drug impairment.

## 7. Reproducing the review

The briefing, the findings register, the verifiers' protocol, the per-reviewer reports and
verifier verdicts, and the numbered scripts of every reviewer and verifier are preserved in Git
history at commit 7ee597e (under `docs/red_team/` and `scripts/audit/red_team/<ID>/`); they were
removed from the working tree. The consolidated results are this document.
