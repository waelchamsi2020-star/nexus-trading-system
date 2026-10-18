"""Real browser against an isolated local service. Never connects to MT5.

No mock browser, no production account, no live trades. Axe results are automated
checks, not a complete WCAG conformance assessment.
"""
import argparse
import copy
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from playwright.sync_api import sync_playwright

from nexus.engine import Engine
from nexus.learning import feature_drift_review
from nexus.server import LocalServer


def keyboard_screens(page, checks, screenshots):
    """Real keyboard events in Chromium; not a human screen-reader audit."""
    for view in ('overview','markets','research','news','positions','performance','knowledge','audit','setup'):
        nav=page.locator(f'.nav-item[data-view="{view}"]')
        nav.focus();page.keyboard.press('Enter')
        page.locator('#view-'+view).wait_for(state='visible')
        page.screenshot(path=str(screenshots/f'keyboard-{view}-before.png'),full_page=False)
        page.keyboard.press('Tab')
        focus=page.evaluate("""() => {const e=document.activeElement,s=getComputedStyle(e);return {
            tag:e.tagName,id:e.id,visible:!!(e.getClientRects().length),
            focusVisible:e.matches(':focus-visible'),outline:s.outlineStyle,width:parseFloat(s.outlineWidth),
            shadow:s.boxShadow};}""")
        checks.append({'name':'keyboard_tab_focus_'+view,'group':'keyboard',
                       'passed':focus['visible'] and focus['focusVisible'] and
                                (focus['outline']!='none' and focus['width']>0 or focus['shadow']!='none'),
                       'focus':focus})
        page.keyboard.press('Shift+Tab');page.keyboard.press('Enter')
        checks.append({'name':'keyboard_enter_navigation_'+view,'group':'keyboard',
                       'passed':page.locator('#view-'+view).is_visible()})
        controls=page.locator('#view-'+view).locator('button:enabled:visible,input:enabled:visible,select:enabled:visible,textarea:enabled:visible,summary:visible')
        visited=[]
        if controls.count():
            controls.first.focus()
            for _ in range(min(controls.count(),20)):
                visited.append(page.evaluate("""() => {const e=document.activeElement,s=getComputedStyle(e);return {
                    tag:e.tagName,id:e.id,visible:!!e.getClientRects().length,
                    focusVisible:e.matches(':focus-visible'),outline:s.outlineStyle,width:parseFloat(s.outlineWidth),
                    shadow:s.boxShadow};}"""))
                page.keyboard.press('Tab')
        checks.append({'name':'keyboard_form_traversal_'+view,'group':'keyboard','visited':visited,
                       'passed':all(x['visible'] and x['focusVisible'] and
                                    (x['outline']!='none' and x['width']>0 or x['shadow']!='none') for x in visited)})
        page.screenshot(path=str(screenshots/f'keyboard-{view}-after.png'),full_page=False)


def drift_dashboard_scenario(page, engine, checks, screenshots):
    """Display test with an explicitly synthetic shift; never a performance label."""
    original=copy.deepcopy(engine.learning_state)
    try:
        drift=feature_drift_review([[-1.],[1.]]*20,[[4.]]*12,['fixture_feature'])
        engine.learning_state={'chart_learning':{'mode':'SHADOW_ONLY','models':[
            {'strategy_id':'ema_cross','symbol':'SYNTHETIC','timeframe':'M1','revision':'display-fixture',
             'status':'EVALUATED_SHADOW','samples':52,'train_samples':40,'holdout_samples':12,'drift_review':drift}]}}
        engine._publish()
        page.locator('#refresh-button').click()
        page.locator('.nav-item[data-view="knowledge"]').click()
        page.locator('#chart-learning-details > summary').click()
        page.locator('#school-drift-details > summary').click()
        dashboard=page.locator('#school-drift-dashboard')
        dashboard.get_by_text('غير قابل للتقييم: بيانات التدريب غير كافية',exact=True).first.wait_for()
        details=dashboard.locator('details').first
        details.locator('summary').click()
        details.locator('div[dir="ltr"]').filter(has_text='fixture_feature').first.wait_for()
        bounds_text=details.locator('div[dir="ltr"]').first.inner_text().translate(dict.fromkeys(map(ord,'\u061c\u200e\u200f')))
        if '[-3, 3]' not in bounds_text or 'σ=1' not in bounds_text:raise AssertionError(bounds_text)
        checks.append({'name':'school_drift_58_rows_and_derived_bounds','group':'shadow_drift',
                       'passed':dashboard.locator('tbody tr').count()==58 and drift['status']=='RESEARCH_DRIFT_ALERT',
                       'data_kind':'SYNTHETIC_DISPLAY_TEST','execution_authority':False})
        page.screenshot(path=str(screenshots/'school-drift-synthetic.png'),full_page=True)
    finally:
        engine.learning_state=original;engine._publish()
        page.locator('#refresh-button').click()


def execution_scenarios(checks):
    """Actual UI -> API -> freshness/risk/executor -> synthetic broker ledger.

    The fixture adapter advertises a Demo transport to exercise the production
    freshness boundary, but retains SimBroker.send and cannot contact MT5.
    Signal fixtures are injected; this is not evidence of strategy profitability.
    """
    now = time.time()
    with tempfile.TemporaryDirectory(prefix='quant-browser-orders-') as data:
        engine = Engine(ROOT, Path(data), clock=lambda: now)
        engine._connect(True)
        engine.broker.is_simulation = False  # test adapter only; no production switch
        settings = {'daily_risk':1000.,'daily_target':1000.,'commission_per_lot':0.,
                    'slippage_points':0.,'validation_policy':'forward_demo'}
        engine.executor.activate('MANUAL_DEMO',settings)
        engine.settings=dict(engine.risk.settings)
        engine.status='MANUAL_DEMO'
        engine.scanner.step(99)
        engine.last_deep=now
        engine.last_learning=now
        fixtures=[]
        for side,symbol,sl,tp in (('BUY','EURUSD.demo',1.075,1.095),('SELL','STOCK.A',211.,207.)):
            price=engine.broker.tick(symbol)['ask' if side=='BUY' else 'bid']
            p={'id':'browser-'+side.lower(),'symbol':symbol,'side':side,'sl':sl,'tp':tp,
               'strategy_id':'engulfing','timeframe':'M1','entry_zone':[price-.01,price+.01],
               'qualified':False,'news_ok':True,'signal_validated':True,'validation_policy':'forward_demo',
               'data_time':now-1,'expires_at':now+600,'reason':'Isolated deterministic UI signal fixture'}
            fixtures.append(p)
            engine.manual[p['id']]=p
        engine.opportunities=[{'proposal':p,'intent_id':p['id'],'symbol':p['symbol'],'eligible':True,
                               'decision':p['side'],'expires_at':p['expires_at'],'as_of':now} for p in fixtures]
        engine._publish()
        engine.start_worker(auto_connect=False)
        server=LocalServer(engine,ROOT/'ui');url=server.start()
        try:
            with sync_playwright() as api:
                browser=api.chromium.launch(headless=True)
                page=browser.new_page()
                errors=[]
                page.on('pageerror',lambda error: errors.append(str(error)))
                page.goto(url)
                page.locator('.nav-item[data-view="positions"]').focus();page.keyboard.press('Enter')
                for p in fixtures:
                    side=p['side'].lower()
                    approval=page.locator(f'[data-approve="{p["id"]}"]')
                    approval.focus();page.keyboard.press('Enter')
                    page.locator('#confirm-dialog').wait_for(state='visible')
                    page.keyboard.press('Escape')
                    page.locator('#confirm-dialog').wait_for(state='hidden')
                    checks.append({'name':'keyboard_escape_cancels_'+side,'group':'keyboard',
                                   'passed':not any(x['payload'].get('proposal',{}).get('id')==p['id'] for x in engine.store.intents())})
                    approval.focus();page.keyboard.press('Enter')
                    page.locator('#confirm-dialog').wait_for(state='visible')
                    trapped=[]
                    for _ in range(4):
                        page.keyboard.press('Tab')
                        trapped.append(page.evaluate("!!document.activeElement.closest('#confirm-dialog')"))
                    for _ in range(4):
                        page.keyboard.press('Shift+Tab')
                        trapped.append(page.evaluate("!!document.activeElement.closest('#confirm-dialog')"))
                    checks.append({'name':'keyboard_dialog_focus_trap_'+side,'group':'keyboard','passed':all(trapped)})
                    checks.append({'name':'keyboard_dialog_focus_visible_'+side,'group':'keyboard',
                        'passed':page.evaluate("() => document.activeElement.matches(':focus-visible') && getComputedStyle(document.activeElement).outlineStyle!=='none'")})
                    with page.expect_response(lambda response: response.url.endswith('/api/action')) as receipt:
                        page.locator('#confirm-accept').focus();page.keyboard.press('Enter')
                    result=receipt.value.json()
                    matching=[x for x in engine.store.intents() if x['payload'].get('proposal',{}).get('id')==p['id']]
                    checks.append({'name':'submit_'+side,'group':'ui_execution',
                                   'passed':receipt.value.status==200 and result.get('ok') is True and
                                            len(matching)==1 and matching[0]['state']=='FILLED',
                                   'receipt':result,'intent_ids':[x['id'] for x in matching]})
                    page.locator('#refresh-button').click()
                    page.locator('#positions-table').get_by_text(p['symbol'],exact=True).wait_for()
                    checks.append({'name':'submit_'+side+'_result_visible','group':'ui_execution','passed':True})
                sent_before=len(engine.broker.sent)
                page.locator('.nav-item[data-view="setup"]').focus();page.keyboard.press('Enter')
                page.locator('#setup-advanced > summary').focus();page.keyboard.press('Enter')
                page.locator('#reconcile-button').focus()
                page.keyboard.press('Tab');page.keyboard.press('Shift+Tab')
                checks.append({'name':'keyboard_reconcile_tab_order','group':'keyboard',
                    'passed':page.locator('#reconcile-button').evaluate("e=>e===document.activeElement")})
                checks.append({'name':'keyboard_reconcile_focus_visible','group':'keyboard',
                    'passed':page.locator('#reconcile-button').evaluate("e=>e===document.activeElement && e.matches(':focus-visible') && getComputedStyle(e).outlineStyle!=='none'")})
                with page.expect_response(lambda response: response.url.endswith('/api/action')) as receipt:
                    page.locator('#reconcile-button').focus();page.keyboard.press('Enter')
                response=receipt.value.json()
                checks.append({'name':'run_reconciliation','group':'ui_reconciliation',
                               'passed':response.get('ok') is True and response.get('result',{}).get('ok') is True
                                        and len(engine.broker.sent)==sent_before,'receipt':response})
                page.locator('.nav-item[data-view="audit"]').click()
                page.locator('#refresh-button').click()
                page.locator('#events-list').get_by_text('مطابقة العمليات مع الوسيط',exact=True).first.wait_for()
                checks.append({'name':'reconciliation_audit_visible','group':'ui_reconciliation',
                               'passed':any(x['event']=='RECONCILIATION' for x in engine.store.recent_audit())})
                checks.append({'name':'execution_fixture_no_js_errors','group':'ui_execution','passed':not errors,'errors':errors})
                checks.append({'name':'two_synthetic_orders_only','group':'ui_execution','passed':len(engine.broker.sent)==2})
                browser.close()
        finally:
            engine.stop_worker();server.stop()
            engine.store.close();engine.cache.db.close();engine.news.db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--axe', required=True)
    args = parser.parse_args()
    checks = []; audits = []; console_errors = []; browser_console = []; report = {}
    screenshots = ROOT/'reports/browser'
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='quant-browser-isolated-') as data:
        engine = Engine(ROOT, Path(data))
        engine.start_worker(auto_connect=False)
        server = LocalServer(engine, ROOT/'ui')
        url = server.start()
        try:
            with sync_playwright() as browser_api:
                browser = browser_api.chromium.launch(headless=True)
                context = browser.new_context(viewport={'width':1440, 'height':1000}, bypass_csp=True,
                                              reduced_motion='reduce')
                page = context.new_page()
                page.on('pageerror', lambda error: console_errors.append(str(error)))
                page.on('console', lambda message: browser_console.append({'text':message.text,'location':message.location}) if message.type=='error' else None)
                page.goto(url)
                page.wait_for_function("document.querySelector('#last-update').textContent !== 'لم تُستلم بيانات بعد'")
                response = context.request.get(url+'/api/state')
                checks.append({'name':'unauthenticated_session_rejected', 'passed':response.status==401})
                authorized = page.evaluate("""async () => {
                    const token=document.querySelector('meta[name="nexus-token"]').content;
                    return (await fetch('/api/state',{headers:{'X-Nexus-Token':token}})).status;
                }""")
                checks.append({'name':'page_token_session_authenticated', 'passed':authorized==200})
                checks.append({'name':'disconnected_no_account', 'passed':engine.snapshot()['account'] is None})
                page.locator('.nav-item[data-view="positions"]').click()
                checks.append({'name':'empty_positions_have_explanation',
                               'passed':bool(page.locator('#positions-table').inner_text().strip())})
                page.route('**/api/state', lambda route: route.fulfill(status=503, json={'ok':False,'error':'Intentional isolated network failure'}), times=1)
                page.locator('#refresh-button').focus();page.keyboard.press('Enter')
                page.locator('#service-error').wait_for(state='visible')
                page.screenshot(path=str(screenshots/'keyboard-error-before.png'),full_page=False)
                error_focus=page.locator('#refresh-button').evaluate("e => e===document.activeElement && e.matches(':focus-visible') && getComputedStyle(e).outlineStyle!=='none'")
                checks.append({'name':'keyboard_error_focus_visible','group':'keyboard','passed':error_focus})
                page.keyboard.press('Tab')
                error_next=page.evaluate("document.activeElement.id!=='refresh-button' && !!document.activeElement.getClientRects().length")
                page.keyboard.press('Shift+Tab')
                checks.append({'name':'keyboard_error_tab_order','group':'keyboard','passed':error_next and page.locator('#refresh-button').evaluate("e=>e===document.activeElement")})
                page.keyboard.press('Escape')
                checks.append({'name':'keyboard_error_escape_does_not_hide_failure','group':'keyboard','passed':page.locator('#service-error').is_visible()})
                checks.append({'name':'network_error_is_visible','passed':True})
                page.locator('#refresh-button').focus();page.keyboard.press('Enter')
                page.locator('#service-error').wait_for(state='hidden')
                page.screenshot(path=str(screenshots/'keyboard-error-after.png'),full_page=False)
                checks.append({'name':'keyboard_error_enter_recovers','group':'keyboard','passed':True})
                checks.append({'name':'manual_refresh_recovers_after_network_error','passed':True})
                held = []
                loading_page = context.new_page()
                loading_page.route('**/api/state', lambda route: held.append(route))
                with loading_page.expect_request('**/api/state'):
                    loading_page.goto(url, wait_until='domcontentloaded')
                checks.append({'name':'initial_loading_blocks_trading',
                               'passed':loading_page.locator('#start-button').is_disabled() and bool(held)})
                for route in held:
                    route.continue_()
                loading_page.unroute('**/api/state')
                loading_page.close()

                keyboard_screens(page, checks, screenshots)
                drift_dashboard_scenario(page, engine, checks, screenshots)

                for language in ('ar', 'en'):
                    page.locator('#language-select').select_option(language)
                    expected_dir = 'rtl' if language == 'ar' else 'ltr'
                    checks.append({'name':'document_direction_'+language,
                                   'passed':page.locator('html').get_attribute('dir')==expected_dir})
                    for view in ('overview','markets','research','news','positions','performance','knowledge','audit','setup'):
                        page.locator(f'.nav-item[data-view="{view}"]').click()
                        page.locator('#view-'+view).wait_for(state='visible')
                        checks.append({'name':f'navigation_{language}_{view}', 'passed':True})
                        if view == 'research':
                            checks.append({'name':'chart_has_all_21_periods_'+language,
                                           'passed':page.locator('#chart-timeframe option').count()==21})
                        page.add_script_tag(path=args.axe)
                        result = page.evaluate("""async () => await axe.run(document, {
                            runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}
                        })""")
                        audits.append({'view':view,'language':language,'theme':'forest','width':1440,
                                       'violations':[{'id':v['id'],'impact':v['impact'],
                                                      'nodes':[{'target':n['target'],'summary':n.get('failureSummary','')} for n in v['nodes']]}
                                                     for v in result['violations']],
                                       'incomplete_count':len(result['incomplete'])})

                page.locator('.nav-item[data-view="overview"]').click()
                for language in ('ar', 'en'):
                    page.locator('#language-select').select_option(language)
                    for width in (375,768,1440):
                        page.set_viewport_size({'width':width,'height':900})
                        for theme in ('forest','midnight','graphite','sand','white'):
                            page.locator('#theme-select').select_option(theme)
                            page.evaluate('window.scrollTo(0,0)')
                            page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                            dimensions = page.evaluate("({width:innerWidth, scroll:document.documentElement.scrollWidth})")
                            checks.append({'name':f'no_page_overflow_{language}_{width}_{theme}',
                                           'passed':dimensions['scroll']<=dimensions['width']+1,
                                           'dimensions':dimensions})
                            geometry = page.evaluate("""() => ({
                                headerBottom:document.querySelector('.topbar').getBoundingClientRect().bottom,
                                firstCardTop:document.querySelector('.account-grid .stat-card').getBoundingClientRect().top
                            })""")
                            checks.append({'name':f'header_does_not_cover_content_{language}_{width}_{theme}',
                                           'passed':geometry['firstCardTop']>=geometry['headerBottom'],
                                           'geometry':geometry})
                            result = page.evaluate("""async () => await axe.run(document, {
                                runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}
                            })""")
                            audits.append({'view':'overview','language':language,'theme':theme,'width':width,
                                           'violations':[{'id':v['id'],'impact':v['impact'],
                                                          'nodes':[{'target':n['target'],'summary':n.get('failureSummary','')} for n in v['nodes']]}
                                                         for v in result['violations']],
                                           'incomplete_count':len(result['incomplete'])})
                        page.screenshot(path=str(screenshots/f'overview-{language}-{width}.png'), full_page=True)
                checks.append({'name':'no_javascript_page_errors','passed':not console_errors})
                page.locator('.nav-item[data-view="setup"]').click()
                page.locator('#setup-advanced > summary').click()
                page.locator('#simulation-button').click()
                page.locator('#confirm-accept').click()
                page.locator('#simulation-banner').wait_for(state='visible')
                checks.append({'name':'synthetic_mode_requires_explicit_confirmation','passed':engine.broker.is_simulation})
                page.locator('.nav-item[data-view="research"]').click()
                page.locator('#chart-symbol').select_option('GOLD#')
                page.locator('#chart-timeframe').select_option('M1')
                original_bars = engine.broker.bars
                sample = original_bars('GOLD#','M1',10)
                engine.broker.bars = lambda symbol, tf, count: copy.deepcopy(sample) if symbol=='GOLD#' and tf=='M1' else original_bars(symbol, tf, count)
                with page.expect_response(lambda response: response.url.endswith('/api/action')) as short_receipt:
                    page.locator('#chart-load').click()
                checks.append({'name':'short_chart_action_completes','passed':short_receipt.value.status==200})
                page.wait_for_function("document.querySelector('#chart-title').textContent.includes('GOLD#') && document.querySelector('#chart-title').textContent.includes('M1')")
                page.wait_for_function("document.querySelectorAll('#research-cards .research-card').length===58")
                checks.append({'name':'short_chart_shows_58_missing_nonactionable_models',
                               'passed':len(engine.chart['cards'])==58 and all(c['status']=='DATA_MISSING' and not c['actionable'] for c in engine.chart['cards'])})
                page.locator('#research-model-details > summary').click()
                advisory_index=next(i for i,c in enumerate(engine.chart['cards']) if c['strategy_id']=='four_school_confluence')
                checks.append({'name':'advisory_confluence_card_visible_nonactionable','group':'advisory',
                               'passed':page.locator('#research-cards .research-card').nth(advisory_index).is_visible()
                                        and engine.chart['cards'][advisory_index]['actionable'] is False})
                previous = copy.deepcopy(engine.chart)
                invalid_sample = sample+[dict(sample[-1], time=engine.clock())]
                engine.broker.bars = lambda symbol, tf, count: copy.deepcopy(invalid_sample) if symbol=='GOLD#' and tf=='M1' else original_bars(symbol, tf, count)
                with page.expect_response(lambda response: response.url.endswith('/api/action')) as future_receipt:
                    page.locator('#chart-load').click()
                page.locator('#toast-region .toast').last.wait_for(state='visible')
                checks.append({'name':'future_chart_rejected_without_replacing_previous_snapshot',
                               'passed':engine.chart==previous and future_receipt.value.status in (400,409)})
                engine.broker.bars = original_bars
                unexpected_console = [item for item in browser_console if not
                                      (('503' in item['text'] and '/api/state' in item['location'].get('url','')) or
                                       (('409' in item['text'] or '400' in item['text']) and '/api/action' in item['location'].get('url','')))]
                checks.append({'name':'no_unexpected_browser_console_errors','passed':not unexpected_console,
                               'errors':unexpected_console})
                browser.close()
        finally:
            engine.stop_worker()
            server.stop()
            if engine.store:
                engine.store.close()
            engine.cache.db.close()
            engine.news.db.close()
    execution_scenarios(checks)
    report = {'type':'ISOLATED_BROWSER_UI_E2E', 'utc':datetime.now(UTC).isoformat(),
              'checks':checks,'axe_audits':audits,'javascript_errors':console_errors,'browser_console':browser_console,
              'broker_orders_sent':0,'synthetic_orders_sent':2,'real_terminal_connected':False,
              'not_covered':['actual MT5 terminal submission (intentionally isolated)', 'manual screen-reader audit'],
              'passed':all(c['passed'] for c in checks) and not any(a['violations'] for a in audits)}
    (ROOT/'reports/browser-e2e.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checks':len(checks),'failed_checks':sum(not c['passed'] for c in checks),
                      'axe_scans':len(audits),'axe_violations':sum(len(a['violations']) for a in audits),
                      'javascript_errors':len(console_errors),'passed':report['passed']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
