import subprocess
import sys
import webbrowser
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[91m'
    RESET = '\033[0m'

class Watcher(FileSystemEventHandler):
    def __init__(self):
        self.last_build = 0
        self.cooldown = 1.5
    
    def on_any_event(self, event):
        
        if event.is_directory:
            return
        
        src_path = str(event.src_path)
        ext = Path(src_path).suffix.lower()
        
        if ext not in ['.md', '.html', '.yaml', '.py', '.css', '.js']:
            return
        
        current_time = time.time()
        if current_time - self.last_build < self.cooldown:
            return
        
        self.last_build = current_time
        
        filename = Path(src_path).name
        print(f"\n{Colors.YELLOW}📝 {filename} changed...{Colors.RESET}")
        print(f"{Colors.DIM}🔄 Rebuilding...{Colors.RESET}")
        
        result = subprocess.run([sys.executable, "ssg.py"], capture_output=True, text=True)
        print(result.stdout)
        
        print(f"{Colors.GREEN}✅ Build complete! Refresh browser.{Colors.RESET}\n")

def print_banner():
    print(f"""
{Colors.CYAN}══════════════════════════════════════════════════════════
                                                              
  {Colors.BOLD}██████╗ ██╗   ██╗ ██████╗ ██████╗ ██████╗  █████╗ {Colors.CYAN}
  {Colors.BOLD}██╔══██╗╚██╗ ██╔╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗{Colors.CYAN}
  {Colors.BOLD}██████╔╝ ╚████╔╝ ██║     ██║   ██║██████╔╝███████║{Colors.CYAN}
  {Colors.BOLD}██╔═══╝   ╚██╔╝  ██║     ██║   ██║██╔══██╗██╔══██║{Colors.CYAN}
  {Colors.BOLD}██║        ██║   ╚██████╗╚██████╔╝██║  ██║██║  ██║{Colors.CYAN}
  {Colors.BOLD}╚═╝        ╚═╝    ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝{Colors.CYAN}
                                                             
  {Colors.GREEN}✦ Development Server ✦{Colors.CYAN}                      
  {Colors.DIM}Auto-rebuild • Live reload{Colors.CYAN}                      
══════════════════════════════════════════════════════════{Colors.RESET}
    """)

def main():
    print_banner()
    
    # Build pertama
    print(f"{Colors.DIM}📦 Initial build...{Colors.RESET}")
    subprocess.run([sys.executable, "ssg.py"])
    
    print(f"""
{Colors.GREEN}➜  Server: {Colors.BOLD}http://localhost:8000{Colors.RESET}
{Colors.DIM}➜  Watching: content/, templates/, static/{Colors.RESET}
{Colors.DIM}➜  Press Ctrl+C to stop{Colors.RESET}
    """)
    
    webbrowser.open('http://localhost:8000')
    
    os.chdir('output')
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    os.chdir('..')
    
    observer = Observer()
    watcher = Watcher()
    
    observer.schedule(watcher, 'content', recursive=True)
    observer.schedule(watcher, 'templates', recursive=True)
    
    if Path('static').exists():
        observer.schedule(watcher, 'static', recursive=True)
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        server.terminate()
        print(f"\n{Colors.DIM}👋 PyCora stopped.{Colors.RESET}")

if __name__ == "__main__":
    main()