import threading
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from nexus import quant
from nexus import strategies as st
from nexus.broker import MT5Broker, SimBroker
from nexus.timeframes import bar_close_time, month_start


def ts(value):return datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp()
def bar(t):return {'time': t,'open': 100,'high': 102,'low': 98,'close': 101,'tick_volume': 100}

# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class CalendarBars(unittest.TestCase):
    def test_month_boundaries_cover_leap_short_long_and_year_rollover(self):
        for start,end in [('2024-02-01','2024-03-01'),('2025-02-01','2025-03-01'),
                          ('2025-01-01','2025-02-01'),('2025-12-01','2026-01-01')]:
            with self.subTest(start=start):
                self.assertEqual(bar_close_time(ts(start),'MN1'),ts(end))
                self.assertEqual(st.validate_bars([bar(ts(start))],'MN1',ts(end))[0]['time'],ts(start))
                with self.assertRaises(st.DataError):st.validate_bars([bar(ts(start))],'MN1',ts(end)-1)
        self.assertEqual(bar_close_time(12345,'M5'),12645)

    def test_card_validity_uses_next_calendar_month(self):
        rows=[bar(month_start(ts('2025-02-01'),i-64)) for i in range(65)]
        card=st.analyze_strategy('ema_cross','X','MN1',rows,ts('2025-03-01'))
        self.assertEqual(card['data_time'],ts('2025-03-01'))
        self.assertEqual(card['expires_at'],ts('2025-04-01'))
        self.assertNotEqual(card['status'],'STALE')
        self.assertEqual(st.analyze_strategy('ema_cross','X','MN1',rows,ts('2025-04-01'))['status'],'STALE')

    def test_broker_does_not_drop_completed_february_or_accept_unfinished_january(self):
        broker=MT5Broker.__new__(MT5Broker);broker.lock=threading.RLock()
        dtype=[('time','i8'),('open','f8'),('high','f8'),('low','f8'),('close','f8')]
        for opening,now,wanted in [('2025-02-01','2025-03-01',1),('2025-01-01','2025-01-31',0)]:
            data=np.array([(ts(opening),100,102,98,101)],dtype=dtype)
            broker.mt5=SimpleNamespace(TIMEFRAME_MN1=1,copy_rates_from_pos=lambda *a, data=data:data)
            with patch('nexus.broker.time.time',return_value=ts(now)):
                self.assertEqual(len(broker.bars('X','MN1',1)),wanted)

    def test_monthly_simulator_prefix_and_completed_boundaries(self):
        sim=SimBroker(clock=lambda:ts('2025-03-15'))
        short=sim.bars('EURUSD.demo','MN1',3);long=sim.bars('EURUSD.demo','MN1',7)
        self.assertEqual(short,long[-3:])
        self.assertEqual([x['time'] for x in short],[ts('2024-12-01'),ts('2025-01-01'),ts('2025-02-01')])
        st.validate_bars(short,'MN1',ts('2025-03-01'))

    def test_replay_signal_clock_never_uses_nominal_month_seconds(self):
        rows=[bar(month_start(ts('2024-01-01'),i)) for i in range(40)]
        seen=[]
        def signal(history,as_of):
            seen.append((history[-1]['time'],as_of));return {'status':'WAIT'}
        quant.replay(rows,'engulfing',timeframe='MN1',signal_fn=signal)
        self.assertGreater(len(seen),10)
        for opening,closing in seen:self.assertEqual(closing,month_start(opening,1))
