"""Consequential checks for label availability, alarm burden and recalibration accounting."""

import itertools
import numpy as np
import pandas as pd
from research.models import emission, filter_sequence
from research.practical_models import (
    smooth_origin,
    review_alarms,
    calibration,
    score_calibration,
    replay_hmm,
)


def test_fixed_lag_smoothing_against_complete_path_enumeration():
    start = np.array([0.6, 0.4])
    a = np.array([[0.9, 0.1], [0.2, 0.8]])
    means = np.array([[-1.0], [1.0]])
    var = np.array([[1.0], [0.5]])
    x = np.array([[-0.7], [0.2], [1.2]])
    filtered = filter_sequence(x, start, a, means, var)
    actual = smooth_origin(filtered[0], np.array([emission(y, means, var) for y in x[1:]]), a)
    mass = np.zeros(2)
    for seq in itertools.product(range(2), repeat=3):
        p = start[seq[0]]
        for j, s in enumerate(seq):
            if j:
                p *= a[seq[j - 1], s]
            p *= np.exp(emission(x[j], means, var)[s])
        mass[seq[0]] += p
    np.testing.assert_allclose(actual, mass / mass.sum(), atol=1e-12)
    np.testing.assert_allclose(smooth_origin(filtered[0], np.empty((0, 2)), a), filtered[0])


def test_alarm_needs_confirmation_rearming_and_spacing():
    x = np.array([0, 2, 2, 2, 2, 0, 2, 2, 2, 0, 2, 2], float)
    assert np.flatnonzero(review_alarms(x, 1, confirmation=2, cooldown=6)).tolist() == [2, 8]
    assert review_alarms(np.full(100, 2.0), 1).sum() == 1
    assert not review_alarms(np.tile([2.0, 0.0], 50), 1).any()


def fixture(n=180):
    rng = np.random.default_rng(32)
    return pd.DataFrame(
        rng.normal(0, 0.01, (n, 4)),
        index=pd.bdate_range("2020-01-01", periods=n),
        columns=["SPY", "TLT", "GLD", "DBC"],
    )


def test_covariance_reset_and_forward_targets_by_hand():
    r = fixture()
    st = pd.DataFrame({"p_high": 0.0}, index=r.index)
    st.iloc[40:43] = 0.99
    settings = {"lookback": 30, "reset_window": 20, "feature_warmup": 0}
    mats, sig = calibration(r, st, settings)
    t = 41
    z = r.iloc[t - 19 : t + 1].to_numpy()
    raw = z.T @ z / 20
    expected = 0.9 * raw + 0.1 * np.diag(np.diag(raw))
    np.testing.assert_allclose(mats["HMM reset"][t], expected, atol=1e-15)
    assert np.linalg.eigvalsh(mats["HMM reset"][29:]).min() > 0
    for c in r.columns:
        st["v_" + c] = 0.0001
    scored = score_calibration(r, mats, st)
    row = scored.query('method=="HMM reset" and asset=="SPY"').iloc[0]
    np.testing.assert_allclose(row.target, (r.SPY.iloc[30:35] ** 2).mean())
    assert (
        row.date == r.index[29]
        and row.target_start == r.index[30]
        and row.target_end == r.index[34]
    )
    assert scored.date.max() == r.index[-6]
    np.testing.assert_allclose(row.loss, np.log(row.forecast) + row.target / row.forecast)


def test_future_change_cannot_revise_original_decisions_or_available_labels():
    r = fixture(200)
    cut = r.index[150]
    changed = r.copy()
    changed.loc[changed.index > cut] *= 4
    a, ar, _ = replay_hmm(r, lookback=100, lags=(5, 20))
    b, br, _ = replay_hmm(changed, lookback=100, lags=(5, 20))
    pd.testing.assert_frame_equal(a.loc[:cut], b.loc[:cut])
    pd.testing.assert_frame_equal(ar[ar.available_date <= cut], br[br.available_date <= cut])
    am, asig = calibration(r, a, {"lookback": 100, "feature_warmup": 0})
    bm, bsig = calibration(changed, b, {"lookback": 100, "feature_warmup": 0})
    pd.testing.assert_frame_equal(asig.loc[:cut], bsig.loc[:cut])
    for name in am:
        np.testing.assert_allclose(am[name][:151], bm[name][:151], equal_nan=True)
    for row in ar.itertuples():
        assert r.index.get_loc(row.available_date) - r.index.get_loc(row.state_date) == row.lag


def test_feature_regimes_preserve_available_information():
    from research.feature_regimes import risk_features, replay_feature_hmm
    from research.practical_config import ASSETS

    rng = np.random.default_rng(90)
    r = pd.DataFrame(
        rng.normal(0, 0.01, (285, 8)),
        columns=list(ASSETS),
        index=pd.bdate_range("2020-01-01", periods=285),
    )
    cut = r.index[240]
    changed = r.copy()
    changed.loc[changed.index > cut] *= 4
    pd.testing.assert_frame_equal(risk_features(r).loc[:cut], risk_features(changed).loc[:cut])
    a, ar, _ = replay_feature_hmm(r, lookback=100)
    b, br, _ = replay_feature_hmm(changed, lookback=100)
    pd.testing.assert_frame_equal(a.loc[:cut], b.loc[:cut])
    pd.testing.assert_frame_equal(ar[ar.available_date <= cut], br[br.available_date <= cut])
    assert a.index[0] == r.index[162]
    assert a[[f"v_{ticker}" for ticker in ASSETS]].min().min() > 0
