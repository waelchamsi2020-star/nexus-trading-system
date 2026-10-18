/* Static JavaScript runtime checks using a small DOM substitute.
   This does not launch or imitate a browser and is not visual verification. */
const fs=require('fs');
const path=require('node:path');
const vm=require('vm');
const assert=require('node:assert/strict');
const uiRoot=fs.existsSync(path.join(__dirname,'../ui/index.html'))?path.join(__dirname,'../ui'):path.join(__dirname,'../outputs/NEXUS/ui');
const html=fs.readFileSync(path.join(uiRoot,'index.html'),'utf8');
const source=fs.readFileSync(path.join(uiRoot,'app.js'),'utf8');
const css=fs.readFileSync(path.join(uiRoot,'style.css'),'utf8');
assert(css.includes('#daily-authorization-options>.form-grid{grid-template-columns:minmax(0,1fr)'), 'daily loss and profit fields must stack without changing scalp pairs');
const advanced=html.slice(html.indexOf('<details id="setup-advanced"'), html.indexOf('</section>',html.indexOf('<details id="setup-advanced"')));
assert(advanced.includes('id="simulation-button"') && advanced.includes('id="service-details"'), 'simulation and diagnostics remain available in collapsed advanced settings');
assert(!/^<details[^>]*\bopen\b/.test(advanced), 'advanced setup must start collapsed');
assert(html.indexOf('id="connect-form"')<html.indexOf('id="setup-advanced"'), 'MT5 connection must remain immediately accessible');
for(const id of ['news-source-details','coverage-details','quant-details','rule-learning-details','chart-learning-details','intent-history-details','research-model-details']){
  assert(new RegExp(`<details[^>]*id="${id}"[^>]*>`).test(html),`${id} must remain reachable as a disclosure`);
  assert(!new RegExp(`<details[^>]*id="${id}"[^>]*\\bopen\\b`).test(html),`${id} should start collapsed`);
}
assert(html.indexOf('class="overview-bottom"')<html.indexOf('class="overview-grid"'),'scan and decision must precede trading columns in reading and keyboard order');
for(const id of ['overview-scan','committee-summary','scan-button'])assert.equal([...html.matchAll(new RegExp(`id="${id}"`,'g'))].length,1,`${id} must remain unique after moving panels`);
const ruleLanguage={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(uiRoot,'i18n.js'),'utf8'),ruleLanguage);
assert.equal(ruleLanguage.window.NEXUS_I18N.translate('يجب أن تكون أسعار التنفيذ موجبة ومحدودة','en'),'Execution prices must be finite and positive.');
assert.equal(ruleLanguage.window.NEXUS_I18N.translate('يجب أن تكون أسعار التنفيذ موجبة ومحدودة','ar'),'يجب أن تكون أسعار التنفيذ موجبة ومحدودة');
const i18nSource=fs.readFileSync(path.join(uiRoot,'i18n.js'),'utf8');
assert.equal(ruleLanguage.window.NEXUS_I18N.translate('08:47  بتوقيت دبي','en'),'08:47 UTC+4');
const i18nContext={window:{}};vm.createContext(i18nContext);vm.runInContext(i18nSource,i18nContext,{filename:'i18n.js'});
const translateEnglish=(value)=>i18nContext.window.NEXUS_I18N.translate(value,'en');
// Repeated polling must not rewrite every translated hidden-view text node.
let translationWrites=0,translationText='مصفوفة تقاطع المدارس';
const translationNode={get nodeValue(){return translationText;},set nodeValue(v){translationWrites++;translationText=v;}};
const translationRoot={querySelectorAll:()=>[]};
const applyContext={window:{},NodeFilter:{SHOW_TEXT:4},document:{documentElement:{},title:'',createTreeWalker:()=>{let read=false;return {nextNode:()=>read?null:(read=true,translationNode)};}}};
vm.createContext(applyContext);vm.runInContext(i18nSource,applyContext);
applyContext.window.NEXUS_I18N.apply(translationRoot,'en');assert.equal(translationText,'School confluence matrix');
const firstWrites=translationWrites;applyContext.window.NEXUS_I18N.apply(translationRoot,'en');assert.equal(translationWrites,firstWrites);
translationText='مخاطرة سكالب مستقلة';applyContext.window.NEXUS_I18N.apply(translationRoot,'en');assert(!/[\u0600-\u06ff]/.test(translationText));
applyContext.window.NEXUS_I18N.apply(translationRoot,'ar');assert.equal(translationText,'مخاطرة سكالب مستقلة','changed source text remains restorable');
const idMatches=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);
assert.equal(new Set(idMatches).size,idMatches.length,'HTML IDs must be unique');
for(const m of source.matchAll(/\$\('([^']+)'\)/g))assert(idMatches.includes(m[1]),`missing HTML control ${m[1]}`);
assert(!html.includes('id="commission-input"')&&!html.includes('id="slippage-input"'),'cost entry fields must be removed from the interface');
assert(!html.includes('id="decision-protocol-input"')&&!html.includes('id="forward-demo-input"'),'single supported Demo policy must not expose an invalid selector or historical toggle');
assert(!source.includes("$('decision-protocol-input')")&&!source.includes("$('forward-demo-input')"),'removed policy controls must not be read during activation');
assert(!html.includes('أدخل عمولة الوسيط')&&!html.includes('افتراضات التكاليف'),'the cost entry panel must be removed');
assert(!source.includes("$('commission-input')")&&!source.includes("$('slippage-input')"),'start and backtest must not depend on removed cost fields');
assert(html.indexOf('id="scalp-active-status"')<html.indexOf('id="scalp-options"'),'actual scalp status must stay visible when options are collapsed');
assert(!/id="(?:risk|target)-input"[^>]+\bvalue=/.test(html),'no fixed risk or target');
assert(!/https?:\/\//.test(html),'no external asset requests');
assert(!/localStorage[^\n]*(token|auth)/i.test(source),'authentication must not be persisted');
assert(!html.includes('DEMO ONLY'),'Arabic source markup must not contain an English demo label');
assert(!html.includes('>English</option>'),'Arabic source markup must name the English choice in Arabic');
assert(!html.includes('نسبة من Equity'),'Arabic source markup must not mix Equity into the percentage label');
assert(source.includes("'Activation requested':'جارٍ التحقق من طلب التفعيل الجديد'"),'activation status must have a complete Arabic translation');
assert(i18nSource.includes("'تجريبي فقط':'DEMO ONLY'") && i18nSource.includes("'الإنجليزية':'English'"),'English mode must translate language and demo labels');
assert(source.includes('first(e.data,e.details,e.payload)'),'stored audit payloads must be rendered, not discarded');
assert(source.includes('JSON.stringify(localizedData(details),null,2)'),'stored diagnostic details must localize dynamic strings');
assert(source.includes("reason:['السبب','Reason']") && source.includes('diagnosticKey(k,index)'),'diagnostic keys must localize independently from the exported schema');
assert(source.includes('Additional counted exposure:') && source.includes('Estimated net = attributed realized net'),'English risk summaries must be authored completely in English');
const staticTexts=[...html.matchAll(/>([^<>]+)</g)].map(x=>x[1].replace(/\s+/g,' ').trim()).filter(Boolean);
const staticAttrs=[...html.matchAll(/(?:title|placeholder|aria-label)="([^"]+)"/g)].map(x=>x[1]);
for(const text of [...staticTexts,...staticAttrs])assert(!/[\u0600-\u06ff]/.test(translateEnglish(text)),`English mode left Arabic text: ${text}`);
const dynamicTexts=[
  'داو والتحليل الكلاسيكي','موجات إليوت','الأنماط الانعكاسية الكلاسيكية','الأنماط الهندسية','التحقق التاريخي قيد التنفيذ','السوق مغلق حسب جلسة الوسيط',
  'القبول النهائي لم يجتز بعد؛ راجع تقرير التحقق المرفق.','الاختبار: —',
  '100 × عدد الشروط المتحققة ÷ إجمالي الشروط؛ صفر عند غياب الشروط. هذه درجة تحقق القواعد وليست احتمال نجاح',
  '300 شمعة داخل اليوم لا تكفي لإثبات الموسمية','RSI بمتوسط ربح وخسارة بسيط متحرك وليس تنعيم وايلدر',
  'أعلى درجة فقط لكل عائلة أدلة مترابطة؛ يلزم عائلتان على الأقل، ومعايير كمية ثابتة',
  'تجميع الأدلة يقلل العد المكرر للمؤشرات المترابطة ولا يثبت استقلالها الإحصائي',
  'محرك المخاطر المستقل يملك حق الرفض النهائي؛ اللجنة لا ترسل الأوامر','جلسة صناعية للاختبار','عقد صناعي للاختبارات',
  'متصل للقراءة. التفويض يبدأ فقط بعد إدخال حدود اليوم والضغط على ابدأ.','بدأ فحص جميع رموز المنصة؛ تابع عداد الإنجاز.',
  'اعتمد تفويض Demo وحدود اليوم المحفوظة. ينتظر النظام فرصة تستوفي جميع الفحوص.','جُمعت ملفات التشخيص محليًا. لا ترفع تلقائيًا. راجع أرقام الحساب والتذاكر قبل مشاركتها.'
];
for(const dynamicText of dynamicTexts)assert(!/[\u0600-\u06ff]/.test(translateEnglish(dynamicText)),`English dynamic translation missing: ${dynamicText}`);
assert.equal(translateEnglish('جلسة صناعية للاختبار'),'Synthetic test session.');
assert.equal(translateEnglish('عقد صناعي للاختبارات'),'Synthetic test contract.');
assert(!/[\u0600-\u06ff]/.test(translateEnglish('رسالة خلفية جديدة لم تدخل القاموس بعد')),'English fallback must never mix Arabic text');
assert(source.includes('toast(tr(success || result.message))'),'reviewed localized action text must take precedence over backend source-language success messages');

function environment(fixture,preferences={},network={}){
  const nodes=new Map(),created=[],calls=[],documentHandlers={};
  const timers=new Map();let timerId=0;
  const fakeSetTimeout=(fn,delay)=>{
    if(network.controlTimers){const id=++timerId;timers.set(id,{fn,delay});return id;}
    if(delay===400)Promise.resolve().then(fn);return 1;
  };
  const fakeClearTimeout=id=>{if(network.controlTimers)timers.delete(id);};
  class Element{
    constructor(tag='div',id=''){this.tagName=tag.toUpperCase();this._id='';this.id=id;this.value='';this.textContent='';this.innerHTML='';this.className='';this.hidden=false;this.disabled=false;this.checked=false;this.style={setProperty(name,value){this[name]=value;}};this.dataset={};this.handlers={};this.clientWidth=0;this.clientHeight=0;this.children=[];this.classList={toggle(){},remove(){},contains:()=>false};}
    set id(v){this._id=v;if(v)nodes.set(v,this);}get id(){return this._id;}
    setAttribute(name,value){this.attributes??={};this.attributes[name]=String(value);}
    getAttribute(name){return this.attributes?.[name]??null;}
    addEventListener(type,fn){(this.handlers[type]??=[]).push(fn);}
    appendChild(el){this.children.push(el);}insertAdjacentElement(_,el){this.children.push(el);}
    closest(){return null;}matches(){return false;}focus(){}scrollIntoView(){}remove(){}
  }
  for(const m of html.matchAll(/<([\w]+)[^>]*\bid="([^"]+)"[^>]*>/g))new Element(m[1],m[2]);
  nodes.get('symbol-filter').value='all';nodes.get('event-filter').value='all';nodes.get('chart-timeframe').value='H1';nodes.get('knowledge-filter').value='all';
  const shell=new Element(),setupPanel=new Element(),radios=['AUTO_DEMO','MANUAL_DEMO'].map(value=>{const e=new Element('input');e.value=value;e.checked=value==='AUTO_DEMO';return e;});
  const unitButtons=['money','percent'].map(unit=>{const e=new Element('button');e.dataset.unit=unit;return e;});
  const nav=Object.keys({overview:1,markets:1,research:1,news:1,positions:1,performance:1,knowledge:1,audit:1,setup:1}).map(view=>{const e=new Element('button');e.dataset.view=view;return e;});
  const views=nav.map(n=>new Element('section',`view-${n.dataset.view}`));
  const get=(id)=>{assert(nodes.has(id),`runtime requested unknown element ${id}`);return nodes.get(id);};
  const documentElement=new Element('html'),body=new Element('body');
  const document={
    documentElement,body,
    getElementById:get,
    createElement:(tag)=>{const e=new Element(tag);created.push(e);return e;},
    querySelector:(selector)=>{if(selector==='meta[name="nexus-token"]')return {content:'STATIC_TEST_TOKEN'};if(selector==='.shell')return shell;if(selector==='.topbar')return {getBoundingClientRect:()=>({height:126})};if(selector==='#view-setup > .panel')return setupPanel;if(selector==='input[name="mode"]:checked')return radios.find(r=>r.checked);const m=selector.match(/input\[name="mode"\]\[value="(.+)"\]/);if(m)return radios.find(r=>r.value===m[1]);throw new Error(`unsupported static selector ${selector}`);},
    querySelectorAll:(selector)=>{if(selector==='[data-view]'||selector==='.nav-item[data-view]')return nav;if(selector==='.view')return views;if(selector==='[data-unit]')return unitButtons;if(selector==='.input-unit')return [new Element(),new Element()];if(selector==='input[name="mode"]')return radios;if(selector==='button')return [...nodes.values(),...created].filter(x=>x.tagName==='BUTTON');return [];},
    addEventListener(type,fn){(documentHandlers[type]??=[]).push(fn);}
  };
  const storage={getItem:()=>JSON.stringify(preferences),setItem(){}};
  const context={document,window:{__NEXUS_TOKEN__:'STATIC_TEST_TOKEN',devicePixelRatio:1,addEventListener(){},confirm:()=>true,NEXUS_I18N:{translate:(value,lang)=>i18nContext.window.NEXUS_I18N.translate(value,lang),apply(){}}},location:{hash:''},history:{replaceState(){}},localStorage:storage,console,Intl,Date,JSON,Number,String,Array,Object,Math,Set,URL,AbortController,setTimeout:fakeSetTimeout,clearTimeout:fakeClearTimeout,setInterval:()=>1,requestAnimationFrame:fn=>fn(),fetch:async(path,opts)=>{calls.push({path,opts});return {ok:true,status:200,headers:{get:()=> 'application/json'},json:async()=>network.respond?.(path,opts)??(path==='/api/state'?fixture:{ok:true,state:fixture,path:'C:/NEXUS/knowledge-report.json'})};}};
  vm.runInNewContext(source,context,{filename:'app.js',timeout:3000});
  const navigate=async view=>{const target=nav.find(x=>x.dataset.view===view);for(const fn of target.handlers.click||[])await fn({preventDefault(){},target});};
  return {nodes,created,calls,navigate,timerCount:delay=>[...timers.values()].filter(timer=>timer.delay===delay).length,takeTimer(delay){const entry=[...timers].find(([,timer])=>timer.delay===delay);assert(entry,`no pending timer at ${delay}ms`);timers.delete(entry[0]);return entry[1].fn;},async flush(){await new Promise(setImmediate);for(const target of nav)await navigate(target.dataset.view);await navigate('overview');},async event(id,type){for(const fn of get(id).handlers[type]||[])await fn({preventDefault(){},target:get(id)});},async documentEvent(type,target){for(const fn of documentHandlers[type]||[])await fn({target});}};
}
(async()=>{
  const disconnected=environment({version:'0.1',mode:'READ_ONLY',status:'DISCONNECTED',account:null,scan:{rows:[],complete:false},news:{},chart:{}});await disconnected.flush();
  assert.equal(disconnected.nodes.get('account-balance').textContent,'—');
  assert.equal(disconnected.nodes.get('start-button').disabled,true);
  assert.equal(disconnected.nodes.get('risk-input').value,'');
  assert.equal(disconnected.nodes.get('simulation-banner').hidden,true);
  assert.match(disconnected.nodes.get('scan-status').textContent,/لا يمكن الادعاء/);
  assert.equal(disconnected.calls[0].opts.headers['X-Nexus-Token'],'STATIC_TEST_TOKEN');
  const now=Math.floor(Date.now()/1000);
  const fixture={version:'0.1',simulation:true,mode:'MANUAL_DEMO',status:'MANUAL_DEMO',last_update:now,
    account:{login:123,name:'null null',trade_mode:0,balance:10000,equity:12000,currency:'USD',server:'TEST ONLY'},terminal:{connected:true},execution:{entries_paused:true,reason:'Activation requested'},
    risk:{risk_amount:100,target_amount:200,remaining:80,used:20,realized_losses:5,floating_losses:3,reserved:10,realized_gross:160,realized_net:155,floating_net:0,commission_fee:-5,swap:0,estimated_exit_cost:5,net_target:150,exposure:2,external_exposure:0},
    scan:{discovered:2,checked:1,eligible:1,excluded:0,complete:false,cycle_started:now,rows:[{name:'TEST_A',checked:true,eligible:true,category:'forex',last_scan:now,spec:{trade_contract_size:100000},reason:'Minimum broker lot exceeds risk or margin budget'},{name:'TEST_PENDING',checked:false,eligible:false,status:'PENDING',reasons:['Ambiguous equal-endpoint session']}]},
    opportunities:[{symbol:'TEST_A',decision:'BUY',eligible:true,score:80,intent_id:'fixture_intent',proposal:{id:'fixture_intent',symbol:'TEST_A',side:'BUY',timeframe:'H1',entry:1,expires_at:now+60,reason:'TEST ONLY'}}],
    intents:[{id:'old',kind:'ENTRY',state:'FILLED',reserved:5,payload:{proposal:{symbol:'TEST_A',side:'BUY'},request:{volume:.01},reason:'TEST ONLY'},created:now,updated:now}],
    chart:{symbol:'TEST_A',timeframe:'H1',bars:[],cards:[{school:'<img src=x onerror=alert(1)>',symbol:'TEST_A',timeframe:'H1',status:'WAIT',direction:'BUY',quality:'VALIDATED_OHLC',score:40,score_formula:'rule quality'},{school:'الأنماط الانعكاسية الكلاسيكية',strategy:'classic_reversal_patterns',symbol:'TEST_A',timeframe:'H1',status:'WAIT',direction:'NEUTRAL',quality:'VALIDATED_OHLC',score:50,score_formula:'rule quality',evidence:[{kind:'reversal_pattern',value:{name:'double_top',confirmed_swings:[{kind:'HIGH',price:110,index:4,confirmed_at:now}]}}]}],committee:{decision:'WAIT',reasons:['no fresh completed and triggered entry setup']}},
    news:{
      sources:[{name:'Federal Reserve',status:'OK',description:'Official publisher feed',terms:'Pending legal review',received_at:now,fresh:true},{name:'Unknown External Desk',status:'ERROR',reason:'Connection timed out',terms_status:'Unknown terms',received_at:now,fresh:false}],
      items:[{title:'Federal Reserve raises interest rates',facts:'<script>alert(1)</script>',url:'javascript:alert(1)',source:'Unknown External Desk',provider:'Federal Reserve',assets:['USD'],timezone:'UTC',received_at:now,fresh:true,source_fresh:true,interpretation:'Potential macroeconomic exposure; no inferred direction'},{title:'OLD SOURCE TEST',facts:'TEST ONLY',source:'OLD TEST',assets:['EUR'],fresh:true,source_fresh:false}],
      calendar:{provider:'MT5 Economic Calendar',events:[{title:'National Day',currency:'USD',importance:1,time_utc:now,source_url:'https://www.bls.gov/news.release/empsit.htm',actual:1,previous:2},{title:'S&P Global Manufacturing PMI m/m',currency:'EUR',importance:'HIGH',time_utc:now},{title:'Retail Sales y/y',currency:'GBP',impact:2,time_utc:now},{title:'Unmapped Surprise Gauge',currency:'JPY',importance:0,time_utc:now}]}
    },
    events:[{event:'ORDER_FILLED',payload:{reason:'TEST ONLY'},at:now,sequence:1}],
    performance:{rows:[{strategy:'fixture',symbol:'TEST_A',gross:160,costs:-5,net:155,closed_deals:1,simulation:true}]},
    coverage:[{school:'Test coverage',coverage:'PARTIAL'}],quant_results:[]};
  // A scheduled callback may already be dequeued when an action starts its
  // manual refresh. Both callers must await one GET, and recurring updates
  // must survive its completion or failure without replaying the action.
  for(const failRefresh of [false,true]){
    let stateReads=0,releaseRefresh;
    const blockedRefresh=new Promise(resolve=>{releaseRefresh=resolve;});
    const updatedFixture=JSON.parse(JSON.stringify(fixture));updatedFixture.account.balance=10001;
    const polling=environment(fixture,{}, {controlTimers:true,respond:(path)=>{
      if(path==='/api/action')return {ok:true};
      if(path==='/api/state')return ++stateReads===2?blockedRefresh:stateReads>2?updatedFixture:fixture;
    }});
    await polling.flush();assert.equal(polling.timerCount(2500),1);
    const dequeuedScheduledRefresh=polling.takeTimer(2500);
    const actionRefresh=polling.event('scan-button','click');await new Promise(setImmediate);
    assert.equal(stateReads,2,'action must begin the manual state refresh');
    const scheduledRefresh=dequeuedScheduledRefresh();
    const anotherManualRefresh=polling.event('refresh-button','click');await new Promise(setImmediate);
    assert.equal(stateReads,2,'overlapping refresh callers must share the pending GET');
    releaseRefresh(failRefresh?{ok:false,error:'تعذر الوصول إلى الخدمة المحلية.'}:updatedFixture);
    await Promise.all([actionRefresh,scheduledRefresh,anotherManualRefresh]);
    const nextDelay=failRefresh?6000:2500;
    assert.equal(polling.timerCount(nextDelay),1,'manual refresh completion must preserve exactly one recurring timer');
    assert.equal(polling.calls.filter(call=>call.path==='/api/action').length,1,'polling must not replay the action');
    await polling.takeTimer(nextDelay)();
    assert.equal(stateReads,3,'recurring refresh must continue after the overlap');
    assert.equal(polling.timerCount(2500),1,'successful refresh must retain one normal-interval timer');
    assert.match(polling.nodes.get('account-balance').textContent,/10,001\.00/,'later server changes must reach the visible UI');
    assert.equal(polling.nodes.get('service-error').hidden,true,'successful retry clears the refresh failure');
  }
  console.log('PASS: polling liveness: overlapping action, scheduled and manual refreshes share one GET, retain one recurring timer after success or failure, recover updated state and never replay actions.');
  const rich=environment(fixture);await rich.flush();
  const performanceFixture=JSON.parse(JSON.stringify(fixture));
  performanceFixture.performance.rows.push({strategy:'NO_OUTCOMES',symbol:'EMPTY_ROW',closed_deals:0,gross:0,costs:0,net:0});
  performanceFixture.performance.rows.push({strategy:'COST_ONLY',symbol:'COST_ROW',closed_deals:0,gross:0,costs:-2,net:-2});
  const resultOnly=environment(performanceFixture);await resultOnly.flush();
  assert.doesNotMatch(resultOnly.nodes.get('performance-table').innerHTML,/EMPTY_ROW/,'empty strategy placeholders must not obscure actual performance');
  assert.match(resultOnly.nodes.get('performance-table').innerHTML,/COST_ROW/,'cost-only records must remain visible even without closed deals');
  assert.equal(performanceFixture.performance.rows.length,3,'presentation filtering must not mutate the stored snapshot');
  assert.equal(rich.nodes.get('simulation-banner').hidden,false);
  assert.match(rich.nodes.get('net-progress').textContent,/150\.00/);
  assert.match(rich.nodes.get('intents-table').innerHTML,/منفذ/);
  assert.match(rich.nodes.get('intents-table').innerHTML,/TEST_A/);
  assert.match(rich.nodes.get('pending-intents').innerHTML,/data-approve="fixture_intent"/);
  assert.equal(rich.nodes.get('pending-approval-panel').hidden,false,'pending manual approval must stay visible');
  assert.match(rich.nodes.get('research-cards').innerHTML,/&lt;img/);
  assert(!rich.nodes.get('research-cards').innerHTML.includes('<img'));
  assert.match(rich.nodes.get('research-cards').innerHTML,/الأنماط الانعكاسية الكلاسيكية/);
  assert.match(rich.nodes.get('research-cards').innerHTML,/اسم النموذج/);
  assert.match(rich.nodes.get('research-cards').innerHTML,/نموذج القمتين/);
  assert.doesNotMatch(rich.nodes.get('research-cards').innerHTML,/confirmed_swings|double_top|reversal_pattern|>HIGH</,'Arabic research cards must localize pattern schema and values');
  assert(!rich.nodes.get('news-items').innerHTML.includes('href="javascript:'));
  assert(!rich.nodes.get('news-items').innerHTML.includes('<script'),'foreign source text must never become executable markup');
  assert(!rich.nodes.get('news-items').innerHTML.includes('alert(1)'),'untranslated foreign facts must use the reviewed Arabic fallback');
  assert.match(rich.nodes.get('news-items').innerHTML,/حديث بحسب وقت النشر/);
  assert.match(rich.nodes.get('news-items').innerHTML,/المصدر قديم أو غير متاح/,'stale source must stay visible even with a fresh publication');
  assert.match(rich.nodes.get('calendar-items').innerHTML,/href="https:\/\/www\.bls\.gov\/news\.release\/empsit\.htm"/,'calendar must show bridge source_url');
  assert.match(rich.nodes.get('news-sources').innerHTML,/الاحتياطي الفيدرالي/,'known publisher names must be Arabic');
  assert.match(rich.nodes.get('news-sources').innerHTML,/تفاصيل المصدر بلغة خارجية/,'unknown source prose must fail closed in Arabic');
  assert.match(rich.nodes.get('news-items').innerHTML,/بيان رسمي جديد من مصدر أخبار رسمي/,'unknown foreign headlines must use an honest Arabic source description');
  assert.match(rich.nodes.get('news-items').innerHTML,/الدولار الأمريكي/,'currency codes must be readable Arabic in the news view');
  assert.match(rich.nodes.get('news-items').innerHTML,/التوقيت العالمي/,'source timezone must be Arabic');
  assert.match(rich.nodes.get('calendar-items').innerHTML,/عطلة اليوم الوطني/);
  assert.match(rich.nodes.get('calendar-items').innerHTML,/مؤشر مديري المشتريات الصناعي — تغير شهري/);
  assert.match(rich.nodes.get('calendar-items').innerHTML,/مبيعات التجزئة — تغير سنوي/);
  assert.match(rich.nodes.get('calendar-items').innerHTML,/حدث اقتصادي رسمي مرتبط بعملة الين الياباني/,'unknown calendar titles must stay informative without inventing a translation');
  assert.match(rich.nodes.get('calendar-items').innerHTML,/أهمية مرتفعة/);
  const arabicNewsVisible=['news-coverage','news-sources','news-items','calendar-items'].map(id=>rich.nodes.get(id).innerHTML||rich.nodes.get(id).textContent).join(' ').replace(/<[^>]*>/g,' ').replace(/&(?:[a-z]+|#\d+);/gi,' ').replace(/\b(?:NEXUS|MT5|RSS|XML)\b/g,' ');
  assert.doesNotMatch(arabicNewsVisible,/[A-Za-z]{2,}(?:[\s-]+[A-Za-z]{2,})?/,'Arabic news view must not expose untranslated prose');
  assert.match(rich.nodes.get('events-list').innerHTML,/تنفيذ مؤكد لدى الوسيط/);
  assert.match(rich.nodes.get('events-list').innerHTML,/TEST ONLY/);
  assert.match(rich.nodes.get('events-list').innerHTML,/السبب/,'Arabic audit view must localize payload field names');
  assert(!rich.nodes.get('events-list').innerHTML.includes('"reason"'),'Arabic audit view must not expose raw English schema keys');
  assert.match(rich.nodes.get('symbols-table').innerHTML,/أقل لوت يسمح به الوسيط يتجاوز المخاطرة أو الهامش المتاح/);
  assert.equal(rich.nodes.get('account-login').textContent,'# 123','placeholder account names must not leak into the UI');
  assert.match(rich.nodes.get('start-hint').textContent,/جارٍ التحقق من طلب التفعيل الجديد/);
  rich.nodes.get('symbol-filter').value='unchecked';await rich.event('symbol-filter','change');
  assert.match(rich.nodes.get('symbols-table').innerHTML,/TEST_PENDING/);
  assert.match(rich.nodes.get('symbols-table').innerHTML,/مدة الجلسة غامضة/);
  assert(!rich.nodes.get('symbols-table').innerHTML.includes('<span class="symbol-name">TEST_A'));
  const percent=environment(fixture,{unit:'percent'});await percent.flush();percent.nodes.get('risk-input').value='1';await percent.event('risk-input','input');assert.match(percent.nodes.get('risk-conversion').textContent,/120\.00/,'percentage must use equity, not balance');
  const uncertainFixture=JSON.parse(JSON.stringify(fixture));Object.assign(uncertainFixture.risk,{unattributed_costs:17,cost_uncertainty:['deal:77'],net_target:133,target_confirmed:false});
  const uncertain=environment(uncertainFixture);await uncertain.flush();
  assert.match(uncertain.nodes.get('unattributed-costs').textContent,/17\.00 USD/);
  assert.equal(uncertain.nodes.get('cost-attribution-note').hidden,false);
  assert.match(uncertain.nodes.get('cost-attribution-note').textContent,/غموض الإسناد يمنع الدخول/);
  assert.match(uncertain.nodes.get('cost-attribution-note').textContent,/الدخول الجديد ممنوع حتى المطابقة/);
  assert.match(uncertain.nodes.get('net-progress').textContent,/133\.00/,'use engine net_target; do not subtract unknown costs again');
  assert.match(uncertain.nodes.get('costs-pnl').textContent,/5\.00/,'keep proven attributed costs separate');
  assert.match(uncertain.nodes.get('realized-pnl').textContent,/160\.00/,'retain existing gross realized field');
  assert.match(uncertain.nodes.get('net-formula').textContent,/التكاليف المنسوبة داخلة في المحقق الصافي/);
  const zeroUnknownFixture=JSON.parse(JSON.stringify(fixture));Object.assign(zeroUnknownFixture.risk,{unattributed_costs:0,cost_uncertainty:['deal:88']});const zeroUnknown=environment(zeroUnknownFixture);await zeroUnknown.flush();assert.equal(zeroUnknown.nodes.get('cost-attribution-note').hidden,false,'uncertain attribution must warn even with zero recorded amount');
  const resolvedFixture=JSON.parse(JSON.stringify(fixture));Object.assign(resolvedFixture.risk,{unattributed_costs:0,cost_uncertainty:[]});const resolved=environment(resolvedFixture);await resolved.flush();assert.equal(resolved.nodes.get('cost-attribution-note').hidden,true);
  const performanceCostFixture=JSON.parse(JSON.stringify(fixture));Object.assign(performanceCostFixture.performance,{unattributed_costs:9,cost_uncertainty:['deal:99']});const performanceCost=environment(performanceCostFixture);await performanceCost.flush();assert.match(performanceCost.nodes.get('unattributed-costs').textContent,/9\.00/,'performance summary provides cost uncertainty when risk is not configured');
  const englishFixture=JSON.parse(JSON.stringify(fixture));
  const modelManifest=JSON.parse(fs.readFileSync(path.join(uiRoot,'../docs/agent-rules/manifest.json'),'utf8'));
  englishFixture.coverage=modelManifest.agents;
  const extensionModels=modelManifest.agents.filter(row=>row.contract.definition.rules_source==='extended_models.py');
  assert.equal(extensionModels.length,16);
  for(const meta of extensionModels)englishFixture.chart.cards.push({school:meta.school,strategy:meta.id,version:meta.version,status:'WAIT',direction:'NEUTRAL',quality:'VALIDATED_OHLC',symbol:'TEST_A',timeframe:'M1'});
  englishFixture.opportunities[0].decision_matrix={route:'MULTI_SCHOOL_OHLC',evidence_families:{price_structure:50,price_transform:51},
    directional_evidence:{support:101,opposition:100,net:1},evidence_coverage:{registered_models:58,fresh_eligible_cards:55,excluded_cards:3},
    school_evidence:extensionModels.map(row=>({strategy_id:row.id,school:row.school,status:'WAIT',direction:'NEUTRAL',timeframe:'M1',role:'NO_DIRECTIONAL_VOTE'}))};
  englishFixture.cards=[{strategy_id:'order_flow',status:'DATA_MISSING'},{strategy_id:'order_flow',status:'WAIT'}];
  englishFixture.chart.cards[0].score_formula='100 × عدد الشروط المتحققة ÷ إجمالي الشروط؛ صفر عند غياب الشروط. هذه درجة تحقق القواعد وليست احتمال نجاح';
  englishFixture.chart.cards[0].assumptions=['300 شمعة داخل اليوم لا تكفي لإثبات الموسمية','RSI بمتوسط ربح وخسارة بسيط متحرك وليس تنعيم وايلدر'];
  englishFixture.chart.committee.formula='أعلى درجة فقط لكل عائلة أدلة مترابطة؛ يلزم عائلتان على الأقل، ومعايير كمية ثابتة';
  englishFixture.chart.committee.limitations=['تجميع الأدلة يقلل العد المكرر للمؤشرات المترابطة ولا يثبت استقلالها الإحصائي'];
  englishFixture.chart.committee.risk_authority='محرك المخاطر المستقل يملك حق الرفض النهائي؛ اللجنة لا ترسل الأوامر';
  englishFixture.scan.rows[0].spec.description='عقد صناعي للاختبارات';
  englishFixture.scan.rows[0].session={reason:'جلسة صناعية للاختبار'};
  const english=environment(englishFixture,{language:'en'});await english.flush();
  assert.match(english.nodes.get('research-cards').innerHTML,/Stochastic SMA rebound/);
  assert.match(english.nodes.get('opportunities').innerHTML,/Evidence-family weighting without a fixed vote percentage/);
  assert.match(english.nodes.get('opportunities').innerHTML,/Net evidence/);
  const newMatrixMarkup=english.nodes.get('opportunities').innerHTML;
  assert.doesNotMatch(newMatrixMarkup.slice(newMatrixMarkup.indexOf('<div class="decision-matrix">')),/[\u0600-\u06ff]/,'new matrix names and decision explanation must render in English');
  assert.match(english.nodes.get('coverage-list').innerHTML,/Activity flow: bar-tick approximation/);
  assert.match(english.nodes.get('coverage-list').innerHTML,/not the complete original school/);
  assert.match(english.nodes.get('coverage-list').innerHTML,/Current analysis state/);
  assert.match(english.nodes.get('coverage-list').innerHTML,/1/);
  const renderedEnglish=[...english.nodes.values(),...english.created].flatMap(node=>[node.textContent,node.innerHTML]).filter(Boolean).join('\n');
  assert.match(english.nodes.get('news-items').innerHTML,/Federal Reserve raises interest rates/,'English mode must retain the original publisher headline');
  assert.match(english.nodes.get('research-cards').innerHTML,/Classical Reversal Patterns/,'English mode must translate new school names');
  assert.match(english.nodes.get('calendar-items').innerHTML,/National Day/,'English mode must retain original calendar titles');
  assert.match(english.nodes.get('calendar-items').innerHTML,/Unmapped Surprise Gauge/,'raw unknown titles are available in English mode');
  // The small DOM substitute stores innerHTML as an opaque string, so it
  // cannot execute the real MutationObserver/tree-walker pass. Verify every
  // rendered Arabic text node through the same translator that pass uses.
  const renderedTextNodes=[...renderedEnglish.matchAll(/>([^<>]+)</g)].map(match=>match[1].trim()).filter(Boolean);
  for(const value of renderedTextNodes.filter(value=>/[\u0600-\u06ff]/.test(value))){
    assert(!/[\u0600-\u06ff]/.test(translateEnglish(value)),`English rendered text is not translatable: ${value}`);
  }
  const referenceFixture=JSON.parse(JSON.stringify(fixture));
  referenceFixture.knowledge={catalog_version:'1.0.0',schools:[
    {id:'technical_test',category:'technical',order:1,name_ar:'مرجع فني تجريبي',name_en:'Technical reference fixture',rules_ar:['قاعدة عربية معلنة'],rules_en:['Declared English rule'],exceptions_ar:['استثناء عربي'],exceptions_en:['English exception'],requirements_ar:['شموع مكتملة'],requirements_en:['Completed bars'],scope_ar:'حدود المرجع العربي',scope_en:'English reference scope',strategy_ids:['order_flow'],references:[{title:'Source <img src=x>',url:'https://example.org/reference',scope_ar:'نطاق مصدر عربي',scope_en:'English source scope'},{title:'Unsafe source',url:'javascript:alert(1)'}]},
    {id:'fundamental_test',category:'fundamental',order:1,name_ar:'مرجع أساسي تجريبي',name_en:'Fundamental reference fixture',rules_ar:['القاعدة المالية'],rules_en:['Financial rule'],exceptions_ar:['الحد المالي'],exceptions_en:['Financial limit'],requirements_ar:['قوائم مالية'],requirements_en:['Financial statements'],scope_ar:'تقييم يحتاج بيانات مالية',scope_en:'Valuation needs financial data',strategy_ids:[],references:[]},
    {id:'approach_test',category:'approach',order:1,name_ar:'<script>تنفيذ</script>',name_en:'<script>execute</script>',rules_ar:['قاعدة تقييم'],rules_en:['Valuation rule'],exceptions_ar:[],exceptions_en:[],requirements_ar:[],requirements_en:[],scope_ar:'مرجع منهجي',scope_en:'Approach reference',strategy_ids:[],alias_of:'fundamental_test',references:[]}
  ]};
  referenceFixture.learning={mode:'OBSERVATIONAL',stored_versions:36,observations:150,closed_records:3,eligible_records:2,excluded_records:1,minimum_samples:40,holdout_minimum:12,models:[{strategy_id:'order_flow',revision:'rule-hash',symbol:'TEST_A',timeframe:'H1',regime:'range',samples:2,mean_r:.3,ewma_r:.4,smoothed_positive_rate:.75,holdout_samples:1,holdout_mean_r:-.2,status:'INSUFFICIENT',live_weight_changed:false}],auto_changes:false};
  const referenceAr=environment(referenceFixture);await referenceAr.flush();
  assert.match(referenceAr.nodes.get('knowledge-schools').innerHTML,/قاعدة عربية معلنة/);
  assert.doesNotMatch(referenceAr.nodes.get('knowledge-schools').innerHTML,/Declared English rule|English source scope|Technical reference fixture/,'Arabic reference must select original authored Arabic fields');
  assert.match(referenceAr.nodes.get('knowledge-schools').innerHTML,/القوائم المالية والتدفقات النقدية/,'missing fundamental data must remain explicit');
  assert.match(referenceAr.nodes.get('knowledge-schools').innerHTML,/&lt;script&gt;/,'reference text must escape HTML');
  assert.doesNotMatch(referenceAr.nodes.get('knowledge-schools').innerHTML,/<script>|href="javascript:/,'reference URLs and text must not inject scripts');
  assert.match(referenceAr.nodes.get('learning-models').innerHTML,/عينة غير كافية/);
  assert.match(referenceAr.nodes.get('learning-policy').textContent,/لا يغير قواعد التداول أو الأوزان الحية أو حدود المخاطرة تلقائيًا/,'observational learning must not be presented as live automatic changes');
  await referenceAr.documentEvent('toggle',{dataset:{knowledgeDetails:'technical_test'},open:true});await referenceAr.event('knowledge-search','input');
  assert.match(referenceAr.nodes.get('knowledge-schools').innerHTML,/data-knowledge-details="technical_test" open/,'opened rule details must remain open after a reference refresh');
  await referenceAr.documentEvent('toggle',{dataset:{knowledgeDetails:'technical_test'},open:false});await referenceAr.event('knowledge-search','input');
  assert.doesNotMatch(referenceAr.nodes.get('knowledge-schools').innerHTML,/data-knowledge-details="technical_test" open/,'closing rule details must remain closed on the next update');
  referenceAr.nodes.get('knowledge-filter').value='fundamental';await referenceAr.event('knowledge-filter','change');
  assert.match(referenceAr.nodes.get('knowledge-schools').innerHTML,/مرجع أساسي تجريبي/);
  assert.doesNotMatch(referenceAr.nodes.get('knowledge-schools').innerHTML,/مرجع فني تجريبي/);
  referenceAr.nodes.get('knowledge-search').value='ليس في المكتبة';await referenceAr.event('knowledge-search','input');assert.match(referenceAr.nodes.get('knowledge-schools').innerHTML,/لا توجد مراجع بهذه التصفية/);
  await referenceAr.event('knowledge-export-button','click');
  assert(referenceAr.calls.some(call=>call.opts?.body&&JSON.parse(call.opts.body).action==='knowledge_export'),'reference export must call authorized local action');
  assert.match(referenceAr.nodes.get('knowledge-export-result').textContent,/C:\/NEXUS\/knowledge-report.json/);
  assert.equal(referenceAr.nodes.get('knowledge-export-panel').hidden,false,'successful export must reveal its file path');
  const requestId='a'.repeat(32);let pendingReads=0;
  const queuedExport=environment(referenceFixture,{language:'en'},{respond:(path)=>path==='/api/action'?{ok:true,queued:true,request_id:requestId}:path.startsWith('/api/action-result')?++pendingReads===1?{ok:true,status:'PENDING',result:null}:{ok:true,status:'COMPLETE',result:{ok:true,path:'C:/NEXUS/queued-complete.zip'}}:undefined});
  await queuedExport.flush();await queuedExport.event('knowledge-export-button','click');
  assert.match(queuedExport.nodes.get('knowledge-export-result').textContent,/queued-complete.zip/);
  assert.equal(queuedExport.calls.filter(x=>x.path==='/api/action').length,1,'queued action must never be submitted again');
  assert.equal(queuedExport.calls.filter(x=>x.path.startsWith('/api/action-result')).length,2);
  assert(queuedExport.calls.filter(x=>x.path.startsWith('/api/action-result')).every(x=>x.opts.headers['X-Nexus-Token']==='STATIC_TEST_TOKEN'),'completion lookup requires the same session token');
  const queuedFailure=environment(referenceFixture,{language:'en'},{respond:(path)=>path==='/api/action'?{ok:true,queued:true,request_id:requestId}:path.startsWith('/api/action-result')?{ok:true,status:'COMPLETE',result:{ok:false,error:'الخدمة توقفت قبل تنفيذ الإجراء؛ لم يُنفذ'}}:undefined});
  await queuedFailure.flush();await queuedFailure.event('knowledge-export-button','click');
  assert.equal(queuedFailure.nodes.get('knowledge-export-result').textContent,'','failed queued export must not claim a file was saved');
  assert(queuedFailure.nodes.get('toast-region').children.some(x=>x.className.includes('error')&&/was not executed/.test(x.textContent)),'final queued failure must be rendered in English');
  assert.equal(queuedFailure.calls.filter(x=>x.path==='/api/action').length,1);
  for(const language of ['ar','en']){
    const policyError=environment(referenceFixture,{language},{respond:path=>path==='/api/action'?{ok:false,error:'Four-school historical qualification is unavailable; choose forward_demo'}:undefined});
    await policyError.flush();await policyError.event('scan-button','click');
    const errorToast=policyError.nodes.get('toast-region').children.find(node=>node.className.includes('error'));
    assert(errorToast,'historical-policy rejection must be visible');
    if(language==='ar'){
      assert.match(errorToast.textContent,/التأهيل التاريخي لبروتوكول المدارس الأربع غير متاح/);
      assert.doesNotMatch(errorToast.textContent,/[A-Za-z]/,'Arabic rejection must not expose the backend enum or English message');
    }else{
      assert.equal(errorToast.textContent,'Historical qualification for the four-school protocol is unavailable; choose forward Demo testing.');
      assert.doesNotMatch(errorToast.textContent,/[\u0600-\u06ff]|forward_demo/,'English rejection must use complete reviewed copy');
    }
  }
  const referenceEn=environment(referenceFixture,{language:'en'});await referenceEn.flush();
  assert.match(referenceEn.nodes.get('knowledge-schools').innerHTML,/Declared English rule/);
  assert.match(referenceEn.nodes.get('knowledge-schools').innerHTML,/English exception/);
  assert.match(referenceEn.nodes.get('knowledge-schools').innerHTML,/English reference scope/);
  assert.doesNotMatch(referenceEn.nodes.get('knowledge-schools').innerHTML,/[\u0600-\u06ff]/,'English reference is independently authored, including headings and missing-data text');
  assert.match(referenceEn.nodes.get('learning-policy').textContent,/40 eligible outcomes and 12 later holdout outcomes/);
  assert.match(referenceEn.nodes.get('learning-models').innerHTML,/Insufficient sample/);
  assert.doesNotMatch(referenceEn.nodes.get('learning-models').innerHTML,/[\u0600-\u06ff]/,'learning table must not mix Arabic into English mode');
  const chartLearningFixture=JSON.parse(JSON.stringify(referenceFixture));
  chartLearningFixture.learning.chart_learning={mode:'SHADOW_ONLY',eligible_records:60,missing_features:2,invalid_features:1,minimum_samples:60,models:[{strategy_id:'ema_cross',revision:'entry-rule-revision',symbol:'TEST',timeframe:'M5',samples:60,train_samples:42,holdout_samples:18,purged_overlapping_labels:0,status:'EVALUATED_SHADOW',holdout_model:{brier:.12},holdout_baseline:{brier:.25}}]};
  const chartEn=environment(chartLearningFixture,{language:'en'}),chartAr=environment(chartLearningFixture);await chartEn.flush();await chartAr.flush();
  assert.match(chartEn.nodes.get('chart-learning-policy').textContent,/frozen at the entry decision/);
  assert.match(chartEn.nodes.get('chart-learning-policy').textContent,/does not automatically change trading rules/);
  assert.match(chartEn.nodes.get('chart-learning-models').innerHTML,/Independent research evaluation completed/);
  assert.match(chartEn.nodes.get('chart-learning-models').innerHTML,/>0\.12<\/td>/);
  for(const id of ['chart-learning-mode','chart-learning-summary','chart-learning-policy','chart-learning-models'])assert.doesNotMatch(chartEn.nodes.get(id).innerHTML+chartEn.nodes.get(id).textContent,/[\u0600-\u06ff]/,`English chart learner must not mix Arabic: ${id}`);
  assert.match(chartAr.nodes.get('chart-learning-policy').textContent,/تُحفظ الخصائص وقت قرار الدخول/);
  assert.match(chartAr.nodes.get('chart-learning-models').innerHTML,/تم التقييم البحثي المستقل/);
  const invalidCalls=referenceEn.calls.length;referenceEn.nodes.get('valuation-input').value='bad json';await referenceEn.event('valuation-analyze-button','click');assert.equal(referenceEn.calls.length,invalidCalls,'invalid valuation JSON must not send any action');
  await referenceEn.event('valuation-example-button','click');
  const example=JSON.parse(referenceEn.nodes.get('valuation-input').value);assert.equal(example.model,'dcf');assert.match(example.source,/illustrative.*invented/,'example input provenance must be explicitly synthetic');
  await referenceEn.event('valuation-analyze-button','click');
  assert(referenceEn.calls.some(call=>call.opts?.body&&JSON.parse(call.opts.body).action==='fundamental_analyze'&&JSON.parse(call.opts.body).data.asset==='ILLUSTRATIVE_EXAMPLE'),'valuation must send parsed data to the local financial calculator action');
  const valuedFixture=JSON.parse(JSON.stringify(referenceFixture));valuedFixture.valuation={model:'dcf',currency:'USD',present_value:272.54,enterprise_value:1422.08,equity_value:1272.08,value_per_share:12.7208,terminal_pv:1149.54,terminal_fraction:.8083,as_of:1700000000,published_at:1699000000,input_fingerprint:'hash'};
  const valuedEnglish=environment(valuedFixture,{language:'en'});await valuedEnglish.flush();assert.match(valuedEnglish.nodes.get('valuation-results').innerHTML,/Discounted cash flow/);assert.match(valuedEnglish.nodes.get('valuation-results').innerHTML,/grant no order-sending authority/);assert.match(valuedEnglish.nodes.get('valuation-results').innerHTML,/12\.7208 USD/);assert.doesNotMatch(valuedEnglish.nodes.get('valuation-results').innerHTML,/[\u0600-\u06ff]/);
  const valuedArabic=environment(valuedFixture);await valuedArabic.flush();assert.match(valuedArabic.nodes.get('valuation-results').innerHTML,/التدفقات النقدية المخصومة/);assert.match(valuedArabic.nodes.get('valuation-results').innerHTML,/لا يمنح صلاحية إرسال أوامر/);
  const catalogPath=path.join(uiRoot,'../docs/school-catalog/catalog.json');
  if(fs.existsSync(catalogPath)){
    const completeFixture=JSON.parse(JSON.stringify(referenceFixture));completeFixture.knowledge=JSON.parse(fs.readFileSync(catalogPath,'utf8'));
    assert.equal(completeFixture.knowledge.schools.length,58,'published catalog must contain all 58 requested schools and approaches');
    const actualAr=environment(completeFixture),actualEn=environment(completeFixture,{language:'en'});await actualAr.flush();await actualEn.flush();
    const escaped=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    assert.equal((actualAr.nodes.get('knowledge-schools').innerHTML.match(/class="knowledge-card"/g)||[]).length,58);
    assert.equal((actualEn.nodes.get('knowledge-schools').innerHTML.match(/class="knowledge-card"/g)||[]).length,58);
    for(const school of completeFixture.knowledge.schools){
      assert(actualAr.nodes.get('knowledge-schools').innerHTML.includes(escaped(school.name_ar)),`Arabic school missing: ${school.id}`);
      assert(actualEn.nodes.get('knowledge-schools').innerHTML.includes(escaped(school.name_en)),`English school missing: ${school.id}`);
      for(const rule of school.rules_en)assert(actualEn.nodes.get('knowledge-schools').innerHTML.includes(escaped(rule)),`English rule missing: ${school.id}`);
      for(const rule of school.rules_ar)assert(actualAr.nodes.get('knowledge-schools').innerHTML.includes(escaped(rule)),`Arabic rule missing: ${school.id}`);
      for(const item of school.rule_protocol.summary_en)assert(actualEn.nodes.get('knowledge-schools').innerHTML.includes(escaped(item)),`English protocol missing: ${school.id}`);
      for(const item of school.rule_protocol.summary_ar)assert(actualAr.nodes.get('knowledge-schools').innerHTML.includes(escaped(item)),`Arabic protocol missing: ${school.id}`);
    }
    assert.doesNotMatch(actualEn.nodes.get('knowledge-schools').innerHTML,/[\u0600-\u06ff]/,'all 58 English school references must be independently complete English');
    for(const [category,count] of [['technical',30],['fundamental',20],['approach',8]]){
      actualAr.nodes.get('knowledge-filter').value=category;await actualAr.event('knowledge-filter','change');
      assert.equal((actualAr.nodes.get('knowledge-schools').innerHTML.match(/class="knowledge-card"/g)||[]).length,count,`category filter ${category}`);
    }
    console.log('PASS: actual published 58-school catalog renders every Arabic and English name and rule; filters preserve 30 technical, 20 fundamental and 8 approaches.');
  }else console.log('PENDING: actual 58-school catalog file has not been generated yet; fixture UI checks only.');
  const executionFixture=JSON.parse(JSON.stringify(fixture));
  executionFixture.settings={decision_protocol:'four_school_v1',validation_policy:'forward_demo',scalping:{normal:{enabled:false,risk_percent:.5,target_value:20,min_reward_risk:3},fast:{enabled:false,risk_percent:.25,target_value:10,min_reward_risk:2}}};
  executionFixture.scalping={normal:{settings:executionFixture.settings.scalping.normal,progress:{progress_net:5},latched:true},fast:{settings:executionFixture.settings.scalping.fast,progress:{progress_net:0}}};
  executionFixture.opportunities[0].decision_matrix={passed:true,ict:{status:'CONFIRMED',direction:'LONG'},volume_profile:{status:'DATA_MISSING'},time:{status:'CONFIRMED',direction:'LONG'},momentum:{status:'EVALUATED_NEUTRAL'},elliott:{status:'CONTEXT_CONFIRMED'},structural_rr:{gross_rr:3}};
  executionFixture.opportunities[0].protocol_reasons=[{code:'fixture',ar:'دليل مكتمل من شموع المنصة',en:'Evidence from completed broker bars'}];
  const executionEn=environment(executionFixture,{language:'en'}),executionAr=environment(executionFixture);await executionEn.flush();await executionAr.flush();
  assert.match(executionEn.nodes.get('scalp-progress').innerHTML,/scalp target/i);
  assert.doesNotMatch(executionEn.nodes.get('scalp-progress').innerHTML,/[\u0600-\u06ff]/);
  assert.match(executionEn.nodes.get('opportunities').innerHTML,/Evidence from completed broker bars/);
  assert.doesNotMatch(executionEn.nodes.get('opportunities').innerHTML.split('<div class="decision-matrix">')[1],/[\u0600-\u06ff]/,'new matrix authors English independently of DOM translation');
  assert.match(executionAr.nodes.get('opportunities').innerHTML,/دليل مكتمل من شموع المنصة/);
  assert.doesNotMatch(executionAr.nodes.get('opportunities').innerHTML,/Evidence from completed broker bars/);
  assert.equal(executionEn.nodes.get('scalp-normal-risk').value,'0.5');
  for(const [id,value] of [['risk-input','50'],['target-input','100'],['scalp-mode-input','fast'],['scalp-fast-risk','.25'],['scalp-fast-target','10'],['scalp-fast-rr','1.5']])executionEn.nodes.get(id).value=value;
  await executionEn.event('scalp-fast-risk','input');await executionEn.event('start-form','submit');
  assert(!executionEn.calls.some(x=>x.path==='/api/action'),'ratio below two must never activate');
  executionEn.nodes.get('scalp-fast-rr').value='3';executionEn.nodes.get('scalp-fast-target').value='';await executionEn.event('start-form','submit');
  assert(!executionEn.calls.some(x=>x.path==='/api/action'),'enabled scalp needs an explicit target');
  executionEn.nodes.get('scalp-fast-target').value='15';await executionEn.event('start-form','submit');
  const start=executionEn.calls.filter(x=>x.path==='/api/action').map(x=>JSON.parse(x.opts.body)).find(x=>x.action==='start');
  assert.equal(start.decision_protocol,'four_school_v1');assert.equal(start.validation_policy,'forward_demo');
  assert.equal(start.scalping.fast.enabled,true);assert.equal(start.scalping.normal.enabled,false);
  assert.equal(start.scalping.fast.min_reward_risk,3);assert.equal(start.scalping.fast.risk_percent,.25);assert.equal(start.scalping.fast.target_value,15);
  assert.equal(start.commission_per_lot,0);assert.equal(start.slippage_points,10,'activation retains the authorized slippage allowance without asking for it again');
  assert.equal(executionEn.nodes.get('scalp-fast-target').value,'15','state refresh must preserve a dirty user form');
  const fastFixture=JSON.parse(JSON.stringify(executionFixture));
  fastFixture.mode='AUTO_DEMO';fastFixture.execution={entries_paused:false};
  Object.assign(fastFixture.settings,{commission_per_lot:3.5,slippage_points:17});
  Object.assign(fastFixture.settings.scalping.fast,{enabled:true,risk_percent:1,profit_percent:2,target_value:100,min_reward_risk:2});
  fastFixture.scalping.fast={settings:fastFixture.settings.scalping.fast,progress:{progress_net:12.5}};
  fastFixture.fast_scheduler={enabled:true,timeframe:'M1',symbols_total:12,checked_in_sweep:3,last_sweep_seconds:28.5,observed_revisit_seconds:31.25};
  const pendingActions=[];
  const fastEn=environment(fastFixture,{language:'en'},{respond:path=>path==='/api/action'?new Promise(resolve=>pendingActions.push(resolve)):undefined}),fastAr=environment(fastFixture);
  await fastEn.flush();await fastAr.flush();
  assert.equal(fastEn.nodes.get('scalp-mode-input').value,'fast','backend fast activation must restore the selected mode');
  assert.equal(fastEn.nodes.get('scalp-fast-risk').value,'1');assert.equal(fastEn.nodes.get('scalp-fast-target').value,'100');
  assert.equal(fastEn.nodes.get('scalp-fast-profit').value,'2');
  assert.match(fastEn.nodes.get('scalp-active-status').textContent,/Fast scalp.*Active/);
  assert.match(fastAr.nodes.get('scalp-active-status').textContent,/سكالب سريع.*نشط/);
  const stopToggle=environment(fastFixture,{language:'en'});await stopToggle.flush();
  stopToggle.nodes.get('risk-input').value='';stopToggle.nodes.get('target-input').value='';
  assert.match(stopToggle.nodes.get('start-button').innerHTML,/Stop New Entries/);
  await stopToggle.event('start-button','click');
  const toggleRequests=stopToggle.calls.filter(call=>call.path==='/api/action').map(call=>JSON.parse(call.opts.body));
  assert.equal(toggleRequests.length,1);assert.equal(toggleRequests[0].action,'stop','active toggle stops despite blank or invalid authorization fields');
  assert.equal(toggleRequests.some(x=>['start','flatten','cancel'].includes(x.action)),false,'stopping entries must not activate or liquidate');
  assert.equal(fastEn.nodes.get('fast-scheduler-status').hidden,false);
  assert.match(fastEn.nodes.get('fast-scheduler-status').innerHTML,/3 \/ 12/);
  assert.match(fastEn.nodes.get('fast-scheduler-status').innerHTML,/28\.50 seconds/);
  assert.match(fastEn.nodes.get('fast-scheduler-status').innerHTML,/31\.25 seconds/);
  assert.doesNotMatch(fastEn.nodes.get('fast-scheduler-status').innerHTML,/[\u0600-\u06ff]/,'fast monitoring must be independently complete English');
  assert.match(fastAr.nodes.get('fast-scheduler-status').innerHTML,/زمن العودة المرصود لنفس الرمز/);
  assert.doesNotMatch(fastAr.nodes.get('fast-scheduler-status').innerHTML,/المدة مرصودة|لا تمثل سرعة مضمونة/,'remove the explanatory sentence while retaining measured timings');
  assert.doesNotMatch(fastEn.nodes.get('fast-scheduler-status').innerHTML,/These observed timings vary/);
  const cashFixture=JSON.parse(JSON.stringify(fastFixture));cashFixture.settings.fast_profit_protection=true;
  const cashEn=environment(cashFixture,{language:'en'});await cashEn.flush();
  assert.match(cashEn.nodes.get('execution-policy-note').textContent,/completed M15 and H1 trend confirmation/);
  assert.match(cashEn.nodes.get('execution-policy-note').textContent,/Take profit at one net dollar without waiting for two/);
  assert.doesNotMatch(cashEn.nodes.get('execution-policy-note').textContent,/[\u0600-\u06ff]/);
  const unknownCadence=JSON.parse(JSON.stringify(fastFixture));unknownCadence.mode='READ_ONLY';unknownCadence.execution.entries_paused=true;
  unknownCadence.fast_scheduler.last_sweep_seconds=null;unknownCadence.fast_scheduler.observed_revisit_seconds=null;
  const waitingFast=environment(unknownCadence,{language:'en'});await waitingFast.flush();
  assert.match(waitingFast.nodes.get('scalp-active-status').textContent,/Configured; waiting for execution to resume/,'configured scalp must not claim active execution while paused');
  assert.match(waitingFast.nodes.get('fast-scheduler-status').innerHTML,/No completed sweep yet/);
  assert.match(waitingFast.nodes.get('fast-scheduler-status').innerHTML,/Not measured yet/,'unknown observed cadence must not invent a speed');
  const inactiveStart=JSON.parse(JSON.stringify(fastFixture));inactiveStart.mode='READ_ONLY';inactiveStart.execution.entries_paused=true;
  const startEn=environment(inactiveStart,{language:'en'},{respond:path=>path==='/api/action'?new Promise(resolve=>pendingActions.push(resolve)):undefined});await startEn.flush();
  startEn.nodes.get('risk-input').value='50';startEn.nodes.get('target-input').value='100';
  const startOnce=startEn.event('start-form','submit');await new Promise(setImmediate);
  await startEn.event('start-form','submit');
  assert.equal(pendingActions.length,1,'overlapping start clicks submit one action');
  pendingActions[0]({ok:true,state:fastFixture});await startOnce;
  const canonicalStart=startEn.calls.filter(call=>call.path==='/api/action').map(call=>JSON.parse(call.opts.body)).find(payload=>payload.action==='start');
  assert.equal(canonicalStart.commission_per_lot,3.5);assert.equal(canonicalStart.slippage_points,17,'activation must retain canonical nondefault costs');
  assert.equal(canonicalStart.scalping.fast.enabled,true);assert.equal(canonicalStart.scalping.fast.risk_percent,1);assert.equal(canonicalStart.scalping.fast.target_value,100);assert.equal(canonicalStart.scalping.fast.min_reward_risk,2);
  assert.equal(canonicalStart.scalping.fast.profit_percent,2);
  const restartedMulti=JSON.parse(JSON.stringify(fastFixture));
  restartedMulti.setup={...restartedMulti.settings,decision_protocol:'multi_school_v1'};restartedMulti.settings={};
  restartedMulti.mode='READ_ONLY';restartedMulti.execution.entries_paused=true;
  const resumedMulti=environment(restartedMulti,{language:'en'});await resumedMulti.flush();
  resumedMulti.nodes.get('risk-input').value='100';resumedMulti.nodes.get('target-input').value='100';
  await resumedMulti.event('start-form','submit');
  const resumedPayload=resumedMulti.calls.filter(call=>call.path==='/api/action').map(call=>JSON.parse(call.opts.body)).find(payload=>payload.action==='start');
  assert.equal(resumedPayload.decision_protocol,'multi_school_v1','restart must retain the stored multi-school route');
  assert.equal(resumedPayload.scalp_only,true);assert.equal(resumedPayload.scalping.fast.profit_percent,2);
  fastEn.nodes.get('chart-symbol').value='TEST_A';
  const backtestOnce=fastEn.event('backtest-button','click');await new Promise(setImmediate);
  await fastEn.event('backtest-button','click');
  assert.equal(pendingActions.length,2,'overlapping backtest clicks submit one additional action');
  pendingActions[1]({ok:true,state:fastFixture});await backtestOnce;
  const backtests=fastEn.calls.filter(call=>call.path==='/api/action').map(call=>JSON.parse(call.opts.body)).filter(payload=>payload.action==='backtest');
  assert.equal(backtests.length,1);assert.equal(backtests[0].commission_per_lot,3.5);assert.equal(backtests[0].slippage_points,17,'backtest uses canonical costs without requiring removed inputs');
  const fallbackBacktest=environment(executionFixture);await fallbackBacktest.flush();fallbackBacktest.nodes.get('chart-symbol').value='TEST_A';
  await fallbackBacktest.event('backtest-button','click');
  const fallbackCostPayload=JSON.parse(fallbackBacktest.calls.find(call=>call.path==='/api/action').opts.body);
  assert.equal(fallbackCostPayload.commission_per_lot,0);assert.equal(fallbackCostPayload.slippage_points,10,'backtest retains authorized fallback costs when state has none');
  console.log('PASS: removed commission/slippage controls, retained canonical or authorized 0/10 costs for start/backtest, single submissions, visible actual fast activation and bilingual measured sweep/cadence without invented speed.');
  console.log('PASS: confluence and scalp controls: authored bilingual matrices, target progress, preserved edits, single variant, required amounts and minimum ratio, exact activation payload.');
  console.log('PASS: school reference and observational learning: authored bilingual fields, filters, scope, unavailable financial data, research-only learning status, local export and XSS protection.');
  console.log('PASS: local valuation editor: invalid JSON does not submit, synthetic example explicitly labeled, structured local action, bilingual results and no trading authority.');
  console.log('PASS: queued action completion: wait for the original result, display final path or failure, authenticated tracking and exactly one submission.');
  console.log('PASS: static markup, disconnected state, token header, real schema aliases, synthetic label, manual proposal approval control, XSS containment, scanner pending filter, Equity conversion, fully Arabic dynamic news copy with accurate common-event names and safe unknown-title fallbacks, original English news titles in English mode, news freshness and stale source distinction, calendar original source link, ambiguous-session translation, unattributed cost warning and no double subtraction. No browser or visual verification performed.');
})().catch(e=>{console.error(e);process.exitCode=1;});

