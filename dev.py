import sys
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
except:
    pass
import subprocess, time, threading, json, re
from pathlib import Path
import http.server
import socketserver
from functools import partial

def ensure_root():
    if Path('templates').exists() and Path('content').exists():
        return
    if Path('../templates').exists():
        print("[ERROR] Run from project root: cd ..")
        sys.exit(1)
    print(f"[ERROR] templates/ not found in {Path.cwd()}")
    sys.exit(1)

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def get_port():
    try:
        import yaml
        candidates = [Path("_data/site.yaml"), Path("_data/site.yml"), Path("_data/config.yaml"), Path("metadata.yaml"), Path("_data/metadata.yaml")]
        for f in candidates:
            if f.exists():
                data = yaml.safe_load(f.read_text(encoding='utf-8')) or {}
                
                url = data.get('url','') or data.get('site',{}).get('url','') if isinstance(data.get('site'), dict) else data.get('url','')
                if url and isinstance(url, str) and ':' in url:
                    
                    m = re.search(r':(\d{2,5})(?:/|$)', url)
                    if m:
                        port = m.group(1)
                        if port.isdigit() and 1024 <= int(port) <= 65535:
                            return int(port)
    except:
        pass
    return 8000

VERSION = "PYCORA MEDUSA v2.3.0"
build_timestamp = str(time.time())
build_lock = threading.Lock()

def print_banner(port):
    try:
        print(f"{Colors.CYAN}==================================================={Colors.RESET}")
        print(f"{Colors.BOLD}  PYTHON SSG BY AXCORA{Colors.CYAN}")
        print(f"{Colors.YELLOW}  PYCORA SSG by Axcora Technology - www.axcora.com{Colors.RESET}")
        print(f"{Colors.CYAN}==================================================={Colors.RESET}")
        print(f"{Colors.YELLOW}  {VERSION}{Colors.RESET}")
        print(f"{Colors.CYAN}  Local: http://localhost:{port}/{Colors.RESET}")
        print(f"{Colors.CYAN}==================================================={Colors.RESET}")
    except:
        print(f"PYCORA MEDUSA {VERSION} - http://localhost:{port}/")

LIVE_RELOAD_JS = """
<script id="__pycora_livereload">
(function(){
  let last = null;
  async function check(){
    try{
      const r = await fetch('/__livereload.json?t='+Date.now(), {cache:'no-store'});
      const j = await r.json();
      if(last===null){ last=j.time; }
      else if(j.time!==last){
        console.log('%c[PyCora Medusa] %cChange detected, reloading...','color:#00d4ff;font-weight:bold','color:yellow');
        last=j.time;
        location.reload();
      }
    }catch(e){}
  }
  setInterval(check, 800);
  console.log('%c[PyCora Medusa] %cLiveReload active','color:#00d4ff;font-weight:bold','color:#00ff88');
})();
</script>
"""

def build():
    global build_timestamp
    with build_lock:
        start = time.time()
        print(f"\n{Colors.DIM}  [{time.strftime('%H:%M:%S')}] {Colors.YELLOW}building...{Colors.RESET}")
        result = subprocess.run([sys.executable, "ssg.py"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        for line in result.stdout.splitlines():
            if any(x in line for x in ['[CONTROLLER]','[PAGINATION]','[DYNAMIC','[11TY','ready','ERROR','WARN','PAX','MEDUSA','FREE']):
                if 'ready' in line.lower():
                    print(f"{Colors.GREEN}   {line}{Colors.RESET}")
                elif 'ERROR' in line:
                    print(f"{Colors.RED}  ✖ {line}{Colors.RESET}")
                else:
                    print(f"{Colors.DIM}  │ {Colors.RESET}{line}")
        if result.stderr:
            for l in result.stderr.splitlines():
                if l.strip():
                    print(f"{Colors.RED}  {l}{Colors.RESET}")
        build_timestamp = str(time.time())
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        (output_dir / "__livereload.json").write_text(json.dumps({"time": build_timestamp}), encoding='utf-8')
        injected = 0
        for html_file in output_dir.rglob("*.html"):
            try:
                content = html_file.read_text(encoding='utf-8')
                if '__pycora_livereload' in content:
                    continue
                if '</body>' in content:
                    content = content.replace('</body>', LIVE_RELOAD_JS + '</body>')
                elif '</html>' in content:
                    content = content.replace('</html>', LIVE_RELOAD_JS + '</html>')
                else:
                    content = content + LIVE_RELOAD_JS
                html_file.write_text(content, encoding='utf-8')
                injected += 1
            except:
                pass
        elapsed = time.time() - start
        print(f"{Colors.GREEN}  {Colors.BOLD}Build complete{Colors.RESET}{Colors.GREEN} in {elapsed:.2f}s - injected {injected} files [HMR]{Colors.RESET}")
        return result.returncode == 0

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        super().end_headers()
    def do_GET(self):
        if '__livereload' in self.path:
            output_dir = Path(self.directory)
            json_file = output_dir / "__livereload.json"
            if not json_file.exists():
                json_file.write_text(json.dumps({"time": build_timestamp}), encoding='utf-8')
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json_file.read_bytes())
            return
        return super().do_GET()
    def log_message(self, format, *args):
        if '__livereload' in format%args:
            return
        msg = format%args
        if 'GET' in msg:
            print(f"{Colors.DIM}  {time.strftime('%H:%M:%S')} [HTTP] {Colors.RESET}{msg}")

def serve(port, output_dir):
    handler = partial(Handler, directory=str(output_dir.resolve()))
    class ReuseTCPServer(socketserver.TCPServer):
        allow_reuse_address = True
    with ReuseTCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

def main():
    ensure_root()
    port = get_port()
    print_banner(port)
    build()
    output_dir = Path("output")
    t = threading.Thread(target=serve, args=(port, output_dir), daemon=True)
    t.start()
    print(f"{Colors.DIM}  Press {Colors.BOLD}Ctrl+C{Colors.RESET}{Colors.DIM} to stop{Colors.RESET}")
    print()
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        class WatchHandler(FileSystemEventHandler):
            def __init__(self):
                self.last_time = 0
                self.last_file = ""
            def on_any_event(self, event):
                if event.is_directory:
                    return
                p = event.src_path
                if any(x in p for x in ['output','__pycache__','.git','.pyc','node_modules','dist','site']):
                    return
                if not any(p.endswith(ext) for ext in ['.md','.html','.pax','.yaml','.yml','.css','.js','.json','.py','.lax','.gax']):
                    return
                now = time.time()
                if now - self.last_time < 0.4:
                    return
                if p == self.last_file and now - self.last_time < 1.0:
                    return
                self.last_time = now
                self.last_file = p
                print(f"\n{Colors.CYAN} [WATCH PYCORA] {Path(p).name} changed → rebuilding{Colors.RESET}")
                build()
        observer = Observer()
        observer.schedule(WatchHandler(), ".", recursive=True)
        observer.start()
        print(f"{Colors.DIM}  Watching...{Colors.RESET}")
        while True:
            time.sleep(1)
    except ImportError:
        print("[WATCH] pip install watchdog for instant reload, using polling")
        mtimes = {}
        while True:
            time.sleep(0.6)
            changed = False
            for p in Path(".").rglob("*"):
                if any(x in str(p) for x in ['output','__pycache__','.git','dist','site']):
                    continue
                if p.is_file() and p.suffix in ['.md','.html','.pax','.yaml','.yml','.css','.js','.py','.lax','.gax']:
                    try:
                        mt = p.stat().st_mtime
                        if p not in mtimes:
                            mtimes[p] = mt
                        elif mtimes[p] != mt:
                            mtimes[p] = mt
                            print(f"[WATCH] {p} changed")
                            changed = True
                    except:
                        pass
            if changed:
                build()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  💀 MedusaPYCORA stopped - Bye!\n")
        sys.exit(0)
