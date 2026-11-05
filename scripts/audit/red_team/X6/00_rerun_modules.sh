#!/usr/bin/env bash
# Re-runs analysis modules sequentially into the scratch output dir (never the repo outputs).
RT=/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team
export NHTSA_OUTPUT_DIR=$RT/work/X6/outputs RT_TIMEOUT=1800
for m in "$@"; do
  s=$(date +%s)
  $RT/bin/rt_py -m nhtsa_stats.cli analyze $m > $RT/work/X6/log_$m.txt 2>&1
  echo "$m rc=$? $(( $(date +%s)-s ))s"
done
