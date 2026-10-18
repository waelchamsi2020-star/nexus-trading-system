"""Versioned multi-school OHLC scalp router; no direct broker send authority.

All implemented registry agents contribute inspectable evidence. Missing data
abstains. Autonomous fast mode weighs M1 dependency families without an
individual-school veto; other modes retain timeframe corroboration. Forward Demo
policy, not historical profitability qualification or complete school coverage.
"""
import copy
import hashlib
import json
import math

from . import scalping
from .committee import decide
from .learning import digest
from .strategies import analyze_all, arabic, atr, ema, validate_bars
from .timeframes import bar_close_time

PROTOCOL_ID='multi_school_v1'
DEFINITION={'id':PROTOCOL_ID,'version':'1.4.0','agents':'all_implemented_registry_models',
 'cash_protection':{'currency':'USD','trigger':1,'attempt_target':2,'fallback':'close_if_legal_floor_unavailable',
   'scope':'explicit_current_authorization_owned_fast_positions','net':'paid_cashflows_swap_exit_commission_and_adverse_slippage',
   'entry_trend':'completed_M15_and_H1_close_above_EMA20_above_EMA50_and_rising_EMA20_or_inverse_for_sell'},
 'frames':['M1','M5','M15'],'fast_entry_frames':['M1'],'normal_entry_frames':['M1','M5'],
 'corroboration':'fast_M1_two_dependency_families_strict_net_advantage_no_fixed_vote_percentage_other_modes_two_timeframes',
 'conflict':'fast_directional_family_vote_not_individual_school_veto_other_modes_triggered_veto',
 'default_target':'3R_from_original_completed_close_and_original_stop_when_model_has_default_2R',
 'fast_prefilter':'fresh_quote_and_completed_M1_only',
 'fast_entry_zone':'original_completed_close_plus_minus_half_original_structural_risk_then_independent_net_RR',
 'fast_spread_gate':'actual_broker_net_RR_no_fixed_ATR_or_stop_spread_cutoff_on_authorized_Demo',
 'fast_exit':'SL_TP_invalidation_and_shared_daily_risk_no_fixed_bar_timer',
 'fast_dedup':'one_entry_attempt_per_symbol_completed_M1_bar_across_all_schools',
 'model_specific_targets':'preserved','minimum_net_rr':2,'missing_data':'abstain',
 'source':'MT5_only','volume':'tick_proxy_when_declared_never_real_transaction_volume',
 'scope':'bounded_local_models_not_all_original_school_interpretations','authority':'Demo_forward_only'}
PROTOCOL_REVISION=digest(DEFINITION)
MODULES=('multischool.py','committee.py','engine.py','risk.py','execution.py','scalping.py','market.py','strategies.py','specialists.py','local_models.py','indicators.py','extended_models.py','store.py','config/models.yaml','config/models.schema.json')

def decision(cards,news,now,market,autonomous_fast=False):
    """Route original cards; the separate 3R plan never rewrites research cards."""
    prepared=copy.deepcopy(cards)
    for card in prepared:
        targets=card.get('targets') or []
        if not (card.get('actionable') and targets):continue
        prices=((card.get('entry') or {}).get('price'),(card.get('stop') or {}).get('price'))
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in prices):continue
        if autonomous_fast and card.get('timeframe')=='M1':
            entry=card['entry']['price'];risk=abs(entry-card['stop']['price'])
            card['entry']['zone']=[entry-.5*risk,entry+.5*risk]
        default = targets[0].get('method_code') == 'DEFAULT_STRUCTURAL_2R'
        legacy = targets[0].get('method') in ('2 * proposed stop distance', arabic('2 * proposed stop distance'))
        if not (default or legacy):continue
        entry=card['entry']['price'];stop=card['stop']['price'];sign=1 if card['direction']=='BUY' else -1
        target=entry+sign*3*abs(entry-stop)
        if target>0:card['targets']=[{**targets[0],'price':target,'method':'multi_school_v1 declared 3R plan','method_code':'MULTI_STRUCTURAL_3R'}]
    result=decide(prepared,{},news,now,market,{'validation_policy':'forward_demo',
        'decision_protocol':PROTOCOL_ID,'autonomous_fast':autonomous_fast})
    result['entry_policy']='autonomous_M1' if autonomous_fast else 'multi_timeframe'
    result['decision_protocol']=PROTOCOL_ID;result['protocol_revision']=PROTOCOL_REVISION
    result['school_participation']=[{k:c.get(k) for k in ('strategy_id','timeframe','status','direction','evidence_group','conditions_missing')} for c in cards]
    return result

class MultiSchoolMixin:
    def _cash_trend_context(self,symbol):
        now=self.clock();frames={};cache=getattr(self,'_cash_trend_cache',{})
        for tf,seconds in (('M15',900),('H1',3600)):
            key=(self.risk.key,symbol,tf,int(now//seconds))
            cached=cache.get(key)
            if cached and not 0<=self.clock()-cached['data_time']<seconds:
                cache.pop(key,None)
            if key not in cache:
                bars=validate_bars(self.broker.bars(symbol,tf,100),tf,self.clock())
                if len(bars)<60:raise ValueError('Higher timeframe trend history missing')
                data_time=bar_close_time(bars[-1]['time'],tf)
                if not 0<=self.clock()-data_time<seconds:
                    raise ValueError('Higher timeframe trend data stale')
                close=[b['close'] for b in bars];fast=ema(close,20);slow=ema(close,50)
                direction=('BUY' if close[-1]>fast[-1]>slow[-1] and fast[-1]>fast[-2] else
                    'SELL' if close[-1]<fast[-1]<slow[-1] and fast[-1]<fast[-2] else 'NEUTRAL')
                cache[key]={'timeframe':tf,'data_time':data_time,
                    'close':close[-1],'ema20':fast[-1],'ema50':slow[-1],'previous_ema20':fast[-2],'direction':direction}
            value=cache[key]
            if not 0<=self.clock()-value['data_time']<seconds:
                raise ValueError('Higher timeframe trend data stale')
            frames[tf]=copy.deepcopy(value)
        # Keep only current and preceding buckets; cache is an optimization.
        self._cash_trend_cache={k:v for k,v in cache.items() if k[0]==self.risk.key and k[3]>=int(now//(900 if k[2]=='M15' else 3600))-1}
        return frames

    def _autonomous_fast_enabled(self):
        return bool(self.settings.get('scalp_only') and self._scalp_variant('M1')=='fast'
                    and not self.settings.get('scalping',{}).get('normal',{}).get('enabled'))

    def _load_multi_reference(self):
        value=json.loads((self.root/'docs/knowledge/multi-school-reference.json').read_text(encoding='utf-8'))
        claimed=value.pop('revision',None)
        if digest(value)!=claimed or value.get('definition')!=DEFINITION or set(value.get('modules',{}))!=set(MODULES):
            raise ValueError('Multi-school execution reference is invalid')
        for name,expected in value['modules'].items():
            if hashlib.sha256((self.root/'src/nexus'/name).read_bytes()).hexdigest()!=expected:
                raise ValueError('Multi-school execution source changed: '+name)
        if self.store:
            self._execution_tables()
            with self.store.transaction() as db:
                db.execute('INSERT OR IGNORE INTO execution_reference_versions VALUES(?,?)',
                           (claimed,json.dumps({**value,'revision':claimed},ensure_ascii=False)))
        return {**value,'revision':claimed}

    def _multi_cards(self,symbol,fast_only=False):
        cards=[];books={}
        cache=getattr(self,'_multi_card_cache',{})
        for tf in (['M1'] if fast_only else DEFINITION['frames']):
            context=self._context(symbol,tf)
            bars=self.broker.bars(symbol,tf,1443 if tf=='M1' else 500);now=self.clock()
            # Models read only currency identity from symbol_info. Live bid/ask
            # changes must not recompute all closed-bar indicators every tick.
            stable_context={k:v for k,v in context.items() if k!='symbol_info'}
            stable_context['symbol_info']={k:context.get('symbol_info',{}).get(k) for k in ('currency_base','currency_profit')}
            signature=digest([bars,stable_context])
            key=(symbol,tf);saved=cache.get(key)
            if saved and saved[0]==signature:
                current=copy.deepcopy(saved[1]);self._fast_metrics['skipped_unchanged_bar']+=1
            else:
                current=analyze_all(symbol,tf,bars,now,context)
                cache[key]=(signature,copy.deepcopy(current));self._fast_metrics['evaluations']+=1
                self._observe_rules(current)
            cards.extend(current);books[tf]=bars
        # A bounded cache is an optimization; rule versions/outcomes stay persistent.
        # Retain three frames for the whole discovered universe. A fixed 96
        # entries thrashed as soon as more than 32 symbols became eligible.
        capacity=max(96,min(4096,len(self.scanner.rows)*len(DEFINITION['frames'])))
        while len(cache)>capacity:cache.pop(next(iter(cache)))
        self._multi_card_cache=cache;self.cards_by_symbol[symbol]=cards
        return cards,books

    def _multi_result(self,symbol,exclude=None):
        autonomous=self._autonomous_fast_enabled()
        cards,books=self._multi_cards(symbol,fast_only=autonomous)
        trend={};trend_error=None
        if autonomous and self.settings.get('fast_profit_protection'):
            try:trend=self._cash_trend_context(symbol)
            except (ValueError,KeyError,TypeError) as exc:trend_error=str(exc)
        info=self.broker.symbol(symbol);session=self.broker.session(symbol);calendar=self.broker.calendar()
        tick=self.broker.tick(symbol);now=self.clock()
        gate=self.news.gate(info,calendar,self.broker.is_simulation,now)
        market={'eligible':bool(self.scanner.rows.get(symbol,{}).get('eligible')),'open':bool(session.get('open')),
                'stale':not 0<=now-tick['time']<=15,'spread':tick['ask']-tick['bid'],'tick':tick}
        result=decision(cards,gate,now,market,autonomous_fast=autonomous);accepted=[];by_id={c['id']:c for c in cards}
        for record in result['ranked']:record['timeframe']=by_id.get(record['card_id'],{}).get('timeframe')
        for original in result['proposals']:
            p=copy.deepcopy(original);tf=p['timeframe'];variant=self._scalp_variant(tf)
            record=next(r for r in result['ranked'] if r['card_id']==p['id'])
            record['timeframe']=tf
            if not variant:
                record.update(eligible=False,reason_codes=['SCALP_FRAME_CONTEXT'],
                   reasons=['هذا الفريم للتأكيد فقط؛ الدخول محصور بفريم السكالب المحدد.'])
                continue
            try:
                if autonomous and self.settings.get('fast_profit_protection'):
                    if trend_error:raise ValueError(trend_error)
                    if any(value['direction']!=p['side'] for value in trend.values()):
                        raise ValueError('Completed M15 and H1 trend do not confirm the M1 direction')
                rule=self.rule_library[p['strategy_id']];profile=self.settings['scalping'][variant]
                if not self.scalping_state[variant]['progress']['entries_allowed']:raise ValueError('Scalp goal blocks new entries')
                formation={'symbol':symbol,'timeframe':tf,'strategy_id':p['strategy_id'],'version':p['strategy_version'],
                           'data_time':p['data_time'],'rule_revision':rule['revision'],'protocol_revision':PROTOCOL_REVISION}
                formation_id=digest({k:formation[k] for k in ('symbol','timeframe','data_time','protocol_revision')}) if autonomous else digest(formation)
                identity=digest([formation_id,variant])
                if self._formation_used(symbol,tf,formation_id,exclude):raise ValueError('Formation already owns an intent')
                sign=1 if p['side']=='BUY' else -1;grid=info['trade_tick_size']
                stop=round((math.floor(p['sl']/grid) if sign==1 else math.ceil(p['sl']/grid))*grid,10)
                target=round((math.ceil(p['tp']/grid) if sign==1 else math.floor(p['tp']/grid))*grid,10)
                quote=tick['ask'] if sign==1 else tick['bid']
                if not p['entry_zone'][0]<=quote<=p['entry_zone'][1]:raise ValueError('Quote outside original entry zone')
                matrix={'passed':True,'status':'READY','route':'MULTI_SCHOOL_OHLC','entry_policy':result['entry_policy'],
                        'structural_rr':{'net_cost_validation_pending':True},'evidence_families':record['evidence_families'],
                        'supporting':record['supporting'],'opposing':record['opposing'],
                        'directional_evidence':record.get('directional_evidence'),
                        'evidence_coverage':copy.deepcopy(result.get('evidence_coverage',{}))}
                # Freeze the actual model evaluations with the entry decision.
                # The UI must never fill a different protocol's absent fields
                # with invented neutral votes or use a later candle's cards.
                matrix['school_evidence']=copy.deepcopy([{
                    **{k:c.get(k) for k in ('id','strategy_id','school','version','timeframe','status',
                        'direction','actionable','score','evidence_group','conditions_met',
                        'conditions_missing','data_time','expires_at','assumptions')},
                    'role':('ENTRY_TRIGGER' if c['id']==original['id'] else
                            'SUPPORTING' if c['id'] in record['supporting'] else
                            'OPPOSING' if c['id'] in record['opposing'] else 'NO_DIRECTIONAL_VOTE')
                } for c in cards])
                if trend:matrix['higher_timeframe_trend']=trend
                p.update(id=identity,entry=quote,sl=stop,tp=target,targets=[{'price':target,'method':'versioned multi-school target'}],
                         version=p['strategy_version'],rule_revision=rule['revision'],decision_protocol=PROTOCOL_ID,
                         protocol_revision=PROTOCOL_REVISION,decision_matrix=matrix,formation=formation,formation_id=formation_id,
                         input_snapshot_hash=digest(books),execution_policy_revision=scalping.POLICY_REVISION)
                p=scalping.adaptation_plan(p,self.scalping_state[variant]['session_id'],variant)
                p.update(requested_risk_percent=profile['risk_percent'],requested_min_reward_risk=profile['min_reward_risk'])
                if profile.get('profit_percent') is not None:p['requested_profit_percent']=profile['profit_percent']
                if by_id[original['id']].get('chart_features'):p['chart_features']=by_id[original['id']]['chart_features']
                self._seal_and_preview(p)
                accepted.append(p);record.update(card_id=identity,timeframe=tf,eligible=True)
                if autonomous:break
            except (ValueError,KeyError,TypeError) as exc:
                record.update(eligible=False,reasons=[str(exc)],reason_codes=['MULTI_EXECUTION_GATE'])
        allowed={p['id'] for p in accepted}
        for r in result['ranked']:
            if r['card_id'] not in allowed:r['eligible']=False
        result.update(symbol=symbol,proposals=accepted,news_gate=gate,decision='WAIT',expires_at=now)
        if accepted:result.update(decision=accepted[0]['side'],expires_at=max(p['expires_at'] for p in accepted))
        elif result['ranked']:result['reasons']=sorted({reason for r in result['ranked'] for reason in r.get('reasons',[])})
        return result

    def _multi_analyze_symbol(self,symbol):
        deferred=self._multi_fast_preflight(symbol)
        if deferred is None:deferred=self._multi_fast_hard_gate(symbol)
        if deferred is not None:
            self.decisions[symbol]=deferred;self._rank()
            self._fast_metrics['last_checked_at']=self.clock()
            return False
        result=self._multi_result(symbol);self.decisions[symbol]=result;self._rank()
        if result['proposals']:
            self._fast_metrics['ready_rechecks']+=1;self._fast_metrics['last_ready_at']=self.clock()
        self._fast_metrics['last_checked_at']=self.clock()
        return bool(result['proposals'])

    def _multi_fast_hard_gate(self,symbol):
        """Short-circuit already mandatory gates, never create an entry.

        Execution still reruns the full model and risk path. News is read on
        every visit, and the existing causal trend cache checks its expiry.
        """
        if not self._autonomous_fast_enabled() or not self.settings.get('fast_profit_protection'):
            return None
        metrics=self._fast_metrics
        metrics['hard_gate_checks']=metrics.get('hard_gate_checks',0)+1
        info=self.broker.symbol(symbol);session=self.broker.session(symbol)
        gate=self.news.gate(info,self.broker.calendar(),self.broker.is_simulation,self.clock())
        trend={};reason=None
        if not session.get('open'):
            reason='market eligibility, session or freshness failed'
        elif not gate.get('ok') or gate.get('blackout'):
            reason='required news/calendar coverage missing, stale, or in event blackout'
        else:
            try:
                trend=self._cash_trend_context(symbol)
                directions={value['direction'] for value in trend.values()}
                if set(trend)!={'M15','H1'} or len(directions)!=1 or not directions<={'BUY','SELL'}:
                    reason='Completed M15 and H1 trend do not confirm the M1 direction'
            except (ValueError,KeyError,TypeError) as exc:
                reason=str(exc)
        if reason is None:return None
        metrics['hard_gate_deferred']=metrics.get('hard_gate_deferred',0)+1
        now=self.clock()
        return {'symbol':symbol,'decision':'WAIT','proposals':[],'ranked':[],
                'as_of':now,'expires_at':now,'reasons':[reason],
                'decision_protocol':PROTOCOL_ID,'protocol_revision':PROTOCOL_REVISION,
                'analysis_deferred':{'reason':reason,'timeframe':'M1',
                    'stage':'existing_mandatory_entry_gates','higher_timeframe_trend':trend},
                'news_gate':gate,'school_participation':[]}

    def _multi_fast_preflight(self,symbol):
        """Only freshness can defer autonomous M1; models choose the entry zone."""
        if not self._autonomous_fast_enabled():
            return None
        metrics=self._fast_metrics
        metrics['prefilter_checks']=metrics.get('prefilter_checks',0)+1
        book=self.broker.bars(symbol,'M1',32)
        tick=self.broker.tick(symbol);now=self.clock()
        data=validate_bars(book,'M1',now)
        # Missing history is handled by the full data contracts, never filled.
        if len(data)<15:return None
        width=atr(data);close=data[-1]['close']
        if width<=0:return None
        zone=(close-.15*width,close+.15*width)
        if not 0<=now-tick['time']<=15:
            reason='market eligibility, session or freshness failed'
        elif now>=bar_close_time(bar_close_time(data[-1]['time'],'M1'),'M1'):
            reason='last completed bar is stale'
        else:
            return None
        metrics['prefilter_deferred']=metrics.get('prefilter_deferred',0)+1
        return {'symbol':symbol,'decision':'WAIT','proposals':[],'ranked':[],
                'as_of':now,'expires_at':now,'reasons':[reason],
                'decision_protocol':PROTOCOL_ID,'protocol_revision':PROTOCOL_REVISION,
                'analysis_deferred':{'reason':reason,'entry_zone':list(zone),'timeframe':'M1'},
                'school_participation':[]}

    def _multi_fresh_proposal(self,p):
        if self.settings.get('decision_protocol')!=PROTOCOL_ID or p.get('decision_protocol')!=PROTOCOL_ID:
            raise ValueError('Multi-school authorization changed')
        self.risk.validate_protocol_certificate(p)
        if self.broker.is_simulation:raise ValueError('Synthetic data cannot authorize broker execution')
        if self.clock()>=p['expires_at']:raise ValueError('Multi-school proposal expired')
        result=self._multi_result(p['symbol'],exclude=p['id'])
        fresh=next((x for x in result['proposals'] if x['id']==p['id']),None)
        if fresh is None:raise ValueError('Original multi-school setup no longer passes current evidence and costs')
        for key in ('sl','tp','entry_zone','side','rule_revision','scalp_session_id','requested_risk_percent','requested_profit_percent'):
            if fresh.get(key)!=p.get(key):raise ValueError('Original multi-school plan changed: '+key)
        return fresh
