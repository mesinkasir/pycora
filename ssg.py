import os
import shutil
import yaml
import markdown
from datetime import datetime
from pathlib import Path
import frontmatter
from jinja2 import Environment, FileSystemLoader
import time

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

class SimpleSSG:
    def __init__(self):
        self.start_time = time.time()
        self.config = self.load_config()
        self.setup_directories()
        self.env = Environment(loader=FileSystemLoader('templates'))
        self.posts = []
        self.tags = {}
        self.total_files = 0
        
    def load_config(self):
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    
    def setup_directories(self):
        folders = ['content/posts', 'content/pages', 'templates', 'static', 'output']
        for folder in folders:
            Path(folder).mkdir(parents=True, exist_ok=True)
    
    def read_markdown(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return frontmatter.load(f)
    
    def process_posts(self):
        posts_dir = Path('content/posts')
        for md_file in posts_dir.glob('*.md'):
            post = self.read_markdown(md_file)
            post.metadata['slug'] = md_file.stem
            post.metadata['date'] = post.metadata.get('date', datetime.now())
            
            tags = post.metadata.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]
            elif isinstance(tags, list):
                tags = tags
            else:
                tags = []
            post.metadata['tags'] = tags
            
            post.content = markdown.markdown(
                post.content,
                extensions=['fenced_code', 'tables', 'attr_list', 'toc']
            )
            self.posts.append(post)
            self.total_files += 1
            
            for tag in tags:
                tag = tag.strip()
                if tag not in self.tags:
                    self.tags[tag] = []
                self.tags[tag].append(post)
        
        self.posts.sort(key=lambda x: x.metadata['date'], reverse=True)
    
    def generate_landing(self):
        html = self.env.get_template('landing.html').render(
            site=self.config.get('site', {}),
            posts=self.posts[:6],
            tags=self.tags
        )
        Path('output/index.html').write_text(html, encoding='utf-8')
        self.total_files += 1
    
    def generate_blog(self):
        per_page = 10
        total_pages = (len(self.posts) + per_page - 1) // per_page
        
        for page_num in range(1, total_pages + 1):
            start = (page_num - 1) * per_page
            end = start + per_page
            posts_page = self.posts[start:end]
            
            html = self.env.get_template('blog.html').render(
                site=self.config.get('site', {}),
                posts=posts_page,
                tags=self.tags,
                current_page=page_num,
                total_pages=total_pages
            )
            
            if page_num == 1:
                Path('output/blog/index.html').parent.mkdir(parents=True, exist_ok=True)
                Path('output/blog/index.html').write_text(html, encoding='utf-8')
            else:
                Path(f'output/blog/page/{page_num}/index.html').parent.mkdir(parents=True, exist_ok=True)
                Path(f'output/blog/page/{page_num}/index.html').write_text(html, encoding='utf-8')
            self.total_files += 1
    
    def generate_posts(self):
        for idx, post in enumerate(self.posts):
            prev_post = self.posts[idx - 1] if idx > 0 else None
            next_post = self.posts[idx + 1] if idx < len(self.posts) - 1 else None
            
            related = []
            for p in self.posts:
                if p != post and set(p.metadata['tags']) & set(post.metadata['tags']):
                    related.append(p)
            related = related[:3]
            
            html = self.env.get_template('post.html').render(
                site=self.config.get('site', {}),
                post=post,
                content=post.content,
                prev_post=prev_post,
                next_post=next_post,
                related_posts=related
            )
            
            Path(f'output/blog/{post.metadata["slug"]}/index.html').parent.mkdir(parents=True, exist_ok=True)
            Path(f'output/blog/{post.metadata["slug"]}/index.html').write_text(html, encoding='utf-8')
            self.total_files += 1
    
    def generate_pages(self):
        pages_dir = Path('content/pages')
        for md_file in pages_dir.glob('*.md'):
            page = self.read_markdown(md_file)
            page.metadata['slug'] = md_file.stem
            page.content = markdown.markdown(
               page.content,
               extensions=['fenced_code', 'tables', 'attr_list', 'toc']
            )
            
            html = self.env.get_template('page.html').render(
                site=self.config.get('site', {}),
                page=page.metadata,
                content=page.content
            )
            
            Path(f'output/{md_file.stem}/index.html').parent.mkdir(parents=True, exist_ok=True)
            Path(f'output/{md_file.stem}/index.html').write_text(html, encoding='utf-8')
            self.total_files += 1
    
    def generate_tags(self):
        html = self.env.get_template('tags.html').render(
            site=self.config.get('site', {}),
            tags=self.tags
        )
        Path('output/tags/index.html').parent.mkdir(parents=True, exist_ok=True)
        Path('output/tags/index.html').write_text(html, encoding='utf-8')
        self.total_files += 1
        
        for tag, posts in self.tags.items():
            html = self.env.get_template('tag.html').render(
                site=self.config.get('site', {}),
                tag=tag,
                posts=posts,
                all_tags=list(self.tags.keys())
            )
            tag_folder = Path(f'output/tags/{tag}')
            tag_folder.mkdir(parents=True, exist_ok=True)
            (tag_folder / 'index.html').write_text(html, encoding='utf-8')
            self.total_files += 1
    
    def generate_rss(self):
        if not self.posts:
            return
        now = datetime.now()
        html = self.env.get_template('feed.xml').render(
            site=self.config.get('site', {}),
            posts=self.posts,
            now=now
        )
        Path('output/feed.xml').write_text(html, encoding='utf-8')
        self.total_files += 1
        print(f"{Colors.GREEN}📡 RSS feed generated{Colors.RESET}")

    def generate_sitemap(self):
        now = datetime.now()
        pages = []
        pages_dir = Path('content/pages')
        for md_file in pages_dir.glob('*.md'):
            page = self.read_markdown(md_file)
            pages.append({
                'slug': md_file.stem,
                'title': page.metadata.get('title', md_file.stem)
            })
        
        html = self.env.get_template('sitemap.xml').render(
            site=self.config.get('site', {}),
            posts=self.posts,
            pages=pages,
            tags=self.tags,
            now=now
        )
        Path('output/sitemap.xml').write_text(html, encoding='utf-8')
        self.total_files += 1
        print(f"{Colors.GREEN}🗺️  Sitemap generated{Colors.RESET}")
    
    def generate_404(self):
        """Generate 404 page"""
        html = self.env.get_template('404.html').render(
            site=self.config.get('site', {}),
            posts=self.posts[:5]
        )
        Path('output/404.html').write_text(html, encoding='utf-8')
        self.total_files += 1
        print(f"{Colors.GREEN}📄 404 page generated{Colors.RESET}")
    
    def copy_static(self):
        """Copy static files to output"""
        if Path('static').exists():
            if Path('static/css').exists():
                if Path('output/css').exists():
                    shutil.rmtree('output/css')
                shutil.copytree('static/css', 'output/css', dirs_exist_ok=True)
        if Path('static').exists():
            if Path('static/js').exists():
                if Path('output/js').exists():
                    shutil.rmtree('output/js')
                shutil.copytree('static/js', 'output/js', dirs_exist_ok=True)
            
            if Path('static/img').exists():
                if Path('output/img').exists():
                    shutil.rmtree('output/img')
                shutil.copytree('static/img', 'output/img', dirs_exist_ok=True)
            for file in Path('static').glob('*.*'):
                if file.is_file():
                     shutil.copy2(file, f'output/{file.name}')
            
            print(f"{Colors.GREEN}📁 Static files copied{Colors.RESET}")
    
    def print_banner(self):
        print(f"""
{Colors.CYAN}══════════════════════════════════════════════════════════
                                                              
  {Colors.BOLD}██████╗ ██╗   ██╗ ██████╗ ██████╗ ██████╗  █████╗ {Colors.CYAN}
  {Colors.BOLD}██╔══██╗╚██╗ ██╔╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗{Colors.CYAN}
  {Colors.BOLD}██████╔╝ ╚████╔╝ ██║     ██║   ██║██████╔╝███████║{Colors.CYAN}
  {Colors.BOLD}██╔═══╝   ╚██╔╝  ██║     ██║   ██║██╔══██╗██╔══██║{Colors.CYAN}
  {Colors.BOLD}██║        ██║   ╚██████╗╚██████╔╝██║  ██║██║  ██║{Colors.CYAN}
  {Colors.BOLD}╚═╝        ╚═╝    ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝{Colors.CYAN}
                                                             
  {Colors.GREEN}Python Static Site Generator{Colors.CYAN}    
  {Colors.YELLOW}SSG by Axcora Technology{Colors.CYAN}   
  {Colors.RED}www.axcora.com{Colors.CYAN}                       
  {Colors.DIM}Python • Markdown • YAML{Colors.CYAN}                        
══════════════════════════════════════════════════════════{Colors.RESET}
        """)
    
    def print_summary(self):
        elapsed = time.time() - self.start_time
        site_name = self.config.get('site', {}).get('name', 'PyCora')
        
        tag_list = ', '.join([f'#{tag}' for tag in self.tags.keys()]) if self.tags else 'no tags'
        
        print(f"""
{Colors.GREEN}➜ {Colors.BOLD}{site_name}{Colors.RESET} {Colors.DIM}ready in {elapsed:.3f}s{Colors.RESET}

{Colors.CYAN}  ──────────────────────────────────────────────{Colors.RESET}

  {Colors.BOLD}📄 Pages{Colors.RESET}      {Colors.DIM}→{Colors.RESET}  {self.total_files} files
  {Colors.BOLD}📝 Posts{Colors.RESET}       {Colors.DIM}→{Colors.RESET}  {len(self.posts)} posts
  {Colors.BOLD}🏷️  Tags{Colors.RESET}        {Colors.DIM}→{Colors.RESET}  {len(self.tags)} tags {Colors.DIM}({tag_list}){Colors.RESET}
  {Colors.BOLD}📁 Output{Colors.RESET}      {Colors.DIM}→{Colors.RESET}  ./output

{Colors.CYAN}  ──────────────────────────────────────────────{Colors.RESET}

{Colors.GREEN}✓{Colors.RESET}  Build complete!
{Colors.BLUE}➜{Colors.RESET}  Local:   {Colors.BOLD}http://localhost:8000{Colors.RESET}
{Colors.BLUE}➜{Colors.RESET}  Output:  {Colors.DIM}./output{Colors.RESET}

{Colors.DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}
        """)
    
    def build(self):
        self.print_banner()
        print(f"{Colors.DIM}Building...{Colors.RESET}\n")
        
        self.process_posts()
        self.generate_landing()
        self.generate_blog()
        self.generate_posts()
        self.generate_pages()
        self.generate_tags()
        self.generate_rss()
        self.generate_sitemap()
        self.generate_404()
        self.copy_static()
        
        self.print_summary()

if __name__ == "__main__":
    ssg = SimpleSSG()
    ssg.build()