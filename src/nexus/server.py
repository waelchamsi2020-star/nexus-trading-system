"""Token-authenticated loopback UI service with no external API exposure."""
from __future__ import annotations

import hmac
import json
import logging
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

LOG=logging.getLogger("nexus")


class LocalServer:
    def __init__(self,engine,ui_dir,port=0):
        self.engine,self.ui=engine,Path(ui_dir)
        self.token=secrets.token_urlsafe(32)
        parent=self
        class Handler(BaseHTTPRequestHandler):
            # Vulture review: stdlib HTTPServer/BaseHTTPRequestHandler uses this named override dynamically.
            server_version="Quant Trading AI"
            # Vulture review: stdlib HTTPServer/BaseHTTPRequestHandler uses this named override dynamically.
            def log_message(self,fmt,*args):
                # Do not log headers, tokens or request body.
                if args and str(args[1] if len(args)>1 else "") not in ("200","304"):
                    LOG.debug(fmt,*args)
            def guard(self,api=False):
                if self.headers.get("Host") not in parent.hosts:
                    self.reply(403,{"ok":False,"error":"Host مرفوض"});return False
                origin=self.headers.get("Origin")
                if origin is not None and origin!=parent.origin:
                    self.reply(403,{"ok":False,"error":"Origin مرفوض"});return False
                if self.headers.get("Sec-Fetch-Site") in ("cross-site","same-site"):
                    self.reply(403,{"ok":False,"error":"طلب خارجي مرفوض"});return False
                if api and not hmac.compare_digest(self.headers.get("X-Nexus-Token",""),parent.token):
                    self.reply(401,{"ok":False,"error":"جلسة غير مصرح بها"});return False
                return True
            def reply(self,status,payload,content_type="application/json; charset=utf-8"):
                if isinstance(payload,(dict,list)):
                    raw=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode("utf-8")
                elif isinstance(payload,str):raw=payload.encode("utf-8")
                else:raw=payload
                self.send_response(status);self.send_header("Content-Type",content_type)
                self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store")
                self.send_header("X-Content-Type-Options","nosniff");self.send_header("Referrer-Policy","no-referrer")
                self.send_header("X-Frame-Options","DENY")
                self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
                self.end_headers()
                try:self.wfile.write(raw)
                except (BrokenPipeError,ConnectionResetError):pass
            # Vulture review: stdlib HTTPServer/BaseHTTPRequestHandler uses this named override dynamically.
            def do_GET(self):
                route=urlsplit(self.path).path
                if not self.guard(route.startswith("/api/")):return
                if route=="/api/state":
                    encoded=getattr(parent.engine,'snapshot_json',None)
                    self.reply(200,encoded() if callable(encoded) else parent.engine.snapshot());return
                if route=="/api/action-result":
                    try:
                        query=parse_qs(urlsplit(self.path).query,keep_blank_values=True,max_num_fields=1)
                        if set(query)!={"id"} or len(query["id"])!=1:raise ValueError("معرّف طلب واحد مطلوب")
                    except ValueError:
                        self.reply(400,{"ok":False,"error":"معرّف طلب واحد مطلوب"});return
                    self.reply(200,parent.engine.action_result(query["id"][0]));return
                files={"/":("index.html","text/html; charset=utf-8"),"/index.html":("index.html","text/html; charset=utf-8"),
                       "/style.css":("style.css","text/css; charset=utf-8"),
                       "/i18n.js":("i18n.js","text/javascript; charset=utf-8"),
                       "/session-view.js":("session-view.js","text/javascript; charset=utf-8"),
                       "/app.js":("app.js","text/javascript; charset=utf-8")}
                if route not in files:self.reply(404,{"error":"غير موجود"});return
                name,ctype=files[route]
                try:
                    text=(parent.ui/name).read_text(encoding="utf-8")
                    if name=="index.html":text=text.replace('<meta name="nexus-token" content="">','<meta name="nexus-token" content="'+parent.token+'">')
                    self.reply(200,text,ctype)
                except OSError:self.reply(503,{"error":"ملفات الواجهة غير متاحة"})
            # Vulture review: stdlib HTTPServer/BaseHTTPRequestHandler uses this named override dynamically.
            def do_POST(self):
                if not self.guard(True):return
                if urlsplit(self.path).path!="/api/action":self.reply(404,{"error":"غير موجود"});return
                if self.headers.get("Content-Type","").split(";")[0]!="application/json":
                    self.reply(415,{"error":"JSON مطلوب"});return
                try:
                    length=int(self.headers.get("Content-Length","0"))
                    if not 0<length<=32768:raise ValueError("حجم طلب غير مسموح")
                    def reject_nonfinite(v):raise ValueError("رقم غير صالح: "+v)
                    payload=json.loads(self.rfile.read(length).decode("utf-8"),parse_constant=reject_nonfinite)
                    result=parent.engine.action(payload)
                    self.reply(200,result)
                except (ValueError,KeyError,TypeError,UnicodeError) as exc:self.reply(400,{"ok":False,"error":str(exc),"message":str(exc)})
                except Exception as exc:
                    LOG.exception("API action failure");self.reply(409,{"ok":False,"error":str(exc),"message":str(exc)})
            # Vulture review: stdlib HTTPServer/BaseHTTPRequestHandler uses this named override dynamically.
            def do_OPTIONS(self):self.reply(403,{"error":"الطلبات الخارجية غير مسموحة"})
        self.http=ThreadingHTTPServer(("127.0.0.1",port),Handler)
        # Vulture review: stdlib HTTPServer/BaseHTTPRequestHandler uses this named override dynamically.
        self.http.daemon_threads=True
        port=self.http.server_address[1]
        self.hosts={"127.0.0.1:"+str(port)}
        self.origin=f"http://127.0.0.1:{port}";self.thread=None
    def start(self):
        self.thread=threading.Thread(target=self.http.serve_forever,name="local-interface",daemon=True);self.thread.start()
        return self.origin
    def stop(self):self.http.shutdown();self.http.server_close()
