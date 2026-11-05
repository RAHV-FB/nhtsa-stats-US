# Verifier brief — read all of this before you start

`$RT` = `/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team`.
Repository: `/home/user/nhtsa-stats-US`.

## Your role

A red-team attacker has reported on one published finding (or one cross-cutting dimension) of
this NHTSA FARS/CRSS research project. Its report is `$RT/reports/<ID>.md` and its scripts are in
`scripts/audit/red_team/<ID>/`. Attackers make mistakes and present them as confidently as their
real findings. Your job is to decide which of the attacker's damaging claims are actually true.
Be equally sceptical of the attacker and of the project.

## Rules

`$RT/BRIEFING.md` binds you too: the repository is read-only, all data compute goes through
`$RT/bin/rt_py`, and you must never fabricate a number. Additionally:

* Write only to `scripts/audit/red_team/<ID>/` (name your files `v01_….py`, `v02_….py`, …), to
  `$RT/work/<ID>/` and to your verdict file `$RT/verify/<ID>.md`. Never edit the attacker's own
  scripts; copy one if you need to change it.
* Budget: about 15–25 tool calls. Speed matters, so verify the claims that matter, not
  everything.

## What to verify

Verify every claim that drives the attacker's verdict. That means every attack rated
material/serious/fatal, every REFUTED verdict, and the "most damaging issue". For each one, apply
three lenses:

1. **Reproduce.** Re-run the attacker's script through `rt_py`, or write a minimal independent
   recomputation, and check that the numbers match the report. Flag any number you cannot
   reproduce, or that the script does not actually print.
2. **Publication.** Quote the published text (file:line) the claim is about. Does it really say
   what the attacker says? Is the issue already disclosed in the same report, in `README.md` or
   in `docs/limitations.md`? A disclosed issue is not new, but it can still be under-weighted in
   a headline.
3. **Inference.** Try to refute the attacker's reasoning:
   * Is the alternative analysis valid and comparable?
   * Does it contradict the published claim, or does it just restate a condition the claim
     already makes?
   * Is the attacker misreading the estimand?

## Output

Your final message is the verdict file; also save it to `$RT/verify/<ID>.md`. At most 700 words.

1. A table with columns: claim | reproduce (✓/✗ + numbers) | publication (quote, disclosed?) |
   inference (holds / partly / fails, and why) | **status**. The status is one of:
   * CONFIRMED;
   * PARTLY CONFIRMED (state the corrected claim);
   * NOT CONFIRMED.
2. Your verdict on the finding: REFUTED, WEAKENED, SURVIVES or NOT TESTABLE, with a confidence.
   Say whether you agree with the attacker's verdict, and why.
3. The corrections you would actually recommend (exact wording where useful). Keep only the
   confirmed ones.
4. Your scripts, if any.

## If rt_py keeps returning 75 (no compute slot)

Many reviewers share 4 slots. Don't give up after a few tries.

* **Short scripts:** retry with a longer wait, e.g.
  `RT_MAXWAIT=420 RT_TIMEOUT=150 $RT/bin/rt_py …` (Bash `timeout: 600000`).
* **Longer scripts:** run them in the background with
  `RT_MAXWAIT=1800 RT_TIMEOUT=900 $RT/bin/rt_py … > $RT/work/<ID>/vNN.out 2>&1`
  (Bash `run_in_background: true`), then read the output file when you are notified.

Only fall back to the attacker's saved outputs if a re-run is truly impossible, and say so
explicitly.
