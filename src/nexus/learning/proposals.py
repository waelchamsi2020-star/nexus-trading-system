"""Account-isolated research queue. Approval never changes live configuration."""
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path


class ProposalStore:
    def __init__(self, path, account_key):
        if not isinstance(account_key,str) or not account_key:raise ValueError('Account partition required')
        self.account=account_key
        self.db=sqlite3.connect(path)
        # Vulture review: sqlite3 uses row_factory to provide named-row access.
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''CREATE TABLE IF NOT EXISTS proposals(
          id TEXT,account_key TEXT,created_at REAL,proposal_type TEXT,current_value TEXT,
          proposed_value TEXT,evidence_path TEXT,evidence_sha256 TEXT,status TEXT,reason TEXT,
          PRIMARY KEY(id,account_key));
          CREATE TABLE IF NOT EXISTS proposal_audit(
          id INTEGER PRIMARY KEY,proposal_id TEXT,account_key TEXT,at REAL,status TEXT,reason TEXT);''')

    def close(self):self.db.close()

    def create_proposal(self, proposal_type, current_value, proposed_value, evidence_path, proposal_id=None):
        if not isinstance(proposal_type,str) or not 1<=len(proposal_type)<=80:raise ValueError('Proposal type required')
        path=Path(evidence_path).resolve();blob=path.read_bytes()
        if not blob:raise ValueError('Nonempty research evidence required')
        current=json.dumps(current_value,sort_keys=True,allow_nan=False)
        proposed=json.dumps(proposed_value,sort_keys=True,allow_nan=False)
        identity=uuid.uuid4().hex if proposal_id is None else proposal_id
        if not isinstance(identity,str) or not identity:raise ValueError('Proposal identity required')
        fingerprint=hashlib.sha256(blob).hexdigest()
        with self.db:
            existing=self.db.execute('SELECT * FROM proposals WHERE id=? AND account_key=?',(identity,self.account)).fetchone()
            if existing:
                if (existing['proposal_type'],existing['current_value'],existing['proposed_value'],existing['evidence_sha256'])!=(proposal_type,current,proposed,fingerprint):
                    raise ValueError('Proposal idempotency conflict')
                return identity
            now=time.time()
            self.db.execute('INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?,?,?)',
                (identity,self.account,now,proposal_type,current,proposed,str(path),fingerprint,'PENDING',''))
            self.db.execute('INSERT INTO proposal_audit(proposal_id,account_key,at,status,reason) VALUES(?,?,?,?,?)',
                            (identity,self.account,now,'PENDING','Research only; no execution authority'))
        return identity

    def list_proposals(self):
        return [dict(x) for x in self.db.execute('SELECT * FROM proposals WHERE account_key=? ORDER BY created_at,id',(self.account,))]

    def _decide(self, identity, status, reason):
        if not isinstance(reason,str) or not reason.strip():raise ValueError('Review reason required')
        with self.db:
            row=self.db.execute('SELECT * FROM proposals WHERE id=? AND account_key=?',(identity,self.account)).fetchone()
            if row is None:raise KeyError(identity)
            if row['status']==status and row['reason']==reason:return
            if row['status']!='PENDING':raise ValueError('Research decision is terminal')
            if hashlib.sha256(Path(row['evidence_path']).read_bytes()).hexdigest()!=row['evidence_sha256']:
                raise ValueError('Research evidence changed')
            self.db.execute('UPDATE proposals SET status=?,reason=? WHERE id=? AND account_key=?',(status,reason,identity,self.account))
            self.db.execute('INSERT INTO proposal_audit(proposal_id,account_key,at,status,reason) VALUES(?,?,?,?,?)',
                            (identity,self.account,time.time(),status,reason))

    def approve_proposal(self, identity, reason):self._decide(identity,'APPROVED_RESEARCH_ONLY',reason)

    def reject_proposal(self, identity, reason):self._decide(identity,'REJECTED',reason)
