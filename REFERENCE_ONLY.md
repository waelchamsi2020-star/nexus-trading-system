# Reference-only and refused-no-data schools

The 32 entries below have no new strategy module in Phase A. The five REFUSED_NO_DATA moves are explicit refusals; 27 original references remain reference-only. No row can route an order.

| Catalog ID | School | Required data | Decision and numeric evidence |
|---|---|---|---|
| ta_sentiment | Sentiment / Positioning Analysis | positioning, completed_ohlc | 0/3 positioning feeds verified in MT5 contract: COT, open interest, funding |
| ta_neowave | NEoWave | completed_ohlc, long_history, session_clock | 0 independently specified NEoWave executable models; catalog has zero runtime models |
| ta_volume_theories | Volume Theories | completed_ohlc, real_volume, tick_volume | 0 verified real-volume feeds across the selected symbols; tick count is not real traded volume |
| ta_gaps | Gap Analysis | completed_ohlc, session_clock, corporate_actions | 0 verified corporate-action feeds for gap cause/adjustment in MT5 contract |
| fa_quantitative | Quantitative Fundamental Analysis | financial_statements, issuer_identity, corporate_actions | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| fa_qualitative | Qualitative Fundamental Analysis | filings, issuer_identity, behavior_log | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| fa_macro | Macroeconomic Analysis | macro_series, calendar, session_clock | 0/2 required macro feeds verified in MT5 contract: dependable economic calendar, policy interest-rate series |
| fa_industry | Industry Analysis | peer_data, filings, macro_series | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| fa_company | Company Analysis | financial_statements, issuer_identity, filings, corporate_actions | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_graham_dodd | Graham & Dodd / Security Analysis | financial_statements, issuer_identity, asset_appraisals | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| fa_behavioral | Behavioral Finance | behavior_log, positioning | REFERENCE_ONLY; 0 executable models in the catalog; 2 reference data requirements |
| fa_value | Value Investing | financial_statements, cash_forecasts, discount_rates, asset_appraisals | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_growth | Growth Investing | financial_statements, cash_forecasts, discount_rates, corporate_actions | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_income | Income Investing | dividends, financial_statements, security_terms, fund_holdings | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_garp | Growth at a Reasonable Price (GARP) | financial_statements, cash_forecasts, peer_data | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| fa_index | Index Investing | index_membership, fund_holdings, corporate_actions | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| fa_fund | Fund Investing | fund_holdings, filings, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| fa_commodity | Commodity Fundamental Analysis | commodity_balance, futures_curve, issuer_identity, macro_series | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_currency | Currency Fundamental Analysis | macro_series, calendar, issuer_identity, yield_curves | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_bond | Bond Analysis | security_terms, yield_curves, financial_statements, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_equity | Equity Analysis | financial_statements, issuer_identity, corporate_actions, cash_forecasts | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_absolute | Absolute / Intrinsic Valuation | cash_forecasts, discount_rates, financial_statements, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_relative | Relative Valuation | peer_data, financial_statements, issuer_identity, corporate_actions | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| fa_asset_based | Asset-Based Valuation | asset_appraisals, financial_statements, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| ap_top_down | Top-Down Approach | macro_series, peer_data, financial_statements, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| ap_bottom_up | Bottom-Up Approach | financial_statements, issuer_identity, cash_forecasts, discount_rates | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| ap_ddm | Dividend Discount Model (DDM) | dividends, cash_forecasts, discount_rates, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| ap_dcf | Discounted Cash Flow (DCF) | cash_forecasts, discount_rates, financial_statements, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 4 reference data requirements |
| ap_relative | Relative Valuation / Comparables Approach | peer_data, financial_statements, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| ap_asset_based | Asset-Based Valuation Approach | asset_appraisals, financial_statements, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| ap_present_value | Present Value Models | cash_forecasts, discount_rates, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
| ap_multiples | Multiplier / Multiples Models | peer_data, financial_statements, issuer_identity | REFERENCE_ONLY; 0 executable models in the catalog; 3 reference data requirements |
