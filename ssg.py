
import sys
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
except:
    pass

import shutil, yaml, json, re, markdown
from datetime import datetime, date
import pathlib as _pl
Path = _pl.Path
from jinja2 import Environment, FileSystemLoader, ChainableUndefined
from jinja2.exceptions import TemplateNotFound
import time

class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n?', re.DOTALL)

def parse_frontmatter_raw(raw: str):
    meta = {}
    content = raw
    m = FRONTMATTER_RE.match(raw)
    if m:
        try:
            fm_text = m.group(1)
            meta = yaml.safe_load(fm_text) or {}
            content = raw[m.end():].lstrip('\n')
        except:
            meta = {}
    return meta, content

def load_frontmatter_file(filepath: Path):
    raw = filepath.read_text(encoding='utf-8')
    return parse_frontmatter_raw(raw)

class AttrDict(dict):
    def __getattr__(self, name):
        if name in self:
            val = self[name]
            if isinstance(val, dict) and not isinstance(val, AttrDict):
                return AttrDict(val)
            return val
        return ChainableUndefined()
    def __setattr__(self, name, value):
        self[name] = value
    def __bool__(self):
        return len(self) > 0
    def __str__(self):
        return "" if len(self) == 0 else super().__str__()
    def __repr__(self):
        return "" if len(self) == 0 else super().__repr__()
    def __call__(self, *args, **kwargs):
        return ChainableUndefined()

def ensure_root():
    if Path('templates').exists() and Path('content').exists():
        return
    if Path('../templates').exists():
        print("[ERROR] Run from project root: cd ..")
        sys.exit(1)
    if not Path('templates').exists():
        print(f"[ERROR] templates/ not found in {Path.cwd()}")
        sys.exit(1)

VERSION = "MEDUSA v2.4.6"
GENERATOR = "pycora medusa v2.4.6"
GENERATOR_META = f'<meta name="generator" content="{GENERATOR}">'

class PAXLoader(FileSystemLoader):
    def _fix_slice_in_source(self, source: str) -> str:
        if '[' not in source or ':' not in source:
            return source
        source = re.sub(r'([A-Za-z0-9_\.\|\)\]\}\']+)\s*\[\s*:\s*(\d+)\s*\]', r'\1 | limit(\2)', source)
        def repl_slice(m):
            expr = m.group(1)
            start = m.group(2).strip() if m.group(2) else ''
            end = m.group(3).strip()
            if not start:
                return f"{expr} | limit({end})"
            return f"{expr} | slice({start}, {end})"
        source = re.sub(r'([A-Za-z0-9_\.\|\)\]\}\']+)\s*\[\s*(\d*)\s*:\s*(\d+)\s*\]', repl_slice, source)
        return source
    def get_source(self, environment, template):
        t = template.strip().lstrip('/')
        def _load_and_fix(cand):
            src, filename, uptodate = super(PAXLoader, self).get_source(environment, cand)
            src = self._fix_slice_in_source(src)
            return src, filename, uptodate
        try:
            return _load_and_fix(t)
        except TemplateNotFound:
            pass
        p = Path(t)
        candidates = []
        if '.' not in p.name:
            candidates.append(t + '.pax')
            candidates.append(t + '.html')
            candidates.append(f"layouts/{t}.pax")
            candidates.append(f"layouts/{t}.html")
            candidates.append(f"{t}/index.pax")
            candidates.append(f"{t}/index.html")
        else:
            if t.endswith('.html'):
                candidates.append(t[:-5] + '.pax')
            if t.endswith('.pax'):
                candidates.append(t[:-4] + '.html')
            stem = str(p.with_suffix(''))
            candidates.append(f"{stem}.pax")
            candidates.append(f"{stem}.html")
        for cand in candidates:
            try:
                return _load_and_fix(cand)
            except:
                continue
        try:
            base_dir = Path(self.searchpath[0]) if isinstance(self.searchpath, (list, tuple)) else Path(self.searchpath)
            if base_dir.exists():
                target_name = p.name
                for found in base_dir.rglob(target_name):
                    if found.is_file():
                        rel = found.relative_to(base_dir).as_posix()
                        try:
                            return _load_and_fix(rel)
                        except:
                            continue
                if '.' not in p.name:
                    for ext in ['.pax','.html']:
                        for found in base_dir.rglob(p.name + ext):
                            if found.is_file():
                                rel = found.relative_to(base_dir).as_posix()
                                try:
                                    return _load_and_fix(rel)
                                except:
                                    continue
        except:
            pass
        raise TemplateNotFound(template)

class CollectionList(list):
    def __init__(self, items=None, subs=None):
        super().__init__(items or [])
        self._subs = dict(subs) if subs else {}
    def __getattr__(self, name):
        if name in self._subs:
            return self._subs[name]
        for k, v in self._subs.items():
            leaf = k.split('/')[-1]
            if k == name or leaf == name or k.replace('-','_') == name or leaf.replace('-','_') == name or k.replace('/','_') == name:
                return v
        return CollectionList([])
    def __getitem__(self, key):
        if isinstance(key, slice):
            return CollectionList(super().__getitem__(key), subs=self._subs)
        if isinstance(key, str):
            if key in self._subs:
                return self._subs[key]
            for k, v in self._subs.items():
                leaf = k.split('/')[-1]
                if k == key or leaf == key or k.replace('-','_') == key or leaf.replace('-','_') == key:
                    return v
        return super().__getitem__(key)

class SimpleSSG:
    def __init__(self):
        ensure_root()
        self.start_time = time.time()
        self.config = self.load_config()
        self.setup_directories()
        self.env = Environment(loader=PAXLoader('templates'), undefined=ChainableUndefined)
        self.env.globals.update(self.config)
        self.env.globals.update(self.config.get('site', {}))
        self.env.globals['generator'] = GENERATOR
        self.env.globals['generator_meta'] = GENERATOR_META
        self.env.filters["slugify"] = lambda t: re.sub(r"[^a-z0-9]+","-",str(t).lower()).strip("-")
        def _parse_num(n):
            try:
                if isinstance(n, slice):
                    return n.stop if n.stop is not None else 0
                s = str(n)
                if ':' in s:
                    s = s.split(':')[-1]
                s = s.strip('() []{}').strip()
                return int(float(s)) if s else 0
            except:
                try:
                    if isinstance(n, slice):
                        return n.stop or 0
                    return int(n)
                except:
                    return 0
        def _limit_filter(seq, n=0):
            num = _parse_num(n)
            if not seq:
                return CollectionList([])
            subs = getattr(seq, '_subs', {}) if isinstance(seq, CollectionList) else {}
            sliced = list(seq)[:num] if num>0 else list(seq)
            return CollectionList(sliced, subs=subs)
        def _slice_filter(seq, n=0, *args):
            if not seq:
                return CollectionList([])
            subs = getattr(seq, '_subs', {}) if isinstance(seq, CollectionList) else {}
            try:
                if isinstance(n, slice):
                    return CollectionList(list(seq)[n], subs=subs)
                if len(args)==0:
                    num = _parse_num(n)
                    sliced = list(seq)[:num] if num>0 else list(seq)
                elif len(args)==1:
                    if isinstance(args[0], slice):
                        return CollectionList(list(seq)[args[0]], subs=subs)
                    start = _parse_num(n)
                    end = _parse_num(args[0])
                    sliced = list(seq)[start:end]
                else:
                    start = _parse_num(n)
                    end = _parse_num(args[0])
                    step = _parse_num(args[1]) if args[1] else 1
                    sliced = list(seq)[start:end:step]
            except:
                try:
                    if isinstance(n, slice):
                        sliced = list(seq)[n]
                    else:
                        sliced = list(seq)[:_parse_num(n)]
                except:
                    sliced = list(seq)
            return CollectionList(sliced, subs=subs)
        def _where_exp_filter(seq, key=None, value=None):
            if not seq:
                return CollectionList([])
            subs = getattr(seq, '_subs', {}) if isinstance(seq, CollectionList) else {}
            if key is None:
                return CollectionList(list(seq), subs=subs)
            out = []
            for item in seq:
                meta = item.metadata if hasattr(item,'metadata') else item
                v = meta.get(key) if isinstance(meta, dict) else getattr(meta, key, None)
                if isinstance(v, list):
                    if value is None:
                        if v:
                            out.append(item)
                    else:
                        if str(value).lower() in [str(x).lower() for x in v] or str(value) in map(str,v) or value in v:
                            out.append(item)
                else:
                    if value is None:
                        if v:
                            out.append(item)
                    else:
                        if isinstance(v, bool) or isinstance(value, bool):
                            if bool(v) == bool(value) or str(v).lower() == str(value).lower():
                                out.append(item)
                        else:
                            if str(v).lower() == str(value).lower() or v == value:
                                out.append(item)
            return CollectionList(out, subs=subs)
        def _filter_tag_filter(seq, tag_name):
            if not seq:
                return CollectionList([])
            tag_name = str(tag_name).strip(':"\'').lower()
            out = []
            for item in seq:
                meta = item.metadata if hasattr(item,'metadata') else {}
                tags = meta.get('tags', []) if isinstance(meta, dict) else getattr(meta, 'tags', [])
                if isinstance(tags, str):
                    tags = [tags]
                if tag_name in [str(t).lower() for t in tags]:
                    out.append(item)
            return CollectionList(out, subs=getattr(seq, '_subs', {}) if isinstance(seq, CollectionList) else {})
        def _sort_filter(seq, attr='date', reverse=False):
            if not seq:
                return CollectionList([])
            subs = getattr(seq, '_subs', {}) if isinstance(seq, CollectionList) else {}
            def _key(x):
                m = x.metadata if hasattr(x,'metadata') else {}
                v = m.get(attr) if isinstance(m, dict) else getattr(m, attr, '')
                return str(v).lower() if isinstance(v, str) else v or ''
            try:
                sorted_list = sorted(list(seq), key=_key, reverse=bool(reverse))
            except:
                sorted_list = list(seq)
            return CollectionList(sorted_list, subs=subs)
        self.env.filters["limit"] = _limit_filter
        self.env.filters["slice"] = _slice_filter
        self.env.filters["where"] = _where_exp_filter
        self.env.filters["filter_by"] = _where_exp_filter
        self.env.filters["filter_tag"] = _filter_tag_filter
        self.env.filters["where_tag"] = _filter_tag_filter
        self.env.filters["by_tag"] = _filter_tag_filter
        self.env.filters["tag"] = _filter_tag_filter
        self.env.filters["sort_by"] = _sort_filter
        self.env.filters["sort"] = _sort_filter
        self.env.filters["reverse"] = lambda seq: CollectionList(list(reversed(list(seq))), subs=getattr(seq, '_subs', {})) if seq else CollectionList([])
        self.env.filters["first"] = lambda seq: seq[0] if seq else None
        self.env.filters["last"] = lambda seq: seq[-1] if seq else None
        self.collections = {}
        self.controllers = {}
        self.all_items = []
        self.tags = {}
        self.total_files = 0

    def render_string_safe(self, text: str, ctx: dict, max_depth=5):
        if not isinstance(text, str):
            return text
        if '{{' not in text and '{%' not in text:
            return text
        current = text
        for _ in range(max_depth):
            if '{{' not in current and '{%' not in current:
                break
            try:
                tpl = self.env.from_string(current)
                rendered = tpl.render(**ctx)
                if rendered == current:
                    break
                current = rendered
            except:
                break
        return current

    def render_meta_templates(self, meta: dict, ctx: dict):
        if not isinstance(meta, dict):
            return meta
        for k, v in list(meta.items()):
            if isinstance(v, str):
                meta[k] = self.render_string_safe(v, ctx)
            elif isinstance(v, dict):
                self.render_meta_templates(v, ctx)
            elif isinstance(v, list):
                new_list = []
                for item in v:
                    if isinstance(item, str):
                        new_list.append(self.render_string_safe(item, ctx))
                    elif isinstance(item, dict):
                        self.render_meta_templates(item, ctx)
                        new_list.append(item)
                    else:
                        new_list.append(item)
                meta[k] = new_list
        return meta

    def load_data_file(self, filepath: Path):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if filepath.suffix in ['.yaml','.yml']:
                    return yaml.safe_load(f) or {}
                if filepath.suffix == '.json':
                    return json.load(f)
        except:
            return {}
        return {}

    def deep_merge(self, base, new):
        for k, v in new.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self.deep_merge(base[k], v)
            else:
                base[k] = v
        return base

    def load_config(self):
        config = {}
        data_dir = Path("_data")
        if data_dir.exists():
            for file in data_dir.rglob("*.*"):
                if file.suffix not in ['.yaml','.yml','.json']:
                    continue
                if file.name.startswith('.'):
                    continue
                rel = file.relative_to(data_dir).with_suffix("")
                parts = rel.parts
                content = self.load_data_file(file)
                if not content:
                    continue
                cur = config
                for p in parts[:-1]:
                    cur = cur.setdefault(p, {})
                cur[parts[-1]] = content
                if parts[0] != 'site':
                    site_cur = config.setdefault('site', {})
                    s_cur = site_cur
                    for p in parts[:-1]:
                        s_cur = s_cur.setdefault(p, {})
                    if parts[-1] not in s_cur:
                        s_cur[parts[-1]] = content
        if Path("config.yaml").exists():
            with open('config.yaml', 'r', encoding='utf-8') as f:
                legacy = yaml.safe_load(f) or {}
                if 'site' in legacy:
                    config.setdefault('site', {})
                    self.deep_merge(config['site'], legacy['site'])
                    for k, v in legacy.items():
                        if k != 'site' and k not in config:
                            config[k] = v
                else:
                    if 'site' not in config:
                        config['site'] = legacy
                    else:
                        self.deep_merge(config['site'], legacy)
        config.setdefault('site', {})
        config['site']['generator'] = GENERATOR
        config['generator'] = GENERATOR
        return config

    def setup_directories(self):
        for folder in ['content','templates','templates/layouts','templates/partials','static','output','_data']:
            Path(folder).mkdir(parents=True, exist_ok=True)

    def find_template_file(self, name: str):
        base_dir = Path('templates')
        name = name.strip().lstrip('/')
        candidates = []
        candidates.append(base_dir / name)
        if '.' not in Path(name).name:
            candidates.append(base_dir / f"{name}.pax")
            candidates.append(base_dir / f"{name}.html")
            candidates.append(base_dir / f"layouts/{name}.pax")
            candidates.append(base_dir / f"layouts/{name}.html")
        else:
            stem = str(Path(name).with_suffix(''))
            candidates.append(base_dir / f"{stem}.pax")
            candidates.append(base_dir / f"{stem}.html")
        for cand in candidates:
            if cand.exists() and cand.is_file():
                return cand
        for cand in candidates:
            basename = Path(cand).name
            for found in base_dir.rglob(basename):
                if found.is_file():
                    return found
        return None

    def parse_template_frontmatter(self, file_path: Path):
        try:
            raw = file_path.read_text(encoding='utf-8')
        except:
            return {}, ""
        return parse_frontmatter_raw(raw)

    def _to_attrdict(self, obj):
        if isinstance(obj, dict):
            ad = AttrDict()
            for k, v in obj.items():
                ad[k] = self._to_attrdict(v)
            return ad
        elif isinstance(obj, list):
            return [self._to_attrdict(x) for x in obj]
        else:
            return obj

    def build_context(self, extra=None):
        ctx = {}
        ctx['collections'] = self.collections
        ctx['tags'] = self.tags
        ctx['site'] = self.config.get('site', {})
        ctx['config'] = self.config
        ctx['generator'] = GENERATOR
        ctx['generator_meta'] = GENERATOR_META
        ctx['version'] = VERSION
        ctx['posts'] = self.collections.get('posts', CollectionList([]))
        protected = set(self.config.keys()) | set(self.config.get('site', {}).keys())
        protected.update(['collections','tags','site','config','posts','all_items','generator','generator_meta','version','content','page','post','prev_post','next_post','related_posts','collection_name','pagination','toc','all_tags','tag','prev','next'])
        for col_name, col_items in self.collections.items():
            safe_name = col_name.replace('/', '_').replace('-', '_')
            if col_name not in protected and col_name not in ctx:
                ctx[col_name] = col_items
            if safe_name not in protected and safe_name not in ctx:
                ctx[safe_name] = col_items
            leaf = col_name.split('/')[-1]
            if leaf not in protected and leaf not in ctx:
                ctx[leaf] = col_items
            safe_leaf = leaf.replace('-','_')
            if safe_leaf not in protected and safe_leaf not in ctx:
                ctx[safe_leaf] = col_items
        for col in self.collections.values():
            if isinstance(col, CollectionList):
                for sub_name, sub_items in col._subs.items():
                    leaf = sub_name.split('/')[-1]
                    if leaf not in protected and leaf not in ctx:
                        ctx[leaf] = sub_items
                    if sub_name not in protected and sub_name not in ctx:
                        ctx[sub_name] = sub_items
                    safe_leaf = leaf.replace('-','_')
                    if safe_leaf not in protected and safe_leaf not in ctx:
                        ctx[safe_leaf] = sub_items
        for k, v in self.config.items():
            if isinstance(v, dict):
                ctx[k] = self._to_attrdict(v)
            else:
                if k not in ctx or k in protected:
                    ctx[k] = v
        for k, v in self.config.get('site', {}).items():
            if k not in protected and k not in ctx:
                ctx[k] = self._to_attrdict(v) if isinstance(v, dict) else v
        ctx['all_items'] = self.all_items
        RESERVED = {'collections','tags','site','config','posts','all_items','generator','generator_meta','version','content','page','post','prev_post','next_post','related_posts','collection_name','pagination','toc','all_tags','tag','prev','next'}
        if extra:
            ctx.update(extra)
            page_data = extra.get('page')
            if isinstance(page_data, dict):
                for k, v in page_data.items():
                    if k.startswith('_'):
                        continue
                    if k in RESERVED:
                        continue
                    ctx[k] = self._to_attrdict(v) if isinstance(v, dict) else v
            post_obj = extra.get('post')
            if post_obj and hasattr(post_obj, 'metadata'):
                for k, v in post_obj.metadata.items():
                    if k.startswith('_'):
                        continue
                    if k in RESERVED:
                        continue
                    if k not in ctx or k not in (page_data or {}):
                        ctx[k] = self._to_attrdict(v) if isinstance(v, dict) else v
        return ctx

    def render_template(self, template_name, _chain=None, /, **ctx):
        if 'collections' not in ctx:
            ctx['collections'] = self.collections
        if 'posts' not in ctx and 'posts' in self.collections:
            ctx['posts'] = self.collections['posts']
        if 'tags' not in ctx:
            ctx['tags'] = self.tags
        ctx.setdefault('hero', AttrDict())
        ctx.setdefault('section1', AttrDict())
        ctx.setdefault('section2', AttrDict())
        ctx.setdefault('total_pages', 1)
        ctx.setdefault('current_page', 1)
        if 'pagination' not in ctx:
            ctx['pagination'] = {'items': ctx.get('posts', []), 'current_page': 1, 'total_pages': 1, 'total_items': len(ctx.get('posts', [])), 'prev_url': None, 'next_url': None, 'first_url': '/', 'last_url': '/'}
        if _chain is None:
            _chain = []
        if template_name in _chain:
            raise RuntimeError(f"Circular layout: {' -> '.join(_chain + [template_name])}")
        _chain.append(template_name)
        tpl_file = self.find_template_file(template_name)
        if not tpl_file:
            try:
                tpl = self.env.get_template(template_name if '.' in template_name else f"{template_name}.html")
                return self.inject_generator(tpl.render(**ctx))
            except:
                try:
                    tpl = self.env.get_template(f"{template_name}.pax")
                    return self.inject_generator(tpl.render(**ctx))
                except Exception as e:
                    raise FileNotFoundError(f"Template not found: {template_name} - {e}")
        fm, body = self.parse_template_frontmatter(tpl_file)
        if fm:
            tmp_ctx = {**ctx, 'site': self.config.get('site', {}), 'config': self.config}
            self.render_meta_templates(fm, tmp_ctx)
        if '{% extends' in body:
            try:
                tpl = self.env.get_template(str(tpl_file.relative_to('templates')))
                return self.inject_generator(tpl.render(**ctx))
            except:
                pass
        try:
            inner_tpl = self.env.from_string(body)
            inner_html = inner_tpl.render(**ctx)
        except:
            inner_tpl = self.env.from_string(body)
            inner_html = inner_tpl.render(**ctx)
        layout_name = fm.get('layout')
        if layout_name:
            ctx['content'] = inner_html
            page_ctx = ctx.get('page', {})
            if isinstance(page_ctx, dict):
                merged = {**page_ctx, **fm}
                if 'url' in page_ctx:
                    merged['url'] = page_ctx['url']
                if 'permalink' in page_ctx:
                    merged['permalink'] = page_ctx['permalink']
                ctx['page'] = merged
            else:
                ctx['page'] = fm
            return self.render_template(layout_name, _chain, **ctx)
        else:
            return self.inject_generator(inner_html)

    def get_template(self, name, /):
        class Wrapper:
            def __init__(self, parent, name):
                self.parent = parent
                self.name = name
            def render(self, **ctx):
                return self.parent.render_template(self.name, **ctx)
        return Wrapper(self, name)

    def get_markdown_parser(self):
        return markdown.Markdown(
            extensions=['fenced_code','tables','attr_list','toc','footnotes','admonition','def_list','abbr','codehilite','sane_lists','smarty','meta'],
            extension_configs={'toc': {'toc_depth': '1-6', 'permalink': False}, 'codehilite': {'guess_lang': False, 'use_pygments': True}}
        )

    def read_markdown(self, filepath):
        meta, raw_content = load_frontmatter_file(filepath)
        base_ctx_for_fm = {'site': self.config.get('site', {}), 'config': self.config}
        self.render_meta_templates(meta, base_ctx_for_fm)
        toc_flag = meta.get('toc', False)
        toc_enabled = toc_flag is True or (isinstance(toc_flag, str) and toc_flag.lower() in ('true','1','yes')) or toc_flag == 1
        md_ctx = {'site': self.config.get('site', {}), 'config': self.config, 'page': meta, 'collections': self.collections, 'tags': self.tags}
        md_ctx.update(meta)
        raw_content_rendered = self.render_string_safe(raw_content, md_ctx, max_depth=5)
        md = self.get_markdown_parser()
        html = md.convert(raw_content_rendered)
        meta['toc'] = getattr(md, 'toc', '') if toc_enabled and '<li' in getattr(md, 'toc', '') else ''
        meta['word_count'] = len(re.findall(r'\w+', raw_content))
        meta['reading_time'] = max(1, round(meta['word_count'] / 200))
        if 'date' in meta and isinstance(meta['date'], str):
            try:
                meta['date'] = datetime.fromisoformat(meta['date'])
            except:
                try:
                    meta['date'] = datetime.strptime(meta['date'], "%Y-%m-%d")
                except:
                    pass
        def _to_attr(v):
            if isinstance(v, dict):
                ad = AttrDict()
                for kk, vv in v.items():
                    ad[kk] = _to_attr(vv)
                return ad
            elif isinstance(v, list):
                return [_to_attr(x) for x in v]
            return v
        attr_meta = AttrDict()
        for k, v in (meta or {}).items():
            attr_meta[k] = _to_attr(v)
        class PostObj:
            def __init__(self, metadata, content_html, raw_md):
                object.__setattr__(self, 'metadata', metadata)
                object.__setattr__(self, 'content', content_html)
                object.__setattr__(self, 'raw_content', raw_md)
                object.__setattr__(self, 'toc', metadata.get('toc',''))
                image_aliases = ['image', 'images', 'cover', 'thumbnail', 'featured_image', 'featured', 'photo', 'picture', 'banner', 'hero', 'img']
                found_image = None
                for alias in image_aliases:
                    if alias in metadata and metadata[alias]:
                        val = metadata[alias]
                        if isinstance(val, list) and len(val) > 0:
                            val = val[0]
                        if val:
                            found_image = val
                            break
                if found_image:
                    if 'image' not in metadata:
                        metadata['image'] = found_image
                for kk, vv in metadata.items():
                    if not kk.startswith('_'):
                        try:
                            object.__setattr__(self, kk, vv)
                        except:
                            pass
            def __getattr__(self, name):
                md = object.__getattribute__(self, 'metadata')
                if name in md:
                    return md[name]
                return AttrDict()
            def __getitem__(self, key):
                md = object.__getattribute__(self, 'metadata')
                if key in md:
                    return md[key]
                try:
                    return object.__getattribute__(self, key)
                except AttributeError:
                    raise KeyError(key)
            def __contains__(self, key):
                md = object.__getattribute__(self, 'metadata')
                return key in md
        obj = PostObj(attr_meta, html, raw_content_rendered)
        obj.metadata['_file_path'] = str(filepath)
        return obj

    def scan_content(self):
        content_root = Path('content')
        if not content_root.exists():
            return
        all_md = list(content_root.rglob('*.md'))
        controllers_raw = []
        for md_file in all_md:
            item = self.read_markdown(md_file)
            if 'collection' in item.metadata and md_file.parent == content_root:
                controllers_raw.append(md_file)
            elif 'collection' in item.metadata and md_file.name == f"{item.metadata['collection']}.md":
                controllers_raw.append(md_file)
        for md_file in content_root.glob('*.md'):
            item = self.read_markdown(md_file)
            if 'collection' in item.metadata:
                if md_file not in controllers_raw:
                    controllers_raw.append(md_file)
        for md_file in controllers_raw:
            ctrl = self.read_markdown(md_file)
            col_name = ctrl.metadata['collection']
            output_name = md_file.stem
            self.controllers[output_name] = {'file': md_file, 'collection': col_name, 'output_name': output_name, 'metadata': ctrl.metadata, 'content': ctrl.content, 'obj': ctrl}
        for md_file in all_md:
            if md_file in controllers_raw:
                continue
            item = self.read_markdown(md_file)
            rel_to_root = md_file.relative_to(content_root)
            rel_slug = rel_to_root.with_suffix('').as_posix()
            if rel_slug == 'index':
                rel_slug = ''
            parts = rel_to_root.parts
            user_slug = item.metadata.get('slug', None)
            if user_slug:
                bare = str(user_slug).strip('/').split('/')[-1]
            else:
                bare = Path(rel_slug).name
            item.metadata['slug'] = rel_slug
            item.metadata['bare_slug'] = bare
            item.metadata['_rel_path'] = rel_slug
            item.metadata['_file'] = str(md_file)
            item.metadata['url'] = f"/{rel_slug}/"
            item.metadata['permalink'] = f"/{rel_slug}/"
            item.metadata['link'] = f"/{rel_slug}/"
            item.metadata['href'] = f"/{rel_slug}/"
            try:
                setattr(item, 'slug', rel_slug)
                setattr(item, 'bare_slug', bare)
                setattr(item, '_rel_path', rel_slug)
                setattr(item, 'url', f"/{rel_slug}/")
                setattr(item, 'permalink', f"/{rel_slug}/")
                setattr(item, 'link', f"/{rel_slug}/")
                setattr(item, 'href', f"/{rel_slug}/")
            except:
                pass
            if len(parts) > 1:
                top = parts[0]
                if top not in self.collections:
                    self.collections[top] = CollectionList([])
                if item not in self.collections[top]:
                    self.collections[top].append(item)
                for depth in range(2, len(parts)+1):
                    if depth <= len(parts):
                        col_path = '/'.join(parts[:depth-1])
                        if col_path == top:
                            continue
                        if col_path not in self.collections:
                            self.collections[col_path] = CollectionList([])
                        if '/'.join(parts[:-1]) == col_path or '/'.join(parts[:-1]).startswith(col_path + '/'):
                            if item not in self.collections[col_path]:
                                self.collections[col_path].append(item)
                        if col_path == '/'.join(parts[:-1]):
                            if item not in self.collections[col_path]:
                                self.collections[col_path].append(item)
                cur = self.collections[top]
                for i in range(1, len(parts)-1):
                    sub = parts[i]
                    full = '/'.join(parts[:i+1])
                    if full not in self.collections:
                        self.collections[full] = CollectionList([])
                    if sub not in cur._subs:
                        cur._subs[sub] = self.collections[full]
                    cur._subs[sub.replace('-','_')] = self.collections[full]
                    cur._subs[full] = self.collections[full]
                    cur._subs[full.replace('/', '_')] = self.collections[full]
                    cur = self.collections[full]
                    root = self.collections[top]
                    leaf = parts[i]
                    if leaf not in root._subs:
                        if i == 1:
                            root._subs[leaf] = self.collections['/'.join(parts[:2])]
                            root._subs[leaf.replace('-','_')] = self.collections['/'.join(parts[:2])]
            def _norm_tags(v):
                if v is None:
                    return []
                if isinstance(v, str):
                    if ',' in v:
                        return [x.strip() for x in v.split(',') if x.strip()]
                    return [v.strip()] if v.strip() else []
                if isinstance(v, (list, tuple)):
                    out=[]
                    for x in v:
                        if isinstance(x, str) and x.strip():
                            out.append(x.strip())
                    return out
                return []
            tags_raw = item.metadata.get('tags', [])
            tags_clean = _norm_tags(tags_raw)
            seen=set()
            uniq=[]
            for t in tags_clean:
                tl=t.lower()
                if tl not in seen:
                    seen.add(tl)
                    uniq.append(t)
            item.metadata['tags'] = uniq
            try:
                setattr(item, 'tags', uniq)
            except:
                pass
            for tag in uniq:
                if tag not in self.tags:
                    self.tags[tag] = []
                self.tags[tag].append(item)
            self.all_items.append(item)
        def _get_date(item):
            d = item.metadata.get('date')
            if d is None:
                return datetime.min
            if isinstance(d, datetime):
                return d
            try:
                if isinstance(d, date):
                    return datetime.combine(d, datetime.min.time())
            except:
                pass
            if isinstance(d, str):
                try:
                    return datetime.fromisoformat(d)
                except:
                    try:
                        return datetime.strptime(d, "%Y-%m-%d")
                    except:
                        return datetime.min
            return datetime.min
        for col_name in self.collections:
            try:
                self.collections[col_name].sort(key=lambda x: _get_date(x), reverse=True)
            except:
                pass
        try:
            self.all_items.sort(key=lambda x: _get_date(x), reverse=True)
        except:
            pass

    def apply_filters(self, items, controller_meta):
        filtered = list(items)
        filter_by = controller_meta.get('filter_by')
        filter_value = controller_meta.get('filter_value')
        if filter_by and filter_value is not None:
            filtered = [it for it in filtered if str(it.metadata.get(filter_by, '')) == str(filter_value) or (isinstance(it.metadata.get(filter_by), list) and filter_value in it.metadata.get(filter_by))]
        filter_tag = controller_meta.get('filter_tag')
        if filter_tag:
            filtered = [it for it in filtered if filter_tag in it.metadata.get('tags', [])]
        filter_dict = controller_meta.get('filter')
        if isinstance(filter_dict, dict):
            for k, v in filter_dict.items():
                if k in ('tag','tags'):
                    filtered = [it for it in filtered if v in it.metadata.get('tags', [])]
                else:
                    filtered = [it for it in filtered if it.metadata.get(k) == v]
        elif isinstance(filter_dict, str):
            filtered = [it for it in filtered if it.metadata.get(filter_dict)]
        where = controller_meta.get('where')
        if where and isinstance(where, str):
            try:
                for it in list(filtered):
                    conditions = [c.strip() for c in where.split(' and ')]
                    ok = True
                    for cond in conditions:
                        if '==' in cond:
                            k, v = [x.strip().strip('"').strip("'") for x in cond.split('==',1)]
                            if v.lower() == 'true':
                                v = True
                            elif v.lower() == 'false':
                                v = False
                            if str(it.metadata.get(k)) != str(v) and it.metadata.get(k) != v:
                                if not (it.metadata.get(k) is True and v is True):
                                    ok = False
                        elif '!=' in cond:
                            k, v = [x.strip().strip('"').strip("'") for x in cond.split('!=',1)]
                            if str(it.metadata.get(k)) == str(v):
                                ok = False
                    if not ok:
                        filtered.remove(it)
            except:
                pass
        sort_by = controller_meta.get('sort_by', 'date')
        sort_order = controller_meta.get('sort_order', 'desc')
        valid_orders = ['asc', 'desc']
        valid_fields = ['date', 'title', 'author', 'category', 'featured', 'slug']
        if sort_order and sort_order.lower() not in valid_orders:
            if sort_order.lower() in valid_fields or sort_by.lower() in valid_orders:
                if sort_by.lower() in valid_orders:
                    sort_by, sort_order = sort_order, sort_by
                elif sort_order.lower() in valid_fields:
                    if sort_by.lower() in valid_fields and sort_order.lower() == 'date':
                        sort_by = 'date'
                        sort_order = 'desc'
        sort_order = sort_order.lower() if isinstance(sort_order, str) else 'desc'
        if sort_order not in valid_orders:
            sort_order = 'desc'
        reverse = sort_order != 'asc'
        def _sort_key(x):
            v = x.metadata.get(sort_by, '')
            if sort_by == 'date':
                if isinstance(v, datetime):
                    return v
                try:
                    if isinstance(v, date):
                        return datetime.combine(v, datetime.min.time())
                except:
                    pass
                if isinstance(v, str):
                    try:
                        return datetime.fromisoformat(v)
                    except:
                        return datetime.min
                if v is None or v == '':
                    return datetime.min
            return str(v).lower() if isinstance(v, str) else v
        try:
            filtered.sort(key=lambda x: _sort_key(x), reverse=reverse)
        except:
            pass
        limit = controller_meta.get('limit')
        if limit:
            try:
                filtered = filtered[:int(limit)]
            except:
                pass
        subs = getattr(items, '_subs', {}) if isinstance(items, CollectionList) else {}
        return CollectionList(filtered, subs=subs)

    def inject_generator(self, html: str) -> str:
        if not html or 'name="generator"' in html.lower():
            return html
        if '<head>' in html:
            return html.replace('<head>', f'<head>\n  {GENERATOR_META}', 1)
        return html

    def write_output(self, dest_path, html_content):
        html_content = self.inject_generator(html_content)
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        Path(dest_path).write_text(html_content, encoding='utf-8')
        self.total_files += 1

    def generate_pax_pages(self):
        base_dir = Path('templates')
        if not base_dir.exists():
            return
        files = []
        files.extend(base_dir.rglob('*.pax'))
        files.extend(base_dir.rglob('*.html'))
        for f in files:
            rel = f.relative_to(base_dir).as_posix()
            if rel.startswith('partials/') or rel.startswith('layouts/'):
                continue
            try:
                raw = f.read_text(encoding='utf-8')
            except:
                continue
            if not raw.startswith('---'):
                continue
            fm, body = self.parse_template_frontmatter(f)
            if not fm:
                continue
            generic_layout_names = ('base','default','page','post','posts','blog','landing','list','archive','main','master','layout')
            if f.stem in generic_layout_names and '/' in rel:
                if 'permalink' not in fm and 'url' not in fm:
                    continue
            if 'layout' not in fm and f.stem in ('default','base','main','layout','master'):
                if 'permalink' not in fm and 'url' not in fm:
                    continue
            permalink = fm.get('permalink') or fm.get('url')
            if permalink:
                pstr = str(permalink).strip()
                if pstr.startswith('/'):
                    pstr = pstr[1:]
                if pstr.endswith('/'):
                    out_path = Path('output') / pstr / 'index.html'
                elif pstr.endswith('.html'):
                    out_path = Path('output') / pstr
                else:
                    out_path = Path('output') / pstr / 'index.html'
            else:
                rel_no_ext = f.relative_to(base_dir).with_suffix('')
                if rel_no_ext.name == 'index':
                    out_path = Path('output') / rel_no_ext.parent / 'index.html'
                else:
                    out_path = Path('output') / rel_no_ext / 'index.html'
            url_path = '/' + out_path.parent.relative_to('output').as_posix() + '/'
            url_path = url_path.replace('//','/').replace('/./','/')
            if url_path == '//' or url_path == '/.':
                url_path = '/'
            page_meta = dict(fm)
            page_meta.setdefault('url', url_path)
            page_meta.setdefault('permalink', url_path)
            page_meta.setdefault('slug', out_path.parent.relative_to('output').as_posix())
            default_pag = {'items': self.collections.get('posts', []), 'current_page': 1, 'total_pages': 1, 'total_items': len(self.collections.get('posts', [])), 'prev_url': None, 'next_url': None, 'first_url': url_path, 'last_url': url_path}
            ctx = self.build_context({
                'site': self.config.get('site', {}),
                'page': page_meta,
                'content': body,
                'url': url_path,
                'permalink': url_path,
                'pagination': default_pag,
                'total_pages': 1,
                'current_page': 1,
                'hero': AttrDict(),
                'section1': AttrDict(),
                'section2': AttrDict(),
            })
            try:
                inner_tpl = self.env.from_string(body)
                inner_html = inner_tpl.render(**ctx)
                layout = fm.get('layout')
                if layout:
                    ctx['content'] = inner_html
                    ctx['page'] = {**page_meta, **fm}
                    ctx['page']['url'] = url_path
                    ctx['page']['permalink'] = url_path
                    html = self.render_template(layout, **ctx)
                else:
                    html = inner_html
                self.write_output(str(out_path), html)
            except:
                pass

    def generate_landing(self):
        index_path = Path('content/index.md')
        if index_path.exists():
            page = self.read_markdown(index_path)
            if 'url' not in page.metadata:
                page.metadata['url'] = '/'
                page.metadata['permalink'] = '/'
                page.metadata['slug'] = ''
            layout = page.metadata.get('layout', 'home')
            ctx = self.build_context({
                'site': self.config.get('site', {}),
                'page': page.metadata,
                'content': page.content,
                'url': page.metadata.get('url', '/'),
                'permalink': page.metadata.get('permalink', '/')
            })
            try:
                html = self.render_template(layout, **ctx)
            except:
                html = self.render_template('landing', **ctx)
            self.write_output('output/index.html', html)
        else:
            try:
                page_home = {'url': '/', 'permalink': '/', 'slug': '', 'title': 'Home'}
                ctx = self.build_context({'site': self.config.get('site', {}), 'content': '', 'page': page_home, 'url': '/', 'permalink': '/'})
                html = self.render_template('landing', **ctx)
                self.write_output('output/index.html', html)
            except:
                pass

    def generate_controllers(self):
        for output_name, ctrl in self.controllers.items():
            collection_name = ctrl.get('collection', output_name)
            collection_path = collection_name.replace('.', '/').replace('_', '/')
            base_items = self.collections.get(collection_name, CollectionList([]))
            if not base_items:
                base_items = self.collections.get(collection_path, CollectionList([]))
            if not base_items and '.' in collection_name:
                leaf = collection_name.split('.')[-1]
                top = collection_name.split('.')[0].split('/')[0]
                if top in self.collections:
                    try:
                        base_items = getattr(self.collections[top], leaf)
                    except:
                        pass
            if not base_items:
                for k, v in self.collections.items():
                    if k.endswith('/' + collection_path.split('/')[-1]) or k == collection_path:
                        base_items = v
                        break
            aggregated = []
            seen = set()
            for it in base_items:
                f = it.metadata.get('_file')
                if f not in seen:
                    seen.add(f)
                    aggregated.append(it)
            sub_keys = [k for k in self.collections.keys() if k.startswith(collection_name + '/') or k.startswith(collection_path + '/')]
            for col_key in sub_keys:
                for it in self.collections[col_key]:
                    f = it.metadata.get('_file')
                    if f not in seen:
                        seen.add(f)
                        aggregated.append(it)
            subs = getattr(base_items, '_subs', {}) if isinstance(base_items, CollectionList) else {}
            if not subs:
                for col_key in sub_keys:
                    leaf = col_key.split('/')[-1]
                    subs[leaf] = self.collections[col_key]
                    subs[leaf.replace('-','_')] = self.collections[col_key]
            items = CollectionList(aggregated, subs=subs)
            meta = ctrl['metadata']
            items = self.apply_filters(items, meta)
            layout = meta.get('layout', f"{output_name}-list")
            pagination_val = meta.get('pagination', None)
            if 'url' not in meta:
                meta['url'] = f"/{output_name}/"
                meta['permalink'] = f"/{output_name}/"
                meta['slug'] = output_name
            if pagination_val is None or pagination_val == False or str(pagination_val).lower() == 'false':
                pagination = {'items': items, 'current_page': 1, 'total_pages': 1, 'total_items': len(items), 'prev_url': None, 'next_url': None, 'first_url': f"/{output_name}/", 'last_url': f"/{output_name}/"}
                ctx = self.build_context({
                    'site': self.config.get('site', {}),
                    'page': meta,
                    'content': ctrl['content'],
                    'collection_name': output_name,
                    'collection': collection_name,
                    'pagination': pagination,
                    'items': items,
                    'posts': items,
                    'tags': self.tags,
                    'total_pages': 1,
                    'current_page': 1,
                    'url': meta.get('url', f"/{output_name}/"),
                    'permalink': meta.get('permalink', f"/{output_name}/")
                })
                try:
                    html = self.render_template(layout, **ctx)
                except:
                    try:
                        html = self.render_template('blog', **ctx)
                    except:
                        html = self.render_template(f"{output_name}", **ctx)
                self.write_output(f'output/{output_name}/index.html', html)
            else:
                try:
                    per_page = int(pagination_val)
                except:
                    per_page = 10
                total_items = len(items)
                total_pages = max(1, (total_items + per_page - 1) // per_page)
                for page_num in range(1, total_pages + 1):
                    chunk = items[(page_num-1)*per_page : page_num*per_page]
                    chunk = CollectionList(chunk, subs=getattr(items, '_subs', {}))
                    pagination = {'items': chunk, 'current_page': page_num, 'total_pages': total_pages, 'total_items': total_items, 'prev_url': f"/{output_name}/page/{page_num-1}/" if page_num > 1 else None, 'next_url': f"/{output_name}/page/{page_num+1}/" if page_num < total_pages else None, 'first_url': f"/{output_name}/", 'last_url': f"/{output_name}/page/{total_pages}/"}
                    if page_num == 2:
                        pagination['prev_url'] = f"/{output_name}/"
                    if page_num == 1:
                        pagination['prev_url'] = None
                    paginated_url = f"/{output_name}/" if page_num == 1 else f"/{output_name}/page/{page_num}/"
                    meta_pag = dict(meta)
                    meta_pag['url'] = paginated_url
                    meta_pag['permalink'] = paginated_url
                    ctx = self.build_context({
                        'site': self.config.get('site', {}),
                        'page': meta_pag,
                        'content': ctrl['content'],
                        'collections': self.collections,
                        'collection_name': output_name,
                        'collection': collection_name,
                        'pagination': pagination,
                        'items': chunk,
                        'posts': chunk,
                        'tags': self.tags,
                        'total_pages': total_pages,
                        'current_page': page_num,
                        'total_items': total_items,
                        'per_page': per_page,
                        'url': paginated_url,
                        'permalink': paginated_url
                    })
                    try:
                        html = self.render_template(layout, **ctx)
                    except:
                        try:
                            html = self.render_template('blog', **ctx)
                        except:
                            try:
                                html = self.render_template(output_name, **ctx)
                            except:
                                continue
                    if page_num == 1:
                        self.write_output(f'output/{output_name}/index.html', html)
                    else:
                        self.write_output(f'output/{output_name}/page/{page_num}/index.html', html)

    def generate_all_items(self):
        def _date_key(x):
            v = x.metadata.get('date')
            if isinstance(v, datetime):
                return v
            try:
                if isinstance(v, date):
                    return datetime.combine(v, datetime.min.time())
            except:
                pass
            if isinstance(v, str):
                try:
                    return datetime.fromisoformat(v)
                except:
                    try:
                        return datetime.strptime(v, "%Y-%m-%d")
                    except:
                        return datetime.min
            return datetime.min
        collection_sorted_cache = {}
        def get_sorted_collection(col_path):
            if col_path in collection_sorted_cache:
                return collection_sorted_cache[col_path]
            items = self.collections.get(col_path, None)
            if items is None:
                items = [it for it in self.all_items if it.metadata.get('_rel_path','').startswith(col_path + '/')]
                items = CollectionList(items)
            try:
                sorted_items = sorted(items, key=_date_key, reverse=True)
            except:
                sorted_items = list(items)
            collection_sorted_cache[col_path] = sorted_items
            return sorted_items
        try:
            sorted_all = sorted(self.all_items, key=_date_key, reverse=True)
        except:
            sorted_all = list(self.all_items)
        for item in self.all_items:
            rel = item.metadata.get('_rel_path', '')
            if rel == '':
                continue
            fpath = item.metadata.get('_file', '')
            try:
                parts = Path(fpath).relative_to('content').parts
            except:
                parts = Path(rel).parts
            prev_post = None
            next_post = None
            related_posts = []
            hierarchy = []
            if len(parts) > 1:
                for i in range(len(parts)-1, 0, -1):
                    col_path = '/'.join(parts[:i])
                    if col_path in self.collections:
                        hierarchy.append(col_path)
            if len(parts) > 0 and parts[0] not in hierarchy and parts[0] in self.collections:
                hierarchy.append(parts[0])
            sorted_col_used = None
            for col_path in hierarchy:
                cand = get_sorted_collection(col_path)
                idx = None
                for j, p in enumerate(cand):
                    if p.metadata.get('_file') == fpath or p.metadata.get('_rel_path') == rel:
                        idx = j
                        break
                if idx is None:
                    continue
                has_prev = idx > 0
                has_next = idx < len(cand) - 1
                if has_prev or has_next or col_path == hierarchy[-1]:
                    sorted_col_used = cand
                    if has_prev:
                        prev_post = cand[idx - 1]
                    if has_next:
                        next_post = cand[idx + 1]
                    if (not prev_post or not next_post) and len(hierarchy) > 1:
                        top_cand = get_sorted_collection(hierarchy[-1])
                        for j2, p2 in enumerate(top_cand):
                            if p2.metadata.get('_file') == fpath:
                                if not prev_post and j2 > 0:
                                    prev_post = top_cand[j2 - 1]
                                if not next_post and j2 < len(top_cand) - 1:
                                    next_post = top_cand[j2 + 1]
                                break
                    break
            if not prev_post and not next_post:
                for j, p in enumerate(sorted_all):
                    if p.metadata.get('_file') == fpath:
                        if j > 0:
                            prev_post = sorted_all[j - 1]
                        if j < len(sorted_all) - 1:
                            next_post = sorted_all[j + 1]
                        break
            try:
                cur_tags = item.metadata.get('tags', [])
                source = sorted_col_used if sorted_col_used else sorted_all
                if cur_tags:
                    for other in source:
                        if other.metadata.get('_file') == fpath:
                            continue
                        ot = other.metadata.get('tags', [])
                        if any(t in ot for t in cur_tags):
                            related_posts.append(other)
                        if len(related_posts) >= 6:
                            break
            except:
                related_posts = []
            default_layout = 'page'
            if len(parts) > 1:
                default_layout = parts[0].rstrip('s')
            layout = item.metadata.get('layout', default_layout)
            final_content = self.render_string_safe(item.content, self.build_context({
                'page': item.metadata,
                'post': item,
            }))
            ctx = self.build_context({
                'site': self.config.get('site', {}),
                'page': item.metadata,
                'post': item,
                'content': final_content,
                'toc': item.metadata.get('toc',''),
                'collection_name': parts[0] if len(parts)>1 else 'pages',
                'prev_post': prev_post,
                'next_post': next_post,
                'related_posts': related_posts,
                'prev': prev_post,
                'next': next_post,
            })
            try:
                html = self.render_template(layout, **ctx)
            except:
                try:
                    html = self.render_template('post', **ctx)
                except:
                    try:
                        html = self.render_template('page', **ctx)
                    except:
                        continue
            self.write_output(f'output/{rel}/index.html', html)

    def generate_tags(self):
        try:
            page_tags_index = {'url': '/tags/', 'permalink': '/tags/', 'slug': 'tags', 'title': 'Tags'}
            dummy_post = AttrDict()
            ctx = self.build_context({
                'site': self.config.get('site', {}),
                'page': page_tags_index,
                'url': '/tags/',
                'permalink': '/tags/',
                'post': dummy_post,
                'posts': []
            })
            html = self.render_template('tags', **ctx)
            self.write_output('output/tags/index.html', html)
            for tag, posts in self.tags.items():
                page_tag = {'url': f'/tags/{tag}/', 'permalink': f'/tags/{tag}/', 'slug': f'tags/{tag}', 'title': f'Tag: {tag}', 'tag': tag}
                first_post = posts[0] if posts else AttrDict()
                ctx2 = self.build_context({
                    'site': self.config.get('site', {}),
                    'tag': tag,
                    'posts': posts,
                    'post': first_post,
                    'all_tags': list(self.tags.keys()),
                    'page': page_tag,
                    'url': f'/tags/{tag}/',
                    'permalink': f'/tags/{tag}/',
                    'slug': f'tags/{tag}'
                })
                html2 = self.render_template('tag', **ctx2)
                self.write_output(f'output/tags/{tag}/index.html', html2)
        except:
            pass

    def generate_feeds(self):
        for col_name in self.collections:
            items = self.collections[col_name][:10]
            if not items:
                continue
            try:
                html = self.render_template('feed', site=self.config.get('site', {}), posts=items, collection_name=col_name, collections=self.collections, now=datetime.now(), version=VERSION, generator=GENERATOR)
                Path(f'output/{col_name}/feed.xml').parent.mkdir(parents=True, exist_ok=True)
                Path(f'output/{col_name}/feed.xml').write_text(html, encoding='utf-8')
                self.total_files += 1
            except:
                pass
        try:
            site = self.config.get('site', {})
            site_url = site.get('url', 'http://localhost:8000').rstrip('/')
            site_name = site.get('name', 'PyCora')
            site_desc = site.get('description', 'Static Site')
            def _feed_date_key(x):
                d = x.metadata.get('date')
                if isinstance(d, datetime):
                    return d
                try:
                    if isinstance(d, date):
                        return datetime.combine(d, datetime.min.time())
                except:
                    pass
                if d is None or d == '':
                    return datetime.min
                return datetime.min
            all_posts = sorted(self.all_items, key=_feed_date_key, reverse=True)[:20]
            rss_items = ""
            for p in all_posts:
                title = p.metadata.get('title', 'Untitled')
                link = f"{site_url}{p.metadata.get('url', '/')}"
                desc = p.metadata.get('description', '') or p.metadata.get('excerpt', '') or ''
                import xml.sax.saxutils as saxutils
                title_esc = saxutils.escape(str(title))
                date_str = ""
                try:
                    d = p.metadata.get('date')
                    if isinstance(d, datetime):
                        date_str = d.strftime('%a, %d %b %Y %H:%M:%S GMT')
                    else:
                        date_str = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
                except:
                    date_str = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
                rss_items += f"\n  <item>\n    <title>{title_esc}</title>\n    <link>{link}</link>\n    <guid>{link}</guid>\n    <description><![CDATA[{desc}]]></description>\n    <pubDate>{date_str}</pubDate>\n  </item>"
            rss_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n  <title>{site_name}</title>\n  <description>{site_desc}</description>\n  <link>{site_url}/</link>\n  <atom:link href="{site_url}/feed.xml" rel="self" type="application/rss+xml" />\n  <lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>\n  <generator>{GENERATOR}</generator>\n  {rss_items}\n</channel>\n</rss>'
            Path('output/feed.xml').write_text(rss_xml, encoding='utf-8')
            Path('output/rss.xml').write_text(rss_xml, encoding='utf-8')
            Path('output/feed/rss.xml').parent.mkdir(parents=True, exist_ok=True)
            Path('output/feed/rss.xml').write_text(rss_xml, encoding='utf-8')
            self.total_files += 3
            atom_items = ""
            for p in all_posts:
                title = p.metadata.get('title', 'Untitled')
                link = f"{site_url}{p.metadata.get('url', '/')}"
                desc = p.metadata.get('description', '') or ''
                title_esc = saxutils.escape(str(title))
                updated = datetime.now().isoformat()
                try:
                    d = p.metadata.get('date')
                    if isinstance(d, datetime):
                        updated = d.isoformat()
                except:
                    pass
                atom_items += f"\n  <entry>\n    <title>{title_esc}</title>\n    <link href=\"{link}\" />\n    <id>{link}</id>\n    <updated>{updated}</updated>\n    <summary><![CDATA[{desc}]]></summary>\n  </entry>"
            atom_xml = f'<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n  <title>{site_name}</title>\n  <subtitle>{site_desc}</subtitle>\n  <link href="{site_url}/atom.xml" rel="self" />\n  <link href="{site_url}/" />\n  <id>{site_url}/</id>\n  <updated>{datetime.now().isoformat()}</updated>\n  {atom_items}\n</feed>'
            Path('output/atom.xml').write_text(atom_xml, encoding='utf-8')
            Path('output/feed/atom.xml').parent.mkdir(parents=True, exist_ok=True)
            Path('output/feed/atom.xml').write_text(atom_xml, encoding='utf-8')
            self.total_files += 2
            import json as json_lib
            json_items = []
            for p in all_posts:
                link = f"{site_url}{p.metadata.get('url', '/')}"
                json_items.append({"id": link, "url": link, "title": p.metadata.get('title', 'Untitled'), "summary": p.metadata.get('description', '') or p.metadata.get('excerpt', '') or '', "date_published": p.metadata.get('date').isoformat() if isinstance(p.metadata.get('date'), datetime) else datetime.now().isoformat(), "tags": p.metadata.get('tags', [])})
            json_feed = {"version": "https://jsonfeed.org/version/1", "title": site_name, "description": site_desc, "home_page_url": f"{site_url}/", "feed_url": f"{site_url}/feed.json", "items": json_items}
            Path('output/feed.json').write_text(json_lib.dumps(json_feed, indent=2), encoding='utf-8')
            Path('output/feed/feed.json').parent.mkdir(parents=True, exist_ok=True)
            Path('output/feed/feed.json').write_text(json_lib.dumps(json_feed, indent=2), encoding='utf-8')
            self.total_files += 2
        except:
            pass

    def generate_sitemap(self):
        try:
            site = self.config.get('site', {})
            site_url = site.get('url', 'http://localhost:8000').rstrip('/')
            urls = []
            urls.append(f"  <url><loc>{site_url}/</loc><lastmod>{datetime.now().date().isoformat()}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>")
            for item in self.all_items:
                loc = f"{site_url}{item.metadata.get('url', '/')}"
                lastmod = ""
                try:
                    d = item.metadata.get('date')
                    if isinstance(d, datetime):
                        lastmod = f"<lastmod>{d.date().isoformat()}</lastmod>"
                    elif d:
                        lastmod = f"<lastmod>{datetime.now().date().isoformat()}</lastmod>"
                except:
                    pass
                urls.append(f"  <url><loc>{loc}</loc>{lastmod}<changefreq>weekly</changefreq><priority>0.8</priority></url>")
            for tag in self.tags.keys():
                urls.append(f"  <url><loc>{site_url}/tags/{tag}/</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>")
            urls.append(f"  <url><loc>{site_url}/tags/</loc><changefreq>weekly</changefreq><priority>0.3</priority></url>")
            for ctrl_name in self.controllers.keys():
                urls.append(f"  <url><loc>{site_url}/{ctrl_name}/</loc><changefreq>daily</changefreq><priority>0.7</priority></url>")
            base_dir = Path('templates')
            for f in list(base_dir.rglob('*.pax'))+list(base_dir.rglob('*.html')):
                rel = f.relative_to(base_dir).as_posix()
                if rel.startswith('partials/') or rel.startswith('layouts/'):
                    continue
                try:
                    raw = f.read_text(encoding='utf-8')
                    if not raw.startswith('---'):
                        continue
                    fm,_ = self.parse_template_frontmatter(f)
                    if 'layout' in fm or 'permalink' in fm or 'url' in fm:
                        p = fm.get('permalink') or fm.get('url')
                        if p:
                            urls.append(f"  <url><loc>{site_url}{p}</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>")
                        else:
                            rn = f.relative_to(base_dir).with_suffix('')
                            if rn.name == 'index':
                                loc = f"{site_url}/{rn.parent}/"
                            else:
                                loc = f"{site_url}/{rn}/"
                            urls.append(f"  <url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>")
                except:
                    pass
            sitemap_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{chr(10).join(urls)}\n</urlset>'
            Path('output/sitemap.xml').write_text(sitemap_xml, encoding='utf-8')
            self.total_files += 1
            robots_txt = f'User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n'
            Path('output/robots.txt').write_text(robots_txt, encoding='utf-8')
            self.total_files += 1
        except:
            pass

    def generate_404(self):
        try:
            html = self.render_template('404', site=self.config.get('site', {}), collections=self.collections, version=VERSION, generator=GENERATOR, generator_meta=GENERATOR_META)
            self.write_output('output/404.html', html)
        except:
            pass

    def copy_static(self):
        for src_root in [Path('static'), Path('public')]:
            if not src_root.exists():
                continue
            for item in src_root.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(src_root)
                    dest = Path('output') / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

    def build(self):
        self.scan_content()
        self.generate_landing()
        self.generate_controllers()
        self.generate_all_items()
        self.generate_pax_pages()
        self.generate_tags()
        self.generate_feeds()
        self.generate_sitemap()
        self.generate_404()
        self.copy_static()
        print(f"  Ready in {time.time()-self.start_time:.2f}s - {self.total_files} files - {VERSION}")
print(Colors.CYAN + "==================================================" + Colors.RESET)
print(Colors.BOLD + Colors.CYAN + "  PYCORA MEDUSA VERSION" + Colors.RESET)
print(Colors.YELLOW + "  SSG by Axcora Technology - www.axcora.com" + Colors.RESET)
print(Colors.CYAN + "===================================================" + Colors.RESET)
print(Colors.CYAN + f"  https://pycora:axcora.com/" + Colors.RESET)
print(Colors.CYAN + "===================================================" + Colors.RESET)

if __name__ == "__main__":
    SimpleSSG().build()
 
