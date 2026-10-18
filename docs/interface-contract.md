# Internal interface contract

All public payloads are JSON-safe dictionaries; timestamps are UTC Unix seconds. No NaN/Infinity. All broker calls raise BrokerError on missing data (empty tuple is a valid empty book; None is an error). The root owns broker.py, market.py, engine.py, news.py, bridge/, server.py and app.py. Strategies and risk components use dependency injection, never import MetaTrader5.

Broker methods: account(), terminal(), symbols(), symbol(name), select(name), tick(name), bars(name, timeframe, count), positions(), orders(), deals(since), history_orders(since), calc_profit(side,name,volume,open_price,close_price), calc_margin(side,name,volume,price), check(request), send(request), session(name), calendar().

account: login, server, trade_mode (0 demo / 1 contest / 2 real), margin_mode (0 netting / 2 hedging), balance, equity, currency, margin_free, trade_allowed, platform_id. terminal: connected, trade_allowed, tradeapi_disabled. MT5 dictionary field names otherwise remain official.

symbol: name,path,description,currency_base,currency_profit,currency_margin,trade_calc_mode,trade_contract_size,trade_mode (0 disabled / 1 long / 2 short / 3 close / 4 full), point,trade_tick_size,trade_tick_value,volume_min,max,step,volume_limit,trade_stops_level,trade_freeze_level,trade_exemode,filling_mode,order_mode,expiration_time. session: known,open,as_of,server_offset_seconds,reason. tick: time,bid,ask. bars: time,open,high,low,close,tick_volume,real_volume,spread; ONLY completed bars, ascending, timeframe in the broker adapter's declared TIMEFRAMES map. Automatic decisions use M1,M5,M15,H1,H4.

Canonical request: action DEAL/REMOVE/SLTP, side BUY/SELL, symbol,volume,price,sl,tp,magic,comment,position/order optional,deviation. Adapter translates to MT5 constants and picks valid fill policy. check: retcode=0 success; send: retcode 10009 done,10010 partial,10008 placed; None/exception/10012 timeout/10031 connection are unknown, never safe automatic retry.

position: ticket,identifier,symbol,type (0 buy / 1 sell),volume,price_open,price_current,sl,tp,profit,swap,magic,comment,time. order/deal/history_order retain official names and numeric types. Deal type 0/1 trades, 2 balance; entry 0/1/2/3.

Card and Proposal/committee schemas are defined by strategy module. Engine ranks only fresh READY cards and quant-qualified proposals; risk final authority.

Simulation uses exactly this Broker API with is_simulation=True; live MT5 is False. It is a test fixture, never a fallback for failed MT5.
