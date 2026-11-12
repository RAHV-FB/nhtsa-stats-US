# What the crash data can and cannot say about interventions

*Speed cameras, roadside alcohol and drug testing, belt enforcement and other measures.
Every number is read from `outputs/tables/` when this report is rendered. Estimate types:
**observed** (FARS census), **estimated** (CRSS design-based) and **adjusted association**
(model-based, conditional on a reported crash, not causal).*

## 1. The identification problem

The 36 archives describe crashes. They contain no record of where cameras stood, how many
roadside checks were held, how many drivers were tested or warned, what campaigns ran, or what
any of it cost. A search of all
{{json:simulation/inventory_enforcement_cost_fields|n_columns_scanned|,.0f}} source
columns for enforcement- or cost-like fields found nothing that measures an intervention
(`simulation/inventory_enforcement_cost_fields`).

So the data **cannot** estimate the effect of any intervention. What they can do is show where
deaths concentrate and how the target groups overlap (observed), and how strongly each targeted
circumstance is associated with a crash being fatal (adjusted association, not a causal effect).

## 2. Where deaths concentrate (observed)

Mean deaths per year, 2022–2024, in each target segment (FARS; all road deaths:
{{simulation/baseline|name=fars.deaths_per_year|value|,.0f}} per year). Deaths whose status is
unknown are not counted, so segment counts are lower bounds. The alcohol segment (a driver at
BAC ≥ 0.08) is an expected value over NHTSA's 10 multiply-imputed BAC values, not a census count.

| Segment | Reliability | Deaths per year | Share of all road deaths | Deaths per year with unknown status (not counted) |
|---|---|---|---|---|
| Speeding-related | {{simulation/baseline|name=fars.deaths_per_year.speeding|reliability|}} | {{simulation/baseline|name=fars.deaths_per_year.speeding|value|,.0f}} | {{simulation/baseline|name=fars.share_of_deaths.speeding|value|pct:1}} | {{simulation/baseline|name=fars.deaths_per_year.speeding.status_unknown|value|,.0f}} |
| Exceeded the limit or racing | {{simulation/baseline|name=fars.deaths_per_year.speeding_exceeded_limit|reliability|}} | {{simulation/baseline|name=fars.deaths_per_year.speeding_exceeded_limit|value|,.0f}} | {{simulation/baseline|name=fars.share_of_deaths.speeding_exceeded_limit|value|pct:1}} | {{simulation/baseline|name=fars.deaths_per_year.speeding_exceeded_limit.status_unknown|value|,.0f}} |
| Alcohol (driver BAC ≥ 0.08) | {{simulation/baseline|name=fars.deaths_per_year.alcohol|reliability|}} | {{simulation/baseline|name=fars.deaths_per_year.alcohol|value|,.0f}} | {{simulation/baseline|name=fars.share_of_deaths.alcohol|value|pct:1}} | none (BAC imputed) |
| Drugs (police-reported) | {{simulation/baseline|name=fars.deaths_per_year.drugs|reliability|}} | {{simulation/baseline|name=fars.deaths_per_year.drugs|value|,.0f}} | {{simulation/baseline|name=fars.share_of_deaths.drugs|value|pct:1}} | {{simulation/baseline|name=fars.deaths_per_year.drugs.status_unknown|value|,.0f}} |
| Unrestrained occupants of light vehicles | {{simulation/baseline|name=fars.deaths_per_year.unrestrained_lpv|reliability|}} | {{simulation/baseline|name=fars.deaths_per_year.unrestrained_lpv|value|,.0f}} | {{simulation/baseline|name=fars.share_of_deaths.unrestrained_lpv|value|pct:1}} | {{simulation/baseline|name=fars.deaths_per_year.unrestrained_lpv.status_unknown|value|,.0f}} |

**The drug segment is driven by missing data, not by drug involvement.** The counted segment
is a lower bound on drug-positive crashes and mostly reflects who was tested and recorded: the
{{simulation/baseline|name=fars.deaths_per_year.drugs.status_unknown|value|,.0f}} deaths per year
in crashes of unknown drug status (not counted) far outnumber the
{{simulation/baseline|name=fars.deaths_per_year.drugs|value|,.0f}} counted. Testing is
selective by injury severity and state (`reports/alcohol_drugs_restraints.md`), and the police
field used here and the toxicology-based count used elsewhere in the reports are different
definitions of drug involvement, so this row neither shows how many deaths drugs contribute nor
allows a comparison with the other segments.

The segments overlap heavily, so their deaths cannot be added:

{{mdtable:simulation/segment_overlap|nested=False|segment_a:Segment A:;segment_b:Segment B:;deaths_both:Deaths per year in both:,.0f;share_of_a_also_in_b:Share of A also in B:pct:0;share_of_b_also_in_a:Share of B also in A:pct:0}}

For example, speeding-related and alcohol-involved crashes together account for
{{simulation/segment_overlap|segment_a=speeding;segment_b=alcohol|deaths_either|,.0f}} deaths a
year, not the sum of the two segments. Segment counts are not "preventable fractions": a death
in a speeding-related crash might have occurred without the speeding.

## 3. Associations with a fatal outcome (adjusted, not causal)

The two kinds of police-recorded speeding differ. Exceeding the limit has a large adjusted
association with a fatal outcome
({{severity/fatal_speeding_type|level=exceeded_limit_or_racing|adj_rr|ci:1}}). "Too fast for
conditions", the larger category, shows no detectable excess for a fatal outcome
({{severity/fatal_speeding_type|level=too_fast_for_conditions|adj_rr|ci:2}}) and a small one for
fatal-or-serious outcomes ({{severity/ka_speeding_type|level=too_fast_for_conditions|adj_rr|ci:2}}).
These are associations conditional on a police-reported crash; residual confounding and the
recording of behaviours after the crash can inflate them (finding 9 in `reports/findings.md`).
Alcohol involvement is strongly associated with a fatal outcome under every coding
(`reports/findings.md`, finding 4). Drug involvement cannot support even the association: drug
status is unknown for about half of fatal crashes, testing is selective by injury severity and
state, coding changed in 2019–2020, and a positive test shows presence, not impairment. Within
the same vehicle in fatal crashes, belted occupants were less likely to die than unbelted ones
(`reports/findings.md`, finding 7); that estimate is conditional on a fatal crash and sensitive to
survivor misreporting of belt use, and it says nothing about how many occupants enforcement
would convert. The contrasts for pedestrian lighting, speed limits and striking-vehicle type
compare places and vehicles as they are, not the effect of changing them.

## 4. The evidence ledger

*Source: `policy/evidence_ledger`.*

{{mdtable:policy/evidence_ledger||intervention:Intervention:;fars_deaths_per_year_in_segment:FARS deaths per year in target segment (2022–2024):,.0f;adjusted_severity_rr:Adjusted fatal RR of the targeted circumstance:;evidence_grade_target_association:Strength of the target association:}}

The full ledger, with prevalence, robustness to measurement error, relevant interactions, who is
most affected, and what each intervention's effect would require, is in
`outputs/tables/policy/evidence_ledger.csv` and the interface.

## 5. What would be needed to estimate effects

Effect estimates would require data that are not in this repository: camera locations and
operating periods, check schedules and test counts, citation records, measured travel speeds
or traffic volumes, and programme costs, linked to crashes in time and place. With such data,
designs such as before–after comparisons with comparison sites or staggered roll-outs could
estimate effects; the severity associations here would then serve as plausibility checks.
