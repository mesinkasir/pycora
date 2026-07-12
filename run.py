import subprocess
import sys

def check_dependencies():
    try:
        import markdown, yaml, frontmatter, jinja2, watchdog
        return True
    except:
        return False

def main():
    print("""
 ══════════════════════════════════════════════════════════
   ██████╗ ██╗   ██╗ ██████╗ ██████╗ ██████╗  █████╗     
   ██╔══██╗╚██╗ ██╔╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗    
   ██████╔╝ ╚████╔╝ ██║     ██║   ██║██████╔╝███████║    
   ██╔═══╝   ╚██╔╝  ██║     ██║   ██║██╔══██╗██╔══██║    
   ██║        ██║   ╚██████╗╚██████╔╝██║  ██║██║  ██║    
   ╚═╝        ╚═╝    ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝    
                                                               
   PyCora - Static Site Generator                        
   Python • Markdown • YAML                                   
   By Axcora Technology
   www.axcora.com
 ══════════════════════════════════════════════════════════
    """)
    
    if not check_dependencies():
        print("⚠️  Dependencies not installed!")
        choice = input("Install now? (y/n): ").strip()
        if choice.lower() == 'y':
            subprocess.run([sys.executable, "install.py"])
        else:
            return
    
    print("\n📖 Select command:")
    print("  [1] Build site (ssg.py)")
    print("  [2] Development server (dev.py)")
    print("  [3] Install/Update dependencies")
    print("  [4] Exit")
    
    choice = input("\nChoose (1-4): ").strip()
    
    if choice == "1":
        subprocess.run([sys.executable, "ssg.py"])
    elif choice == "2":
        subprocess.run([sys.executable, "dev.py"])
    elif choice == "3":
        subprocess.run([sys.executable, "install.py"])
    else:
        print("👋 Bye!")

if __name__ == "__main__":
    main()