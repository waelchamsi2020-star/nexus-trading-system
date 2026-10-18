"""Observational lifecycle of one immutable signal, without execution authority.

Invalidation and expiry are separate terminal branches. This shared lifecycle
does not claim to implement every internal formation stage of each school.
"""
import copy
import math

from .strategies import validate_bars
from .timeframes import bar_close_time


class SetupTracker:
    def __init__(self,card):
        self.card=copy.deepcopy(card)
        self.phase='SETUP'
        self.last_time=card['valid_at']
        self.last_bar=None
        self.events=[{'phase':'SETUP','at':self.last_time}]

    def _clock(self,as_of):
        if isinstance(as_of,bool) or not isinstance(as_of,(int,float)) or not math.isfinite(as_of) or as_of<self.last_time:
            raise ValueError('Lifecycle clock must be finite and monotonic')

    def _transition(self,phase,as_of):
        self.last_time=as_of
        if phase!=self.phase:
            self.phase=phase
            self.events.append({'phase':phase,'at':as_of})
        return self.phase

    def advance(self,as_of):
        self._clock(as_of)
        if self.phase in ('SETUP','ARMED') and as_of>=self.card['expires_at']:
            return self._transition('EXPIRED',as_of)
        self.last_time=as_of
        return self.phase

    def arm(self,as_of):
        self._clock(as_of)
        if self.phase in ('INVALIDATED','EXPIRED'):raise ValueError('Terminal setup cannot be rearmed')
        if as_of>=self.card['expires_at']:return self._transition('EXPIRED',as_of)
        c=self.card
        if c.get('status')!='READY' or c.get('actionable') is not True or c.get('direction') not in ('BUY','SELL'):
            raise ValueError('Only an executable READY card can be armed')
        level=(c.get('invalidation') or {}).get('price')
        if isinstance(level,bool) or not isinstance(level,(int,float)) or not math.isfinite(level) or level<=0:
            raise ValueError('A finite structural invalidation level is required')
        return self._transition('ARMED',as_of)

    def observe(self,bar,as_of):
        self._clock(as_of)
        rows=validate_bars([bar],self.card['timeframe'],as_of)
        if self.last_bar is not None and rows[0]['time']<=self.last_bar['time']:
            if rows[0]==self.last_bar:return self.advance(as_of)
            raise ValueError('A completed lifecycle candle cannot be rewritten')
        self.last_bar=copy.deepcopy(rows[0])
        if self.phase in ('INVALIDATED','EXPIRED'):
            self.last_time=as_of
            return self.phase
        c=self.card
        close_time=bar_close_time(bar['time'],c['timeframe'])
        if self.phase=='ARMED' and close_time<=c['expires_at']:
            level=c['invalidation']['price']
            crossed=bar['close']<level if c['direction']=='BUY' else bar['close']>level
            if crossed:return self._transition('INVALIDATED',as_of)
        if as_of>=c['expires_at']:return self._transition('EXPIRED',as_of)
        self.last_time=as_of
        return self.phase

    def snapshot(self):
        return {'phase':self.phase,'events':copy.deepcopy(self.events),
                'last_observed_at':self.last_time,
                'card_id':self.card['id'],'model_id':self.card['strategy_id'],
                'evidence_family':self.card['evidence_group'],'execution_authority':False}
