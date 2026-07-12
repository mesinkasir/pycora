import subprocess
import sys
import os

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
   By Axcora Technology
   www.axcora.com
   Python • Markdown • YAML                                   
 ══════════════════════════════════════════════════════════
    """)
    
    print("📦 Installing PyCora dependencies...\n")
    
    dependencies = [
        'python-frontmatter',
        'markdown',
        'PyYAML',
        'Jinja2',
        'watchdog',
        'livereload'
    ]
    
    # Generate requirements.txt for deployment
    with open('requirements.txt', 'w') as f:
        for dep in dependencies:
            f.write(dep + '\n')
    print("✅ requirements.txt generated for deployment\n")
    
    # Install dependencies
    for dep in dependencies:
        print(f"Installing {dep}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
    
    print("""
════════════════════════════════════════════════════════
  ✅ Installation Complete!                             
                                                        
  📖 How to use:                                        
    python run.py   → Menu                              
    python ssg.py   → Build site                        
    python dev.py   → Development server                
════════════════════════════════════════════════════════
    """)

if __name__ == "__main__":
    main()