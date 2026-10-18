"""Independent fee arithmetic and frozen cross-symbol research boundary checks."""
import unittest
from unittest.mock import patch

from test_strategies import bars

from nexus.walkforward import LookaheadBiasError
from tools.symbol_generalization import evaluate, quote_fee, reprice_usd


class SymbolGeneralization(unittest.TestCase):
    def test_usd_quote_and_jpy_historical_fee_conversion(self):
        self.assertAlmostEqual(.00007, quote_fee(7., symbol="GBPUSD", profit_currency="USD", contract_size=100000., exit_quote=1.3))
        self.assertAlmostEqual(.07, quote_fee(7., symbol="XAUUSD", profit_currency="USD", contract_size=100., exit_quote=3000.))
        self.assertAlmostEqual(.0105, quote_fee(7., symbol="USDJPY", profit_currency="JPY", contract_size=100000., exit_quote=150.))
        self.assertAlmostEqual(.0112, quote_fee(7., symbol="USDJPY", profit_currency="JPY", contract_size=100000., exit_quote=160.))
        trades = [{"entry": 149., "stop": 148., "exit": 150., "gross_price_pnl": 1.}]
        result = reprice_usd(trades, symbol="USDJPY", profit_currency="JPY", contract_size=100000., commission=7.)
        self.assertAlmostEqual(.9895, result[0]["r"])
        with self.assertRaises(ValueError):
            quote_fee(7., symbol="EURGBP", profit_currency="GBP", contract_size=100000., exit_quote=.85)

    def test_segment_windows_and_slippage_identical_without_model_mutation(self):
        rows = bars(430, step=3600)
        for row in rows[210:]:
            row["time"] += 3600
        calls = []
        def replay(segment, model, symbol, timeframe, config, data_kind, context):
            calls.append((len(segment), model, config))
            return {"folds": []}
        specification = {"point": .001, "contract_size": 100000., "profit_currency": "JPY"}
        with patch("tools.symbol_generalization.walk_forward", side_effect=replay):
            result = evaluate(rows, symbol="USDJPY", specification=specification, as_of=2_000_000_000)
        self.assertEqual([210, 220], [call[0] for call in calls])
        self.assertEqual([(105, 46), (110, 49)], [(c[2]["train_bars"], c[2]["test_bars"]) for c in calls])
        self.assertTrue(all(c[1] == "support_bounce" and c[2]["slippage_price"] == .01 for c in calls))
        self.assertFalse(result["qualified"])
        rows[-1]["time"] = 2_000_000_000
        with self.assertRaises(LookaheadBiasError):
            evaluate(rows, symbol="USDJPY", specification=specification, as_of=2_000_000_000)
