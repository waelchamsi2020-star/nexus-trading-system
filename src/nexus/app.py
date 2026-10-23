"""One entry point for Windows: embedded local UI, always READ_ONLY on launch."""
from __future__ import annotations

import argparse
import ctypes
import logging
import os
import sys
import threading
import time
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .demo_bridge import DemoBridge
from .engine import Engine
from .server import LocalServer


class AlreadyRunningError(RuntimeError):
    """Raised when the protected desktop instance is already active."""


def app_root():
    return Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parents[2]))


def window_geometry(available_width, available_height):
    """Presentation-only bounds; never require a window larger than its display."""
    if any(isinstance(x,bool) or not isinstance(x,int) or x<=0
           for x in (available_width,available_height)):
        raise ValueError("Positive display dimensions are required")
    width=min(1450,max(1,available_width-32))
    height=min(950,max(1,available_height-32))
    return {"width":width,"height":height,"min_size":(min(640,width),min(480,height)),"maximized":True}


def desktop_window_geometry():
    width,height=1280,800
    if os.name=="nt":
        try:
            from ctypes import wintypes
            area=wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48,0,ctypes.byref(area),0):
                measured=(area.right-area.left,area.bottom-area.top)
                if min(measured)>0:width,height=measured
        except (AttributeError,OSError):
            pass
    return window_geometry(width,height)


class InstanceLock:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.handle=None;self.file=None
    def acquire(self):
        if os.name=="nt":
            kernel=ctypes.windll.kernel32
            kernel.CreateMutexW.restype=ctypes.c_void_p
            self.handle=kernel.CreateMutexW(None,False,"Local\\NEXUS-Demo-Institution-v1")
            if not self.handle or kernel.GetLastError()==183:
                raise AlreadyRunningError("Quant Trading AI مفتوح بالفعل. استُخدمت النافذة الحالية بدل تشغيل نسخة ثانية.")
        self.file=self.path.open("a+b")
        if self.path.stat().st_size==0:self.file.write(b"0");self.file.flush()
        self.file.seek(0)
        if os.name=="nt":
            import msvcrt
            try:msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as exc:raise RuntimeError("قاعدة اليوم تستخدمها نسخة أخرى من Quant Trading AI") from exc
    def close(self):
        if self.file:
            if os.name=="nt":
                import msvcrt
                try:self.file.seek(0);msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
                except OSError:pass
            self.file.close()
        if self.handle:
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(self.handle))


def focus_existing_window():
    """Bring an existing Quant Trading AI desktop window forward without treating it as a fault."""
    if os.name != "nt":
        return False
    user32=ctypes.windll.user32
    found=[]
    callback_type=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
    def visit(hwnd,_):
        if not user32.IsWindowVisible(hwnd):
            return True
        length=user32.GetWindowTextLengthW(hwnd)
        if length:
            title=ctypes.create_unicode_buffer(length+1)
            user32.GetWindowTextW(hwnd,title,length+1)
            if "QUANT TRADING AI" in title.value.upper() or "NEXUS" in title.value.upper():
                found.append(hwnd)
                return False
        return True
    user32.EnumWindows(callback_type(visit),0)
    if not found:
        return False
    user32.ShowWindow(found[0],9)
    user32.SetForegroundWindow(found[0])
    return True


def main():
    parser=argparse.ArgumentParser(description="Quant Trading AI Demo-only local trading research")
    parser.add_argument("--browser",action="store_true",help="Use the default browser if WebView unavailable")
    parser.add_argument("--headless",action="store_true",help="Local test service; no trading activation")
    parser.add_argument("--no-connect",action="store_true")
    parser.add_argument("--port",type=int,default=0)
    parser.add_argument("--data-dir",default="")
    args=parser.parse_args()
    root=app_root()
    # Stable profile and mutex retain pre-rename ledger and single-instance protection.
    data=Path(args.data_dir) if args.data_dir else Path(os.environ.get("LOCALAPPDATA",str(root)))/"NEXUS"
    data.mkdir(parents=True,exist_ok=True)
    handler=RotatingFileHandler(data/"nexus.log",maxBytes=2_000_000,backupCount=5,encoding="utf-8")
    logging.basicConfig(level=logging.INFO,handlers=[handler],format="%(asctime)s %(levelname)s %(message)s")
    lock=InstanceLock(data/"instance.lock")
    engine=server=None
    try:
        lock.acquire()
        demo_directory = data / "demo-live-20261019"
        integrated_demo = (demo_directory / "user-controls-enabled").exists()
        engine=Engine(root,data)
        # The legacy engine supplies read-only research even in integrated mode.
        # _connect starts READ_ONLY; DemoBridge rejects every legacy activation.
        # The dedicated Demo service remains the sole authorized sender.
        engine.start_worker(auto_connect=not args.no_connect)
        desktop_backend = (DemoBridge(engine, demo_directory)
                           if integrated_demo else engine)
        server=LocalServer(desktop_backend,root/"ui",args.port);url=server.start()
        (data / "desktop-url.txt").write_text(url, encoding="utf-8")
        if args.headless:
            print("Quant Trading AI local test service: "+url,flush=True)
            while engine.running:time.sleep(.5)
        elif args.browser:
            webbrowser.open(url)
            while engine.running:time.sleep(.5)
        else:
            try:
                import webview
                window=webview.create_window("Quant Trading AI",url,**desktop_window_geometry(),text_select=True)
                def close_window_when_service_stops():
                    while engine.running:
                        time.sleep(.2)
                    try:window.destroy()
                    except Exception:
                        logging.getLogger(__name__).exception("Handled boundary failure")
                threading.Thread(target=close_window_when_service_stops,name="nexus-window-shutdown",daemon=True).start()
                webview.start(gui="edgechromium",private_mode=True)
            except Exception as exc:
                logging.getLogger(__name__).exception("Embedded WebView unavailable; use browser")
                if os.name=="nt":ctypes.windll.user32.MessageBoxW(None,"تعذر فتح نافذة WebView. ستفتح الواجهة في المتصفح المحلي.\n"+str(exc),"Quant Trading AI",0)
                webbrowser.open(url)
                while engine.running:time.sleep(.5)
    except AlreadyRunningError as exc:
        logging.getLogger(__name__).info("SECOND_INSTANCE_FOCUSED %s",exc)
        if args.headless:
            print(str(exc),file=sys.stderr)
            return 1
        if not focus_existing_window() and os.name=="nt":
            ctypes.windll.user32.MessageBoxW(None,str(exc),"Quant Trading AI",0x40)
        return 0
    except Exception as exc:
        logging.getLogger(__name__).exception("Quant Trading AI startup failed")
        if os.name=="nt" and not args.headless:ctypes.windll.user32.MessageBoxW(None,str(exc),"Quant Trading AI",0x10)
        else:print(str(exc),file=sys.stderr)
        return 1
    finally:
        if engine:engine.stop_worker()
        if server:server.stop()
        lock.close()
    return 0


if __name__=="__main__":raise SystemExit(main())
