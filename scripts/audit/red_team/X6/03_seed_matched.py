"""Seed sensitivity of the matched-design bootstrap CIs. Run with NHTSA_OUTPUT_DIR=<scratch>/outputs_seed.
Sets config.RANDOM_SEED to a different value (argv[1]) and runs analysis.matched.run() (2000 replicates).
Then compare outputs_seed/tables/matched with committed tables via 01_diff_tables-like diff (see 04)."""
import sys
from nhtsa_stats import config
from nhtsa_stats.analysis import matched
config.RANDOM_SEED = int(sys.argv[1])
print("seed", config.RANDOM_SEED, "out", config.TABLES_DIR)
print(matched.run())
