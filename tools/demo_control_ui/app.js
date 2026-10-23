const form=document.querySelector('#limits'),message=document.querySelector('#result');
const token=document.querySelector('meta[name="nexus-token"]').content;
let revision=null,dirty=false,pending=null,busy=false,refreshing=false,latest=null;
const save=form.querySelector('[type="submit"]');save.disabled=true;
const buttons=()=>save.disabled=busy||!latest?.limits||revision===null;
const fill=()=>{if(!latest?.limits)return;revision=latest.limits.revision;
 for(const [k,v] of Object.entries(latest.limits.values)){const input=form.elements.namedItem(k);if(input)input.value=v;}};
document.querySelector('#reload-limits').addEventListener('click',()=>{if(busy)return;dirty=false;pending=null;fill();buttons();message.textContent='حُمّلت أحدث الحدود المحفوظة.';});
async function api(path,body){
 const response=await fetch(path,{method:body?'POST':'GET',headers:{'X-Nexus-Token':token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 const result=await response.json();if(!response.ok||result.ok===false)throw Error(result.error||'تعذر الحفظ');return result;
}
form.addEventListener('input',()=>dirty=true);
async function refresh(){
 if(refreshing)return;refreshing=true;
 try{
  const data=await api('/api/state'),s=data.status||{};latest=data;
  document.querySelector('#status').textContent=data.error||`حساب ${s.account??'—'} • ${data.running?'المنفّذ يعمل':('متوقف: '+(data.stop_reason||'الحالة قديمة'))} • ${s.open_positions??'—'} مراكز • الرصيد ${s.balance??'—'} $`;
  if(!dirty&&pending===null)fill();
  if(pending!==null&&data.limits?.revision>pending){message.textContent=`حلّت حدود أحدث محل تعديلك — الإصدار ${data.limits.revision}`;pending=null;if(!dirty)fill();}
  else if(pending!==null&&data.fresh&&s.limits_revision===pending){message.textContent=`طُبقت الحدود في محرك التنفيذ — الإصدار ${pending}`;revision=pending;pending=null;}
 }catch(e){latest=null;document.querySelector('#status').textContent='تعذر الاتصال بالخدمة: '+e.message;}
 finally{refreshing=false;buttons();}
}
form.addEventListener('submit',async e=>{
 e.preventDefault();if(busy||!latest?.limits||revision===null)return;busy=true;buttons();
 try{
  const values={...latest.limits.values};for(const [key,value] of new FormData(form))values[key]=Number(value);
  const result=await api('/api/action',{action:'limits',revision,values});
  pending=result.limits.revision;revision=pending;dirty=false;
  message.textContent='حُفظت الحدود؛ انتظار تأكيد تطبيقها من المنفّذ…';await refresh();
 }catch(err){message.textContent=err.message+' — اضغط تحميل الحدود الحالية لمراجعة أحدث تعديل.';}finally{busy=false;buttons();}
});
refresh();setInterval(refresh,2000);
