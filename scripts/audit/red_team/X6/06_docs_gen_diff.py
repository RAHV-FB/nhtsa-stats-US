"""Regenerate docs/generated/*.md in memory (docs_gen functions, no writes) and compare with committed files.
Needs data/processed (processed_dictionary reads the parquet schemas) so run via rt_py."""
import pathlib
from nhtsa_stats.reporting import docs_gen as g
for name, fn in [("inventory_tables.md", g.inventory_tables), ("harmonised_variables.md", g.harmonised_variables), ("processed_datasets.md", g.processed_dictionary)]:
    new = fn(); old = (pathlib.Path("docs/generated") / name).read_text()
    print(name, "IDENTICAL" if new == old else f"DIFFERS (old {len(old)} new {len(new)})")
