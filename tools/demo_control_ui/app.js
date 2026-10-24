const form=document.querySelector('#limits'),message=document.querySelector('#result');
const token=document.querySelector('meta[name="nexus-token"]').content;
let revision=null,dirty=false,busy=false,refreshing=false,latest=null,saveTimer=null;
const inputs=[...form.querySelectorAll('input')];
function setInputsDisabled(disabled){for(const input of inputs)input.disabled=disabled;}
function fill(){if(!latest?.limits)return;revision=latest.limits.revision;
 for(const [key,value] of Object.entries(latest.limits.values)){const input=form.elements.namedItem(key);if(input)input.value=value;}}
async function api(path,body){
 const response=await fetch(path,{method:body?'POST':'GET',headers:{'X-Nexus-Token':token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 const result=await response.json();if(!response.ok||result.ok===false)throw Error(result.error||'تعذر تطبيق القيم');return result;
}
function showStatus(data){
 const status=document.querySelector('#status'),s=data.status||{};
 if(data.error){status.textContent='تعذر التحقق من حالة المنفّذ: '+data.error;return;}
 if(!data.status_timestamp){status.textContent='لا توجد حالة حديثة من منفّذ التداول.';return;}
 if(!data.fresh){
  const stamp=new Date(data.status_timestamp*1000).toLocaleString('ar');
  status.textContent=`لا يوجد تحديث حديث من المنفّذ • آخر سجل ${stamp} • الحالة المسجلة: ${s.mode==='DEMO_LIVE'?'تجريبي':(s.mode||'غير معروف')} • السبب: ${data.stop_reason||'انقطاع التحديث'}`;
  return;
 }
 status.textContent=`حساب تجريبي ${s.account??'—'} • ${data.running?'المنفّذ يعمل':'المنفّذ متوقف: '+(data.stop_reason||'—')} • ${s.open_positions??'—'} مراكز • الرصيد ${s.balance??'—'} $`;
}
async function refresh(){
 if(refreshing)return;refreshing=true;
 try{
  const data=await api('/api/state');latest=data;showStatus(data);
  setInputsDisabled(!data.limits||!Array.isArray(inputs)||data.limits.values==null);
  if(!dirty&&!busy)fill();
 }catch(error){latest=null;setInputsDisabled(true);document.querySelector('#status').textContent='تعذر الاتصال بخدمة الحدود: '+error.message;}
 finally{refreshing=false;}
}
async function autosave(){
 if(busy||!latest?.limits||revision===null||!form.reportValidity())return;
 busy=true;setInputsDisabled(true);
 try{
  const values={...latest.limits.values};
  for(const input of inputs){const raw=input.valueAsNumber;if(!Number.isFinite(raw))throw Error('أدخل قيمة صحيحة في كل خانة.');values[input.name]=raw;}
  const result=await api('/api/action',{action:'limits',revision,values});
  revision=result.limits.revision;dirty=false;message.textContent='طُبّقت القيم الجديدة تلقائيًا.';
  await refresh();
 }catch(error){message.textContent='لم تُطبّق القيم: '+error.message;}
 finally{busy=false;setInputsDisabled(!latest?.limits);}
}
form.addEventListener('input',()=>{
 dirty=true;message.textContent='سيجري تطبيق التعديل تلقائيًا بعد التوقف عن الكتابة.';
 clearTimeout(saveTimer);saveTimer=setTimeout(autosave,900);
});
form.addEventListener('submit',event=>event.preventDefault());
refresh();setInterval(refresh,5000);
