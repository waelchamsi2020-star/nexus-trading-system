/* Actual execution controls, sharing the desktop's authenticated session. */
(() => {
  let revision = null, pending = null, dirty = false, busy = false, latest = null;
  const fields = [
    ['daily_loss_amount','حد الخسارة اليومي ($)'],['daily_profit_amount','هدف الربح اليومي ($)'],
    ['per_trade_loss_amount','حد خسارة الصفقة ($)'],['per_trade_profit_amount','هدف ربح الصفقة ($)']
  ];
  const panel = document.createElement('article');
  panel.id = 'demo-execution-panel';panel.className = 'panel';panel.hidden = true;
  panel.innerHTML = `<div class="panel-heading"><h2>التداول</h2></div>
    <div class="demo-facts"><span id="demo-scan"></span><span id="demo-open"></span><span id="demo-profit"></span></div>
    <p id="demo-decision" role="status"></p><p id="demo-data-time" class="tiny-note"></p>
    <div class="action-row"><button type="button" id="demo-toggle" class="button primary" disabled>تشغيل</button></div>
    <form id="demo-limits-form"><div class="form-grid">${fields.map(([key,label])=>`<label>${label}<input name="${key}" type="number" step="any" min="${key.startsWith('per_trade')||key==='kill_drawdown_percent'?0:0.000001}" ${key.endsWith('percent')?'max="100"':''} required></label>`).join('')}</div>
    <button class="button secondary" type="submit" disabled>حفظ وتطبيق الحدود</button>
    <button class="button secondary" type="button" id="demo-reload-limits">تحميل الحدود الحالية</button></form>
    <p id="demo-feedback" role="status" aria-live="polite"></p>
    <details><summary>كيفية تطبيق الحدود</summary><p>الحدود تطبق على الدخول الجديد، ولا تغير وقف أو هدف المراكز المفتوحة. تعديلها لا يمحو أرباح وخسائر اليوم. الأقل من حد خسارة الصفقة وحد نسبتها هو النافذ. الحجم الأقصى 0.01 لوت، والتداول على DEMO فقط. الوقف لا يضمن مبلغ الخسارة بسبب الانزلاق. صفر لهدف وخسارة الصفقة معاً يعيد استخدام ATR. يوم الحساب يبدأ 00:00 UTC.</p></details>`;
  document.querySelector('#view-overview .account-grid').insertAdjacentElement('afterend',panel);
  const form = panel.querySelector('form'), feedback = panel.querySelector('#demo-feedback');
  const toggle=panel.querySelector('#demo-toggle'), save=form.querySelector('[type="submit"]');
  const buttons=()=>{toggle.disabled=busy||Boolean(latest?.error)||!latest?.running;save.disabled=busy||!latest?.limits||revision===null;};
  const fillLimits=()=>{if(!latest?.limits)return;revision=latest.limits.revision;
    for(const [key,value] of Object.entries(latest.limits.values)){const input=form.elements.namedItem(key);if(input)input.value=value;}};
  panel.querySelector('#demo-reload-limits').addEventListener('click',()=>{
    if(busy)return;dirty=false;pending=null;fillLimits();feedback.textContent='حُمّلت أحدث الحدود المحفوظة.';buttons();});
  form.addEventListener('input',()=>dirty=true);
  async function send(body) {
    const response = await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json',
      'X-Nexus-Token':document.querySelector('meta[name="nexus-token"]').content},body:JSON.stringify(body)});
    const data = await response.json();if(!response.ok||data.ok===false)throw Error(data.error||data.message||'تعذر تنفيذ الطلب');return data;
  }
  form.addEventListener('submit',async e=>{
    e.preventDefault();if(busy||!latest?.limits||revision===null)return;busy=true;buttons();
    try {
      const values={...latest.limits.values};for(const [key,value] of new FormData(form))values[key]=Number(value);
      const result=await send({action:'demo_limits',values,revision});
      pending=result.limits.revision;revision=pending;dirty=false;
      feedback.textContent='حُفظت الحدود؛ انتظار تأكيد المنفّذ…';
    } catch(err){feedback.textContent=err.message+' — لتحميل تعديل نافذة أخرى اضغط «تحميل الحدود الحالية».';} finally {busy=false;buttons();}
  });
  panel.querySelector('#demo-toggle').addEventListener('click',async()=>{
    if(busy||!latest?.running)return;busy=true;buttons();
    try {const paused=latest.user_paused;await send({action:paused?'demo_resume':'demo_pause'});
      feedback.textContent=paused?'أُرسل طلب استئناف الدخول؛ انتظار تأكيد المنفّذ.':'أُرسل طلب إيقاف الدخول الجديد؛ المراكز المفتوحة تبقى محمية لدى الوسيط.';}
    catch(err){feedback.textContent=err.message;}finally{busy=false;buttons();}
  });
  window.renderDemoPanel = data => {
    if(!data){latest=null;buttons();return;}
    panel.hidden=false;document.body.classList.add('demo-integrated');
    latest=data;const s=data.status||{};
    const text=(id,value)=>{const target=document.getElementById(id);if(target)target.textContent=value;};
    if(!dirty&&pending===null)fillLimits();
    if(pending!==null&&data.limits?.revision>pending){
      feedback.textContent=`حلّت حدود أحدث محل تعديلك — الإصدار ${data.limits.revision}`;pending=null;if(!dirty)fillLimits();
    }else if(pending!==null&&data.fresh&&s.limits_revision===pending){
      feedback.textContent=`طُبقت الحدود — الإصدار ${pending}`;pending=null;
    }
    buttons();
    const header=document.getElementById('header-execution-mode');
    const setHeader=(label,detail)=>{
      if(!header)return;
      const language=document.getElementById('language-select')?.value||'ar';
      header.textContent=window.NEXUS_I18N?.translate(label,language)||label;
      header.title=detail||label;
      header.setAttribute('aria-label',detail?`${header.textContent}. ${detail}`:header.textContent);
    };
    if(data.error){
      setHeader('حالة المنفّذ غير متاحة',String(data.error));
      text('footer-state','حالة المنفّذ غير متاحة');
      for(const id of ['demo-scan','demo-open','demo-profit','demo-decision','demo-data-time'])text(id,'—');
      text('demo-decision','تعذرت قراءة حالة التنفيذ الحالية. لا تُعدّ البيانات القديمة حالة حية.');
      return;
    }
    const isPaused=data.user_paused;
    const label=!data.running?'التنفيذ متوقف':isPaused?'الدخول متوقف':s.daily_halt?'وقف الخسارة اليومي':s.target_halt?'هدف اليوم':'التنفيذ التجريبي يعمل';
    const detail=!data.running?`التفصيل: ${data.stop_reason||'لم تُنشر حالة حديثة'}`:isPaused?'إيقاف دخول جديد بطلب المستخدم':s.daily_halt?'بلغ حد الخسارة اليومي':s.target_halt?'بلغ هدف اليوم':'حلقة التنفيذ التجريبية نشطة';
    setHeader(label,detail);
    text('footer-state',`منفّذ واحد • ${s.symbol||'—'} ${s.timeframe||'—'} • حساب ${s.account??'—'}`);
    text('demo-scan',`النماذج: ${s.models??'—'} • ${s.symbol||'—'} ${s.timeframe||'—'}`);
    text('demo-open',`المراكز المفتوحة: ${s.open_positions??'—'}`);
    text('demo-profit',`صافي اليوم: ${s.daily_profit??'—'} $`);
    const names={NO_TRIGGER:'بلا إشارة',QUOTE_OUTSIDE_MODEL_ENTRY_ZONE:'السعر خارج منطقة الدخول',
      BROKER_MIN_STOP_DISTANCE:'مسافة الوقف لا يقبلها الوسيط',CANDIDATE:'إشارة مرشحة',
      TRADE_CASH_RISK_LIMIT:'تجاوز حد خسارة الصفقة',TRADE_RISK_LIMIT:'تجاوز نسبة المخاطرة',
      DAILY_LOSS_LIMIT:'بلغ حد الخسارة',DAILY_PROFIT_TARGET:'بلغ هدف اليوم',
      PORTFOLIO_EXPOSURE_LIMIT:'بلغ حد مخاطر المراكز',DAILY_LOSS_RESERVE:'لا توجد ميزانية مخاطرة كافية'};
    names.OVERLAPPING_OPPORTUNITY='فرصة متداخلة مع مركز قائم أو أمر في الشمعة نفسها';
    text('demo-decision',Object.entries(data.last_reasons||{}).map(([k,v])=>`${v} ${names[k]||k}`).join(' • ')||'انتظار أول شمعة مكتملة');
    text('demo-data-time',`آخر حالة: ${new Date(s.utc).toLocaleTimeString('ar-AE',{timeZone:'Asia/Dubai'})} • آخر شمعة: ${data.last_bar?new Date(data.last_bar*1000).toLocaleTimeString('ar-AE',{timeZone:'Asia/Dubai'}):'—'}`);
    toggle.textContent=isPaused?'استئناف الدخول':'إيقاف الدخول الجديد';toggle.disabled=!data.running||busy;
  };
})();
