"""合成资料源的 HTTP 传输，仅用于本地授权演练。"""
import argparse
from contextlib import contextmanager
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from urllib.parse import parse_qs, urlsplit

from .protocol import Source

def json_bytes(value):
    return json.dumps(value,ensure_ascii=False).encode()

@contextmanager
def running_source(port=0):
    source=Source()
    source.stage=0
    source.options={}
    source.log=[]
    source.lock=threading.RLock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass
        def run_request(self):
            u=urlsplit(self.path)
            q={k:v[-1] for k,v in parse_qs(u.query,keep_blank_values=True).items()}
            body=self.rfile.read(int(self.headers.get("Content-Length",0)))
            with source.lock:
                if u.path=="/health":
                    result=(200,{"Content-Type":"application/json"},json_bytes({"status":"ok","name":source.name}))
                elif u.path=="/__control" and self.command=="POST":
                    update=json.loads(body or b"{}")
                    source.stage=int(update.pop("stage",source.stage))
                    source.options.update(update)
                    result=(200,{"Content-Type":"application/json"},json_bytes({"stage":source.stage}))
                elif u.path=="/__log":
                    result=(200,{"Content-Type":"application/json"},json_bytes(source.log))
                else:
                    source.log.append({"method":self.command,"path":u.path,"query":q,"stage":source.stage})
                    try:
                        result=source.route(self.command,u.path,q,self.headers,body)
                    except (ValueError,KeyError,IndexError) as error:
                        result=(400,{"Content-Type":"application/json"},json_bytes({"error":"请求不符合来源契约","detail":str(error)}))
            status,headers,data=result
            if isinstance(data,str):data=data.encode()
            self.send_response(status)
            for k,v in headers.items():self.send_header(k,str(v))
            self.send_header("Content-Length",str(len(data)))
            self.end_headers()
            if self.command!="HEAD":
                try:self.wfile.write(data)
                except (BrokenPipeError,ConnectionResetError):pass
        do_GET=do_POST=do_REPORT=do_PROPFIND=do_HEAD=run_request
    server=ThreadingHTTPServer(("0.0.0.0",port),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    source.base=f"http://127.0.0.1:{server.server_port}"
    if hasattr(source,"start"):source.start()
    try:yield f"http://127.0.0.1:{server.server_port}",source
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
        if hasattr(source,"stop"):source.stop()

def main():
    parser=argparse.ArgumentParser(description="启动本地合成资料源")
    parser.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    with running_source(args.port) as (base,source):
        print("资料源就绪："+base,flush=True)
        threading.Event().wait()

if __name__=="__main__":main()
