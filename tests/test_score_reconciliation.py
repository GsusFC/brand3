from src.features.score_reconciliation import reconcile_label_score


def test_reconcile_label_score_uses_unclear_target() -> None:
    mapping = {"clear": 80.0, "unclear": 45.0}

    assert reconcile_label_score(92.0, "unclear", mapping) == 45.0


def test_reconcile_label_score_corrects_pathologically_low_positive_scores() -> None:
    mapping = {"clear": 80.0, "unclear": 45.0}

    assert reconcile_label_score(8.0, "clear", mapping) == 80.0
    assert reconcile_label_score(20.0, "clear", mapping) == 80.0


def test_reconcile_label_score_preserves_reasonable_scores() -> None:
    mapping = {"clear": 80.0, "unclear": 45.0}

    assert reconcile_label_score(72.0, "clear", mapping) == 72.0
