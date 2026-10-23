# What the crash data can and cannot say about interventions

*Speed cameras, roadside alcohol and drug testing, belt enforcement and other measures.
Every number is read from `outputs/tables/` when this report is rendered. Estimate types:
**observed** (FARS census), **estimated** (CRSS design-based), **adjusted association**
(model-based, conditional on a reported crash, not causal) and **hypothetical** (follows from
stated assumptions, not from data about the intervention).*

## 1. The identification problem

The 36 archives describe crashes. They contain no record of where cameras stood, how many
roadside checks were held, how many drivers were tested or warned, what campaigns ran, or what
any of it cost. A search of all
{{json:simulation/inventory_enforcement_cost_fields|n_columns_scanned|,.0f}} source
columns for enforcement- or cost-like fields found nothing that measures an intervention
(`simulation/inventory_enforcement_cost_fields`).

So the data **cannot** estimate the effect of any intervention. What they can do is:

1. show where deaths concentrate and how the target groups overlap (observed);
2. show how strongly each targeted circumstance is associated with a crash being fatal, and how
   much of that association survives measurement error (adjusted association);
3. say what an intervention **would have to achieve** to reach a given reduction
   (hypothetical, but needing no assumption about the intervention itself);
4. project outcomes **if** the user's assumptions about coverage, behaviour and effects hold
   (hypothetical; the policy simulator in the research interface).

## 2. The evidence ledger

*Source: `policy/evidence_ledger`.*

{{mdtable:policy/evidence_ledger||intervention:Intervention:;fars_deaths_per_year_in_segment:FARS deaths per year in target segment (2022–2024):,.0f;adjusted_severity_rr:Adjusted fatal RR of the targeted circumstance:;evidence_grade_target_association:Strength of the target association:;numeric_estimate_possible:Can the data give a numeric effect?:}}

The full ledger, with prevalence, robustness to measurement error, relevant interactions, who is
most affected, and the assumptions each projection needs, is in
`outputs/tables/policy/evidence_ledger.csv` and the interface.

## 3. Where deaths concentrate (observed)

Mean deaths per year, 2022–2024, in each target segment (FARS). Deaths whose status is unknown
are not counted, so segment counts are lower bounds. The alcohol segment (a driver at BAC ≥ 0.08)
is an expected value over NHTSA's 10 multiply-imputed BAC values, not a census count.

{{mdtable:simulation/threshold_required_share|reduction_of_all_deaths_pct=1|segment:Segment:;reliability:Reliability:;segment_deaths_per_year:Deaths per year:,.0f;segment_share_of_all_deaths:Share of all road deaths:pct:1}}

All road deaths: {{simulation/threshold_required_share|segment=speeding;reduction_of_all_deaths_pct=1|all_deaths_per_year|,.0f}}
per year. The segments overlap heavily, so their deaths cannot be added:

{{mdtable:simulation/segment_overlap|nested=False|segment_a:Segment A:;segment_b:Segment B:;deaths_both:Deaths per year in both:,.0f;share_of_a_also_in_b:Share of A also in B:pct:0;share_of_b_also_in_a:Share of B also in A:pct:0}}

A combined programme against speeding and alcohol therefore acts on
{{simulation/segment_overlap|segment_a=speeding;segment_b=alcohol|deaths_either|,.0f}} deaths a
year, not on the sum of the two segments. The simulator combines interventions within each cell
of this overlap, so shared deaths are counted once.

## 4. What an intervention would have to achieve (no effect assumptions)

To cut **all** road deaths by 1%, 5% or 10% through one segment alone, this share of the
segment's deaths would have to be prevented (hypothetical arithmetic on observed counts):

**1% of all deaths**

{{mdtable:simulation/threshold_required_share|reduction_of_all_deaths_pct=1|segment:Segment:;deaths_to_prevent_per_year:Deaths to prevent per year:,.0f;required_share_of_segment_deaths:Share of segment deaths to prevent:pct:1}}

**5% of all deaths**

{{mdtable:simulation/threshold_required_share|reduction_of_all_deaths_pct=5|segment:Segment:;deaths_to_prevent_per_year:Deaths to prevent per year:,.0f;required_share_of_segment_deaths:Share of segment deaths to prevent:pct:1}}

**10% of all deaths**

{{mdtable:simulation/threshold_required_share|reduction_of_all_deaths_pct=10|segment:Segment:;deaths_to_prevent_per_year:Deaths to prevent per year:,.0f;required_share_of_segment_deaths:Share of segment deaths to prevent:pct:1}}

Limit-exceeding speeding — the part of speeding that cameras act on — is a much smaller segment
than speeding as a whole, so a camera programme would have to prevent a far larger share of its
target deaths to reach the same national reduction.

## 5. If the measured associations were causal (still hypothetical)

Treating the adjusted associations as causal effects of removing the factor (severity pathway
only, no effect on whether crashes happen), the change required for a 1% reduction in all road
deaths would be:

{{mdtable:simulation/threshold_conditional_on_empirical_estimates|input_point=estimate;reduction_of_all_deaths_pct=1|segment:Segment:;empirical_input:Empirical input:;input_value:Value:.3f;required_quantity:Required change:;required_value:Required value:pct:1}}

Two cautions apply. First, these associations are conditional on a crash and are not causal;
residual confounding and the recording of behaviours after the crash can inflate them (finding
9 in `reports/findings.md`). Second, the belt rows depend strongly on how truthfully surviving
occupants report belt use. If 10% of "belted" survivors were in fact unbelted, the required
conversion rises to
{{simulation/threshold_conditional_on_empirical_estimates|empirical_input=belt.fatality_reduction.misreport_f10;input_point=estimate;reduction_of_all_deaths_pct=1|required_value|pct:1}}
of unbelted occupants, against
{{simulation/threshold_conditional_on_empirical_estimates|empirical_input=belt.fatality_reduction;input_point=estimate;reduction_of_all_deaths_pct=1|required_value|pct:1}}
with no misreporting.

## 6. Interventions one by one

**Speed cameras.** The data separate two kinds of police-recorded speeding. Exceeding the limit
— what automated enforcement detects — has a large adjusted association with a fatal outcome
({{severity/fatal_speeding_type|level=exceeded_limit_or_racing|adj_rr|ci:1}}). "Too fast for
conditions", the larger category, shows no detectable excess for a fatal outcome
({{severity/fatal_speeding_type|level=too_fast_for_conditions|adj_rr|ci:2}}) and a small one for
fatal-or-serious outcomes ({{severity/ka_speeding_type|level=too_fast_for_conditions|adj_rr|ci:2}}). Any projection
of a camera programme should therefore target limit-exceeding crashes. How many cameras give
what coverage of speeding exposure, how much speeding falls where they operate, and how far the
effect spills over are not in the data; the simulator requires them as inputs. Doubling the
number of cameras does not double coverage: under a saturating coverage curve, doubling from
the point where one unit covers about 63% of the exposure adds only
{{simulation/coverage_doubling_demo|form=saturating;units=1|doubling_ratio|.2f}} times the
coverage (`simulation/coverage_doubling_demo`, a mathematical property of the curve, not data).

**Roadside alcohol testing.** Alcohol involvement is strongly associated with a fatal outcome
under every coding (`reports/findings.md`, finding 4), and FARS attributes
{{simulation/threshold_required_share|segment=alcohol;reduction_of_all_deaths_pct=1|segment_deaths_per_year|,.0f}}
deaths a year to crashes with a driver at BAC ≥ 0.08 (expected value over NHTSA's imputations).
How many checks, how often impaired drivers are detected, and how strongly the perceived risk of
detection deters drinking and driving are not in the data.

**Roadside drug testing.** The data cannot support even the target association: drug status is
unknown for about half of fatal crashes, testing is selective by injury severity and state,
coding changed in 2019–2020, and a positive test shows presence, not impairment. The segment is
flagged LOW reliability, and the simulator can only show what effect sizes would be needed.

**Belt enforcement.** This is the closest the data come to an effect estimate. Within the same
vehicle in fatal crashes, belted occupants were less likely to die than unbelted ones
(`reports/findings.md`, finding 7). How many unbelted occupants enforcement would convert, and
whether converters resemble other unbelted occupants, are assumptions.

**Pedestrian lighting, speed management and vehicle design.** The contrasts between existing
conditions (lit vs unlit roads, speed limits, striking-vehicle type) are large and objectively
measured, but they compare places and vehicles as they are, not the effect of changing them.

## 7. Costs and break-even

No prices exist in the data, and none are assumed. Given user-supplied costs (investment,
operating cost, service life, discount rate), the cost tools compute the equivalent annual cost,
the cost per death or KA crash prevented under the user's effect assumptions, and three
break-even quantities:

* the minimum number of deaths a programme must prevent each year to meet a cost-effectiveness
  threshold the user sets;
* the minimum value of an effectiveness parameter (for example, the behavioural response to
  cameras) at which the programme meets that threshold, solved through the simulation engine;
* the effectiveness at which one intervention outperforms another for the same budget.

Worked examples with invented, clearly labelled inputs are in `docs/policy_assumptions.md`;
they are illustrations of the arithmetic, not results.

## 8. What would be needed to estimate effects

Effect estimates would require data that are not in this repository: camera locations and
operating periods, check schedules and test counts, citation records, measured travel speeds
or traffic volumes, and programme costs, linked to crashes in time and place. With such data,
designs such as before–after comparisons with comparison sites or staggered roll-outs could
estimate effects; the severity associations here would then serve as plausibility checks.
