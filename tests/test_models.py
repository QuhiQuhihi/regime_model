import itertools
import numpy as np
import pandas as pd
import pytest
from research.models import filter_sequence, emission, forecasts, overlay, best_split


def test_forward_filter_against_enumeration():
    start = np.array([0.6, 0.4])
    a = np.array([[0.9, 0.1], [0.2, 0.8]])
    means = np.array([[-1.0], [1.0]])
    v = np.array([[1.0], [0.5]])
    x = np.array([[-0.7], [0.2], [1.2]])
    result = filter_sequence(x, start, a, means, v)
    for t in range(len(x)):
        masses = np.zeros(2)
        for seq in itertools.product(range(2), repeat=t + 1):
            p = start[seq[0]]
            for j, s in enumerate(seq):
                if j:
                    p *= a[seq[j - 1], s]
                p *= np.exp(emission(x[j], means, v)[s])
            masses[seq[-1]] += p
        np.testing.assert_allclose(result[t], masses / masses.sum(), atol=1e-12)
    np.testing.assert_allclose(result.sum(axis=1), 1)


def fixture():
    rng = np.random.default_rng(17)
    return pd.DataFrame(
        rng.normal(0, 0.01, (590, 2)),
        columns=["SPY", "TLT"],
        index=pd.bdate_range("2018-01-01", periods=590),
    )


def test_future_perturbation_preserves_forecasts_and_overlay():
    r = fixture()
    cut = r.index[-20]
    f, _ = forecasts(r, start="2020-01-01")
    changed = r.copy()
    changed.loc[changed.index > cut] *= 3
    g, _ = forecasts(changed, start="2020-01-01")
    # Target outcomes legitimately change after cut; compare only archived forecast fields.
    cols = ["information_date", "model", "forecast", "high_probability", "entropy"]
    pd.testing.assert_frame_equal(
        f.loc[f.information_date <= cut, cols], g.loc[g.information_date <= cut, cols]
    )
    a, b = overlay(r, f), overlay(changed, g)
    pd.testing.assert_frame_equal(a.query("date<=@cut"), b.query("date<=@cut"))
    assert (a.information_date < a.date).all()


def test_no_initial_exposure_before_execution():
    r = fixture()
    f, _ = forecasts(r, start="2020-01-01")
    a = overlay(r, f)
    first = a.query("date==date.min()")
    assert (first.earning_weight == 0).all() and (first.net <= 0).all()
    assert (a.cost >= 0).all() and (a.cash >= -1e-10).all()


def test_known_variance_break_and_missing_data():
    rng = np.random.default_rng(1)
    x = np.r_[rng.normal(0, 0.1, 200), rng.normal(0, 2, 200)]
    gain, bp = best_split(x)
    assert gain > 20 and abs(bp - 200) < 10
    r = fixture()
    r.iloc[1, 0] = np.nan
    with pytest.raises(ValueError):
        forecasts(r, start="2020-01-01")
