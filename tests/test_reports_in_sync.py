"""The committed reports, README and rendered docs equal a fresh render of their templates from the committed tables."""

from __future__ import annotations

import re

import pytest

from nhtsa_stats import config
from nhtsa_stats.reporting import render

TEMPLATES = sorted(p.name for p in render.TEMPLATE_DIR.glob("*") if p.suffix in (".md", ".json"))


DOC_TEMPLATES = sorted(
    f"docs/{p.name}" for p in (render.TEMPLATE_DIR / render.DOCS_TEMPLATE_SUBDIR).glob("*.md")
)


def _committed(template: str):
    if template.startswith("docs/"):
        return config.PROJECT_ROOT / template
    root = config.PROJECT_ROOT if template in render.ROOT_TEMPLATES else render.REPORT_DIR
    return root / template


def test_readme_is_a_template():
    assert "README.md" in TEMPLATES
    assert "README.md" in render.ROOT_TEMPLATES


def test_model_validation_is_a_template():
    assert "docs/model_validation.md" in DOC_TEMPLATES


@pytest.mark.parametrize("template", TEMPLATES + DOC_TEMPLATES)
def test_report_matches_fresh_render(tmp_path, template):
    render.render_all(out_dir=tmp_path, root_dir=tmp_path)
    fresh = (tmp_path / template).read_text()  # docs/<name> lands in tmp_path/docs/
    committed = _committed(template).read_text()
    if template.startswith("docs/"):
        where = template
    else:
        where = "README.md" if template in render.ROOT_TEMPLATES else f"reports/{template}"
    assert fresh == committed, f"{where} is stale: run `nhtsa analyze report`"


@pytest.mark.parametrize("template", [t for t in TEMPLATES + DOC_TEMPLATES if t.endswith(".md")])
def test_committed_report_has_no_unresolved_placeholder(template):
    text = _committed(template).read_text()
    assert "{{" not in text and "}}" not in text
    assert not re.search(r"\bnan\b", text, flags=re.IGNORECASE)


def test_model_validation_prose_claims_hold():
    """Qualitative statements typed in docs/model_validation.md (numbers are rendered) stay true."""
    import pandas as pd

    tables = config.TABLES_DIR / "ml"
    comp = pd.read_csv(tables / "model_comparison.csv")
    assert set(comp.loc[comp["selected_on_2022"], "model"]) == {"hgb"}
    assert len(comp[comp["selected_on_2022"]]) == 4  # one per outcome x stage cell
    paired = pd.read_csv(tables / "paired_differences.csv")
    hgb = paired[
        (paired["model"] == "hgb")
        & (paired["comparison"] == "vs logit_main")
        & paired["metric"].isin(["auroc", "average_precision", "brier_skill"])
    ]
    # "better than the main-effects logistic model on every proper scoring rule (paired CIs exclude zero)"
    assert ((hgb["ci_low"] > 0) | (hgb["ci_high"] < 0)).all()
    assert (hgb["estimate"] > 0).all()
    l2 = paired[
        (paired["model"] == "logit_l2")
        & (paired["comparison"] == "vs logit_main")
        & (paired["metric"] == "auroc")
    ]
    assert (l2["estimate"].abs() < 0.0005).all()  # "L2 tuning changes nothing measurable"
    # the doc says boosting's lowest-risk half is over-predicted and models under-predict later years
    tiers = pd.read_csv(tables / "calibration_by_risk_tier.csv")
    low = tiers[
        (tiers["outcome"] == "fatal")
        & (tiers["weighting"] == "weighted")
        & (tiers["model"] == "hgb")
        & (tiers["risk_tier"] == "lowest 50% of predicted risk")
    ]
    assert (low["oe_ratio"] < 1).all()
    temporal = pd.read_csv(tables / "temporal_stability.csv")
    oe = temporal[
        (temporal["outcome"] == "fatal")
        & (temporal["metric"] == "oe_ratio")
        & (temporal["stage"] == "pre_crash+circumstance")
    ]
    assert (oe["estimate"] > 1).all()  # "observed/expected is above 1 in every later year"
    # §8: crash-type effect modification is clear for these exposures (homogeneity p < 0.001)
    em = pd.read_csv(config.TABLES_DIR / "severity" / "fatal_effect_modification.csv")
    for exposure in ("exceeded_limit", "alcohol", "motorcycle", "large_truck"):
        sub = em[(em["exposure"] == exposure) & (em["outcome"] == "fatal")]
        assert (sub["p_homogeneity_rr"] < 0.001).all(), exposure
