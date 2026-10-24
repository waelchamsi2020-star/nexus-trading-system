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


def navigate(page, view):
    """Open the secondary disclosure before clicking a low-frequency view."""
    if view in ('news','knowledge','audit') and not page.locator('#nav-more').evaluate('(element) => element.open'):
        page.locator('#nav-more > summary').click()
    page.locator(f'.nav-item[data-view="{view}"]').click()


def keyboard_screens(page, checks, screenshots):
    """Real keyboard events in Chromium; not a human screen-reader audit."""
    for view in ('overview','markets','research','news','positions','performance','knowledge','audit','setup'):
        if view in ('news','knowledge','audit'):
            more=page.locator('#nav-more')
            if not more.evaluate('(element) => element.open'):
                summary=more.locator(':scope > summary')
                summary.focus();page.keyboard.press('Enter')
            checks.append({'name':'keyboard_open_more_navigation','group':'keyboard',
                           'passed':more.evaluate('(element) => element.open')})
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
        navigate(page,'knowledge')
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
                navigate(page,'audit')
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
        # Browser QA must never spend a user's external provider quota.
        engine.llm_research.environ = {}
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
                primary_nav=page.locator('nav > .nav-item[data-view]')
                technical_nav=page.locator('#nav-more .nav-item[data-view="knowledge"], #nav-more .nav-item[data-view="news"], #nav-more .nav-item[data-view="audit"]')
                checks.append({'name':'primary_navigation_is_compact','group':'ui_layout',
                               'passed':primary_nav.count()==5 and all(primary_nav.nth(i).is_visible() for i in range(primary_nav.count()))})
                checks.append({'name':'technical_sources_are_secondary','group':'ui_layout',
                               'passed':not page.locator('#nav-more').evaluate('(element) => element.open')
                                        and all(not technical_nav.nth(i).is_visible() for i in range(technical_nav.count()))})
                more_summary=page.locator('#nav-more > summary')
                more_summary.focus();page.keyboard.press('Enter')
                checks.append({'name':'secondary_navigation_opens_by_keyboard','group':'ui_layout',
                               'passed':page.locator('#nav-more').evaluate('(element) => element.open')
                                        and all(technical_nav.nth(i).is_visible() for i in range(technical_nav.count()))})
                page.keyboard.press('Enter')
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
                navigate(page,'news')
                page.locator('#view-news').wait_for(state='visible')
                page.locator('#llm-research-details').evaluate("element => element.open = true")
                page.locator('#llm-research-run').scroll_into_view_if_needed()
                page.locator('#llm-research-providers').get_by_text('Google Gemini',exact=True).wait_for()
                with page.expect_response(lambda response: response.url.endswith('/api/action')) as llm_receipt:
                    page.locator('#llm-research-run').click()
                if llm_receipt.value.status != 200:
                    raise AssertionError(f"LLM shadow action returned HTTP {llm_receipt.value.status}")
                page.wait_for_function("document.querySelector('#llm-research-status').textContent.includes('آخر تحليل')")
                checks.append({'name':'llm_research_missing_keys_fail_closed_no_network','group':'llm_shadow',
                               'passed':len(engine.llm_research.status()['results'])==3
                                        and all(row['status']=='CONFIG_REQUIRED' for row in engine.llm_research.status()['results'])
                                        and engine.llm_research.status()['execution_use']=='NONE',
                               'provider_results':engine.llm_research.status()['results']})
                checks.append({'name':'llm_research_ui_disclaims_execution_authority','group':'llm_shadow',
                               'passed':'لا يغيّر قرار اللجنة أو المخاطر أو الأوامر' in page.locator('#llm-research-details').inner_text()})
                page.screenshot(path=str(screenshots/'llm-shadow-unconfigured.png'),full_page=True)
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
                        navigate(page,view)
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
                    for width in (375,768,1024,1440,1920):
                        page.set_viewport_size({'width':width,'height':900})
                        for theme in ('neural','forest','midnight','graphite','sand','white'):
                            page.locator('#theme-select').select_option(theme)
                            page.evaluate('window.scrollTo(0,0)')
                            page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                            dimensions = page.evaluate("({width:innerWidth, scroll:document.documentElement.scrollWidth})")
                            checks.append({'name':f'no_page_overflow_{language}_{width}_{theme}',
                                           'passed':dimensions['scroll']<=dimensions['width']+1,
                                           'dimensions':dimensions})
                            geometry = page.evaluate("""() => {
                                const rect = (selector) => {
                                    const r = document.querySelector(selector).getBoundingClientRect();
                                    return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width};
                                };
                                return {view:rect('#view-overview.active'),row:rect('#view-overview > .overview-bottom'),
                                    scan:rect('.scan-overview'),decision:rect('.committee-preview'),width:innerWidth};
                            }""")
                            row, view = geometry['row'], geometry['view']
                            scan, decision = geometry['scan'], geometry['decision']
                            contained = (row['width'] >= view['width'] - 2 and
                                         row['left'] >= view['left'] - 2 and row['right'] <= view['right'] + 2)
                            disjoint = (scan['right'] <= decision['left'] + 1 or
                                        decision['right'] <= scan['left'] + 1 or
                                        scan['bottom'] <= decision['top'] + 1 or
                                        decision['bottom'] <= scan['top'] + 1)
                            if width <= 900:
                                sized = scan['width'] >= row['width'] - 2 and decision['width'] >= row['width'] - 2
                            else:
                                sized = scan['width'] >= 250 and decision['width'] >= 240
                            checks.append({'name':f'overview_scan_decision_geometry_{language}_{width}_{theme}',
                                           'passed':contained and disjoint and sized,'geometry':geometry})
                            integrated_geometry = page.evaluate("""() => {
                                const body=document.body;
                                const wasIntegrated=body.classList.contains('demo-integrated');
                                body.classList.add('demo-integrated');
                                const activeView=document.querySelector('#view-overview');
                                let demoPanel=document.querySelector('#demo-execution-panel');
                                const createdDemoPanel=!demoPanel;
                                const priorHidden=demoPanel?.hidden;
                                if(!demoPanel){
                                    demoPanel=document.createElement('article');
                                    demoPanel.id='demo-execution-panel';demoPanel.className='panel';
                                    demoPanel.textContent='حالة تداول تجريبية للاختبار';activeView.append(demoPanel);
                                }else{demoPanel.hidden=false;}
                                const rect=(selector)=>{
                                    const e=document.querySelector(selector),r=e.getBoundingClientRect();
                                    return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width};
                                };
                                const row=rect('#view-overview > .overview-bottom');
                                const view=rect('#view-overview.active');
                                const scan=rect('.scan-overview'),decision=rect('.committee-preview');
                                const execution=rect('#demo-execution-panel');
                                const account=rect('#view-overview > .account-grid');
                                const result={display:getComputedStyle(document.querySelector('#view-overview > .overview-bottom')).display,
                                    hiddenControls:getComputedStyle(document.querySelector('#view-overview > .overview-grid')).display,
                                    row,view,scan,decision,execution,account,width:innerWidth,wasIntegrated};
                                if(createdDemoPanel) demoPanel.remove(); else demoPanel.hidden=priorHidden;
                                if(!wasIntegrated) body.classList.remove('demo-integrated');
                                return result;
                            }""")
                            integrated_contained = (integrated_geometry['display']=='grid' and
                                integrated_geometry['hiddenControls']=='none' and
                                integrated_geometry['row']['width']>=integrated_geometry['view']['width']-2)
                            integrated_disjoint = (
                                integrated_geometry['scan']['right']<=integrated_geometry['decision']['left']+1 or
                                integrated_geometry['decision']['right']<=integrated_geometry['scan']['left']+1 or
                                integrated_geometry['scan']['bottom']<=integrated_geometry['decision']['top']+1 or
                                integrated_geometry['decision']['bottom']<=integrated_geometry['scan']['top']+1)
                            integrated_sized = (
                                integrated_geometry['scan']['width']>=integrated_geometry['row']['width']-2 and
                                integrated_geometry['decision']['width']>=integrated_geometry['row']['width']-2
                                if width<=900 else
                                integrated_geometry['scan']['width']>=250 and
                                integrated_geometry['decision']['width']>=240)
                            integrated_execution_sized = (
                                integrated_geometry['execution']['width']>=integrated_geometry['view']['width']-2 and
                                integrated_geometry['execution']['left']>=integrated_geometry['view']['left']-2 and
                                integrated_geometry['execution']['right']<=integrated_geometry['view']['right']+2 and
                                integrated_geometry['execution']['top']>=integrated_geometry['account']['bottom']-2)
                            checks.append({'name':f'demo_integrated_overview_geometry_{language}_{width}_{theme}',
                                'passed':integrated_contained and integrated_disjoint and integrated_sized and integrated_execution_sized,
                                'geometry':integrated_geometry})
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
                        page.locator('#theme-select').select_option('neural')
                        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                        page.screenshot(path=str(screenshots/f'overview-{language}-{width}.png'), full_page=True)
                page.locator('#language-select').select_option('ar')
                page.evaluate("""() => window.renderDemoPanel({running:false,error:null,
                    stop_reason:'DEMO_ACCOUNT_TRADING_PERMISSION_DISABLED',user_paused:false,
                    status:{models:58,symbol:'EURUSD',timeframe:'M1',open_positions:0,daily_profit:0},
                    last_reasons:{NO_TRIGGER:58},last_bar:null})""")
                checks.append({'name':'executor_status_is_prominent_and_not_duplicated','group':'ui_status',
                    'passed':page.locator('#header-execution-mode').inner_text()=='التنفيذ متوقف'
                             and page.locator('#header-execution-mode').get_attribute('title').endswith('DEMO_ACCOUNT_TRADING_PERMISSION_DISABLED')
                             and page.locator('#demo-runtime').count()==0
                             and page.locator('#demo-execution-panel .panel-heading').inner_text()=='التداول'})
                page.evaluate("""() => window.renderDemoPanel({running:true,error:'DEMO_ACCOUNT_TRADING_PERMISSION_DISABLED',
                    limits:{revision:1,values:{daily_loss_amount:10,daily_profit_amount:10,per_trade_loss_amount:5,per_trade_profit_amount:1}},
                    status:{},last_reasons:{}})""")
                checks.append({'name':'unavailable_executor_detail_stays_in_top_accessible_status','group':'ui_status',
                    'passed':page.locator('#header-execution-mode').inner_text()=='حالة المنفّذ غير متاحة'
                             and 'DEMO_ACCOUNT_TRADING_PERMISSION_DISABLED' in page.locator('#header-execution-mode').get_attribute('aria-label')
                             and page.locator('#demo-execution-panel .panel-heading').inner_text()=='التداول'
                             and page.locator('#demo-toggle').is_disabled()
                             and page.locator('#demo-limits-form [type="submit"]').is_disabled()
                             and page.locator('#demo-decision').inner_text().startswith('تعذرت قراءة')})
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
