'use strict';
/* Presentation only. Never deletes the reconciliation or learning ledger. */
(() => {
  const cutoff = now => Math.floor((now + 7200) / 86400) * 86400 - 7200;
  const active = new Set(['PROPOSED','PENDING_APPROVAL','PREPARED','SENDING','ACCEPTED','PARTIAL','FILLED','UNKNOWN']);
  function select(rows, now, limit=100) {
    const beginning=cutoff(now), pending=[], settled=[];
    for (const row of rows) {
      const status=String(row.status||row.state||'UNKNOWN').toUpperCase();
      const stamp=Number(row.updated_at??row.updated??row.created_at??row.created??row.time);
      if(active.has(status)||!['CLOSED','REJECTED','CANCELLED','EXPIRED'].includes(status)||!Number.isFinite(stamp)) pending.push(row);
      else if(stamp>=beginning) settled.push(row);
    }
    settled.sort((a,b)=>Number(b.updated_at??b.updated??b.created_at??b.created??b.time)-Number(a.updated_at??a.updated??a.created_at??a.created??a.time));
    return {rows:[...pending,...settled.slice(0,limit)],older:rows.length-pending.length-settled.length,omitted:Math.max(0,settled.length-limit),cutoff:beginning};
  }
  window.QuantSessionView={cutoff,select};
})();
