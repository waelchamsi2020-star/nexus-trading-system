"""Context uncertainty adapter tests on explicitly synthetic trade fixtures."""
import copy
import importlib.util
from pathlib import Path

import pytest

from nexus.strategies import REGISTRY

_path = Path(__file__).resolve().parents[1] / 'tools/context_study_statistics.py'
_spec = importlib.util.spec_from_file_location('context_study_statistics_fixture', _path)
stats = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stats)


def fixture_study():
    rows = []
    for index, model in enumerate(sorted(REGISTRY)):
        trades = []
        if index == 0:
            trades = [{'strategy_id': model, 'r': value, 'entry_time': 1000 + counter * 3600,
                       'exit_time': 1100 + counter * 3600, 'symbol': 'SYNTHETIC',
                       'timeframe': 'H1', 'fold_id': counter // 4}
                      for counter, value in enumerate([-1., 2., .5, 1.5] * 10)]
        rows.append({'model': model, 'trades': len(trades), 'trade_records': trades,
                     'net_r': sum(row['r'] for row in trades), 'censored': 3 if index == 0 else 0})
    return {'symbol': 'SYNTHETIC', 'timeframe': 'H1', 'source_data_sha256': 'a' * 64,
            'qualified': False, 'execution_authority': False,
            'protocol': {'costs': stats.EXPECTED_COSTS, 'train': 5000, 'test': 1000,
                         'step': 500, 'embargo': 24},
            'scenarios': [{'commission_usd_round_trip_per_lot': 0., 'models': []},
                          {'commission_usd_round_trip_per_lot': 7., 'models': rows}]}


def fee_rows(study):
    return study['scenarios'][-1]['models']


def test_adapter_uses_fee_seven_all_58_unique_primary_records():
    study = fixture_study()
    document, censoring = stats.fee_seven_document(study)
    assert len(document['models']) == 58
    assert document['commission_usd_round_trip_per_lot'] == 7
    assert document['slippage_points_per_side'] == 10
    assert sum(censoring.values()) == 3
    assert len(document['models'][0]['trades']) == 40
    document['models'][0]['trades'][0]['r'] = 9999
    assert fee_rows(study)[0]['trade_records'][0]['r'] == -1


def test_all_variants_keep_58_models_and_add_search_correction():
    study = fixture_study()
    result = stats.analyze_context_studies({'causal_regime': study, 'full_stage1': copy.deepcopy(study)}, iterations=100)
    assert result['seed'] == 20261019
    assert result['per_variant_family'] == 58
    assert result['provided_family_size'] == 116
    assert result['orders_sent'] == 0
    for variant in result['variants'].values():
        assert variant['family_size'] == 58
        assert variant['unknown_exposures'] == 3
        assert len(variant['models']) == 58
        assert sum(row['iid']['p_two_sided_null_centered'] == 1. for row in variant['models'][1:]) == 57
        winner = variant['selected_winner']
        assert winner['trades'] == 40
        assert winner['net_r'] == 30
        assert winner['censored_exposures'] == 3
        assert winner['p_bonferroni_provided_variants'] >= winner['p_bonferroni_58']
        assert variant['qualified'] is False
        assert variant['execution_authority'] is False


def test_tiny_best_is_descriptive_and_not_promoted():
    study = fixture_study()
    row = fee_rows(study)[0]
    row['trade_records'] = row['trade_records'][:4]
    row['trades'] = 4
    row['net_r'] = sum(trade['r'] for trade in row['trade_records'])
    result = stats.analyze_context_studies({'causal_regime': study}, iterations=100)['variants']['causal_regime']
    assert result['selected_winner'] is None
    assert result['descriptive_best_without_sample_cutoff']['trades'] == 4
    assert result['descriptive_best_without_sample_cutoff']['minimum_30_trades_satisfied'] is False
    assert result['winner_status'] == 'NO_ELIGIBLE_MODEL_WITH_30_TRADES'


@pytest.mark.parametrize('field,value', [('train', 4999), ('test', 999), ('step', 250), ('embargo', 23),
                                       ('costs', 'USD7 but 0 slippage')])
def test_window_or_cost_changes_are_rejected(field, value):
    study = fixture_study()
    study['protocol'][field] = value
    with pytest.raises(ValueError, match='remain fixed'):
        stats.fee_seven_document(study)


def test_missing_models_duplicates_and_reported_count_mismatch_are_rejected():
    study = fixture_study()
    fee_rows(study).pop()
    with pytest.raises(ValueError, match='All 58'):
        stats.fee_seven_document(study)
    study = fixture_study()
    fee_rows(study).append(copy.deepcopy(fee_rows(study)[0]))
    with pytest.raises(ValueError, match='duplicate model'):
        stats.fee_seven_document(study)
    study = fixture_study()
    fee_rows(study)[0]['trades'] += 1
    with pytest.raises(ValueError, match='closed count differs'):
        stats.fee_seven_document(study)


def test_net_mismatch_and_censored_null_not_coerced_to_zero():
    study = fixture_study()
    fee_rows(study)[0]['net_r'] += 1
    with pytest.raises(ValueError, match='net R differs'):
        stats.fee_seven_document(study)
    study = fixture_study()
    fee_rows(study)[0]['trade_records'][0]['r'] = None
    with pytest.raises(ValueError, match='Finite numeric'):
        stats.fee_seven_document(study)
    study = fixture_study()
    fee_rows(study)[0]['censored'] = -1
    with pytest.raises(ValueError, match='censored count'):
        stats.fee_seven_document(study)


def test_duplicate_trade_records_fail_instead_of_silent_deduplication():
    study = fixture_study()
    row = fee_rows(study)[0]
    row['trade_records'].append(copy.deepcopy(row['trade_records'][0]))
    row['trades'] += 1
    row['net_r'] -= 1
    with pytest.raises(ValueError, match='Duplicate OOS'):
        stats.fee_seven_document(study)


def test_input_order_does_not_change_result_or_random_seed():
    study = fixture_study()
    first = stats.analyze_context_studies({'b': study, 'a': copy.deepcopy(study)}, iterations=100)
    second = stats.analyze_context_studies({'a': copy.deepcopy(study), 'b': study}, iterations=100)
    assert first == second


def test_missing_fee_seven_authority_and_invalid_source_are_rejected():
    study = fixture_study()
    study['scenarios'].pop()
    with pytest.raises(ValueError, match='USD7'):
        stats.fee_seven_document(study)
    study = fixture_study()
    study['execution_authority'] = True
    with pytest.raises(ValueError, match='without authority'):
        stats.fee_seven_document(study)
    study = fixture_study()
    study['source_data_sha256'] = 'not-a-sha'
    with pytest.raises(ValueError, match='SHA256'):
        stats.fee_seven_document(study)
