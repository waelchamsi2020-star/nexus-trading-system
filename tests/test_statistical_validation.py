"""Independent arithmetic and failure boundaries for post-selection diagnostics."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('statistical_validation', Path(__file__).resolve().parents[1] / 'tools/statistical_validation.py')
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


def test_bootstrap_exact_manual_null_centering_and_total_scaling():
    values = np.array([-2., -.5, .25, 1.5, 3.])
    result = stats.bootstrap(values, repetitions=1000, seed=91)
    means = values[np.random.default_rng(91).integers(0, 5, size=(1000, 5))].mean(axis=1)
    ci = np.quantile(means, [.025, .975])
    assert result['mean_ci95'] == ci.tolist()
    assert result['total_ci95'] == (5 * ci).tolist()
    assert result['p_two_sided'] == (np.count_nonzero(np.abs(means - values.mean()) >= abs(values.mean())) + 1) / 1001
    assert result == stats.bootstrap(values, repetitions=1000, seed=91)
    assert result['verdict'] == 'NOT_SIGNIFICANT'


def test_bonferroni_and_bh_hand_calculated_and_registry_sensitivity():
    bonf, bh = stats.adjusted_pvalues([.01, .04, .03, .5])
    assert bonf == [.04, .16, .12, 1.]
    assert bh == pytest.approx([.04, .05333333333333334, .05333333333333334, .5])
    bonf_all, bh_all = stats.adjusted_pvalues([.01, .04, .03, .5], family_size=8)
    assert bonf_all == [.08, .32, .24, 1.]
    assert bh_all == pytest.approx([.08, .10666666666666667, .10666666666666667, 1.])
    with pytest.raises(ValueError):
        stats.adjusted_pvalues([.2, .3], family_size=1)
    with pytest.raises(ValueError):
        stats.adjusted_pvalues([float('nan')])


def test_invalid_and_degenerate_bootstrap_cannot_claim_efficacy():
    for values in ([], [1.], [1., 1.]):
        result = stats.bootstrap(values)
        assert result['p_two_sided'] == 1.
        assert result['verdict'] == 'NOT_SIGNIFICANT'
    with pytest.raises(ValueError):
        stats.bootstrap([1., float('inf')])
    with pytest.raises(ValueError):
        stats.bootstrap([1., 2.], repetitions=0)


def test_segment_block_resampling_does_not_mix_missing_market_periods():
    trades = [{'segment': 1, 'r': 1.}, {'segment': 1, 'r': 1.},
              {'segment': 2, 'r': -2.}, {'segment': 2, 'r': -2.}]
    result = stats.block_sensitivity(trades, repetitions=1000)
    assert result['total_ci95'] == [-2., -2.]
    assert result['segment_trade_counts'] == {'1': 2, '2': 2}
    assert result['p_two_sided'] == 1 / 1001
    with pytest.raises(ValueError):
        stats.block_sensitivity([], repetitions=1000)
