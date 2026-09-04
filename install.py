import sys
import io
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
except:
    pass
import subprocess

class Colors:
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

VERSION = "MEDUSA VERSION - PYCORA V2.1.0"

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
  {VERSION}
══════════════════════════════════════════════════════════{Colors.RESET}
        """)
    except:
        print(f"INSTALL - {VERSION}")

def main():
    print_banner()
    deps = ['python-frontmatter','markdown','PyYAML','Jinja2','watchdog','livereload','Pygments']
    with open('requirements.txt','w') as f:
        for d in deps:
            f.write(d+'\n')
    for dep in deps:
        subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
    print(f"Done {VERSION}")

if __name__ == "__main__":
    main()
