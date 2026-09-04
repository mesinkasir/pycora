import sys, io
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
except:
    pass
import subprocess
from pathlib import Path

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

VERSION = "MEDUSA VERSION - PYCORA V2.1.0 - FREE"

def print_banner():
    try:
        print(f"""
{Colors.CYAN}══════════════════════════════════════════════════════════
  {Colors.BOLD}██████╗ ██╗   ██╗ ██████╗ ██████╗ ██████╗  █████╗ {Colors.CYAN}
  {Colors.BOLD}██╔══██╗╚██╗ ██╔╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗{Colors.CYAN}
  {Colors.BOLD}██████╔╝ ╚████╔╝ ██║     ██║   ██║██████╔╝███████║{Colors.CYAN}
  {Colors.BOLD}██╔═══╝   ╚██╔╝  ██║     ██║   ██║██╔══██╗██╔══██║{Colors.CYAN}
  {Colors.BOLD}██║        ██║   ╚██████╗╚██████╔╝██║  ██║██║  ██║{Colors.CYAN}
  {Colors.BOLD}╚═╝        ╚═╝    ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝{Colors.CYAN}
  {Colors.YELLOW}{VERSION}{Colors.CYAN}
══════════════════════════════════════════════════════════{Colors.RESET}
        """)
    except:
        print(f"PYCORA - {VERSION}")

def ensure_root():
    if Path('templates').exists():
        return
    if Path('../templates').exists():
        print("[ERROR] cd ..")
        sys.exit(1)
    if not Path('templates').exists():
        print(f"[ERROR] templates/ not found in {Path.cwd()}")
        sys.exit(1)

def get_port():
    try:
        import yaml
        site_file = Path("_data/site.yaml")
        if site_file.exists():
            with open(site_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                url = data.get("url", "")
                if ":" in url:
                    return int(url.split(":")[-1].strip("/ "))
    except:
        pass
    return 8000

if __name__ == "__main__":
    ensure_root()
    print_banner()
    port = get_port()
    print(f"  Local URL: http://localhost:{port}/")

    print("[1] Build")
    print("[2] Dev")
    try:
        import markdown, yaml, frontmatter, jinja2
    except:
        subprocess.run([sys.executable, "install.py"])
    c = input("Choose [1/2]: ").strip()
    if c == "2":
        subprocess.run([sys.executable, "dev.py"])
    else:
        subprocess.run([sys.executable, "ssg.py"])
