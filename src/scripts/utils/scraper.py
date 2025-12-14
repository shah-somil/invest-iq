#!/usr/bin/env python3
# src/lab1_scraper.py
"""
InvestIQ — Scrape & Store (robust, pattern-matching version)

Data Sources:
    - Company websites (publicly accessible pages only)
    - Seed data from top AI and Fintech company lists
    Citation: All scraped content is from publicly available company websites.
    Used for research and analysis purposes only. See ETHICS.md for details.

External Libraries:
    - requests: https://requests.readthedocs.io/ (Apache 2.0 License)
    - beautifulsoup4: https://www.crummy.com/software/BeautifulSoup/ (MIT License)
    - lxml: https://lxml.de/ (BSD License)

Ethical Considerations:
    - Checks robots.txt before scraping to respect website policies
    - Only scrapes publicly accessible, non-authenticated content
    - Implements host blocking to avoid paywalled content
    - Filters spam URLs and focuses on main content sections
    - All data used for research/analysis, not commercial redistribution
    - See ETHICS.md for comprehensive ethical guidelines

Usage (examples)
---------------
python3 -m src.lab1_scraper --limit 5
python3 -m src.lab1_scraper --company openai
python3 -m src.lab1_scraper --gcs-bucket lab1_raw
python3 -m src.lab1_scraper --overrides data/domain_overrides.json

What it does
------------
• Reads seed: data/seed/top_ai50_seed.json or data/seed/top_fintech50_seed.json  (list or {"companies":[...]})
  expects: company_id, company_name, website
• Fetches and saves (per company):
    - homepage
    - about
    - product/platform/solutions
    - careers/jobs/join
    - blog/news/press/insights/resources/stories/media
• For each section it saves:
    - <section>.html  (raw HTML)
    - <section>.txt   (clean text)
    - <section>.meta.json  (rich page metadata incl. source_url, canonical, sha256, etc.)
• Emits:
    - manifest.json   (chosen URLs for sections)
    - pages.jsonl     (1 JSON object per saved page: section, source_url, crawled_at, status, bytes)
• Output layout:
    data/raw/<company_id>/initial/   (or data/raw/<company_id>/runs/<UTC>/ with --run-mode run)

Guardrails & extras
-------------------
• Checks robots.txt before scraping any URL (respects website crawling policies)
• Never crawls blocked hosts. If homepage resolves there → skip with warning.
• Checks robots.txt before scraping to respect website crawling policies.
• Optional per-company domain overrides: --overrides data/domain_overrides.json
  Format: { "cohere": "https://cohere.com", "baseten": "https://www.baseten.co", ... }
• Section discovery: smart regex on anchor text + URL path, plus scoring and same-domain enforcement.
• Blocks coupon/utm/ref spam in URLs.
• Parser fallback: uses lxml if installed, else html.parser.

Requirements
------------
requests
beautifulsoup4
lxml                      # optional (recommended)
google-cloud-storage      # only if using --gcs-bucket
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]  # src/scripts/lib/scraper.py -> project root
DEFAULT_SEED_PATH = REPO_ROOT / "data" / "seed" / "top_ai50_seed.json"
_SEED_INDEX = None

import requests
from bs4 import BeautifulSoup

# -------- parser selection (fallback if lxml not present) --------
try:
    import lxml  # noqa: F401
    _PARSER = "lxml"
except Exception:
    _PARSER = "html.parser"

# -------- HTTP defaults --------
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
TIMEOUT = 25

# -------- Blocked hosts / spam --------
BLOCKED_HOSTS = {"forbes.com", "www.forbes.com", "w1.buysub.com", "buysub.com"}
SPAM_PATH = re.compile(r"(coupon|coupons|offer|deals|ref=|utm_)", re.I)

# -------- robots.txt cache --------
_ROBOTS_CACHE = {}  # domain -> RobotFileParser instance
_ROBOTS_DECISIONS = {}  # company_id -> {"status": "allowed"/"disallowed"/"error", "domain": str, "robots_url": str, "checked_at": str}

# -------- Section regex patterns --------
PATTERNS = {
    "about": re.compile(
        r"(about(\s*us)?|about-us|company|who\s*we\s*are|our\s*story|mission|team(?!#careers))",
        re.I),
    "product": re.compile(
        r"(product(s)?|platform|solution(s)?|technology|features|capabilit(y|ies))",
        re.I),
    "careers": re.compile(
        r"(career(s)?|jobs?|join(\s*us)?|we'?re\s*hiring|open\s*roles|team#careers)",
        re.I),
    "blog": re.compile(
        r"(blog|news|press|insights|resources|stories|media|updates)",
        re.I),
}

# -------- Canonical slug attempts before discovery --------
CANDIDATE_SLUGS = {
    "homepage": [""],
    "about": ["about", "about-us", "company", "who-we-are", "our-story"],
    "product": ["product", "products", "platform", "solutions", "technology", "features"],
    "careers": ["careers", "career", "jobs", "join-us", "join", "team#careers"],
    "blog": ["blog", "news", "press", "insights", "resources", "stories", "media"],
}

# -------- Optional GCS --------
try:
    from google.cloud import storage  # pip install google-cloud-storage
    _HAS_GCS = True
except Exception:
    _HAS_GCS = False


# ========================== utilities ==========================

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_seed(path="data/seed/top_ai50_seed.json"):
    data = read_json(path)
    rows = data.get("companies", data) if isinstance(data, dict) else data
    out = []
    for r in rows:
        cid = r.get("company_id") or slugify(r.get("company_name", ""))
        out.append({
            "company_id": cid,
            "company_name": r.get("company_name", cid),
            "website": normalize_base(r.get("website", "")),
        })
    return out


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-") or "company"


def normalize_base(url: str) -> str:
    if not url:
        return url
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if "text/html" in r.headers.get("Content-Type", ""):
            return r.url.rstrip("/")
    except Exception:
        pass
    return url.rstrip("/")


def same_domain(u: str, base: str) -> bool:
    try:
        return urlparse(u).netloc == urlparse(base).netloc
    except Exception:
        return False


def is_html_ok(resp: requests.Response) -> bool:
    ctype = resp.headers.get("Content-Type", "").lower()
    return resp.status_code == 200 and ("text/html" in ctype or "application/xhtml" in ctype)


def fetch(url: str, check_robots: bool = True) -> requests.Response:
    """
    Fetch a URL with optional robots.txt checking.
    
    Args:
        url: URL to fetch
        check_robots: If True, check robots.txt before fetching
    
    Returns:
        requests.Response object
    
    Raises:
        requests.RequestException if robots.txt disallows or fetch fails
    """
    if check_robots:
        if not can_fetch(url):
            raise requests.RequestException(
                f"robots.txt disallows fetching {url} for user-agent: {UA}"
            )
    
    return requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, _PARSER)


def clean_text(html: str) -> str:
    s = soup(html)
    for tag in s(["script", "style", "noscript", "svg"]):
        tag.decompose()
    for tag in s.find_all(["nav", "footer", "form", "iframe"]):
        tag.decompose()
    text = s.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def page_meta(html: str, url: str, company_name: str, status: int) -> dict:
    s = soup(html)
    title = (s.title.get_text(strip=True) if s.title else "") or ""
    canonical = ""
    link_canon = s.find("link", rel=lambda x: x and "canonical" in x)
    if link_canon and link_canon.has_attr("href"):
        canonical = urljoin(url, link_canon["href"])
    robots = ""
    meta_robots = s.find("meta", attrs={"name": re.compile(r"robots", re.I)})
    if meta_robots and meta_robots.has_attr("content"):
        robots = meta_robots["content"]

    content_bytes = html.encode("utf-8")
    return {
        "company_name": company_name,
        "source_url": url,
        "crawled_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "http_status": status,
        "title": title[:400],
        "canonical": canonical or url,
        "robots": robots,
        "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
        "content_length": len(content_bytes),
        "parser": "lxml" if _PARSER == "lxml" else "bs4",
        "version": 1,
    }


def blocked(host: str) -> bool:
    host = (host or "").lower()
    return host in BLOCKED_HOSTS or any(host.endswith("." + b) for b in BLOCKED_HOSTS)


def get_robots_parser(url: str) -> RobotFileParser:
    """Get or create a RobotFileParser for the domain of the given URL."""
    try:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        if domain not in _ROBOTS_CACHE:
            rp = RobotFileParser()
            robots_url = urljoin(domain, "/robots.txt")
            rp.set_url(robots_url)
            try:
                rp.read()
            except Exception as e:
                # If robots.txt doesn't exist or is unreadable, allow all
                # (per robots.txt spec, missing file means allow all)
                print(f"  ⚠️  Could not read robots.txt for {domain}: {e}")
                # Create a permissive parser
                rp = RobotFileParser()
                rp.set_url(robots_url)
            _ROBOTS_CACHE[domain] = rp
        
        return _ROBOTS_CACHE[domain]
    except Exception:
        # On any error, return a permissive parser
        rp = RobotFileParser()
        rp.set_url("")
        return rp


def check_robots_for_company(company_id: str, company_name: str, base_url: str) -> dict:
    """
    Check robots.txt status for a company and track the decision.
    
    Returns:
        dict with status, domain, robots_url, checked_at, and details
    """
    try:
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = urljoin(domain, "/robots.txt")
        
        # Check if homepage is allowed
        rp = get_robots_parser(base_url)
        homepage_allowed = rp.can_fetch(UA, base_url)
        
        # Check a few common paths
        test_paths = [
            urljoin(base_url, "/about"),
            urljoin(base_url, "/product"),
            urljoin(base_url, "/careers"),
            urljoin(base_url, "/blog"),
        ]
        paths_allowed = {}
        for path in test_paths:
            paths_allowed[path] = rp.can_fetch(UA, path)
        
        # Determine overall status
        if homepage_allowed and any(paths_allowed.values()):
            status = "allowed"
        elif not homepage_allowed:
            status = "disallowed"
        else:
            status = "partially_allowed"
        
        decision = {
            "company_id": company_id,
            "company_name": company_name,
            "status": status,
            "domain": domain,
            "robots_url": robots_url,
            "homepage_allowed": homepage_allowed,
            "paths_allowed": paths_allowed,
            "checked_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        
        _ROBOTS_DECISIONS[company_id] = decision
        return decision
        
    except Exception as e:
        decision = {
            "company_id": company_id,
            "company_name": company_name,
            "status": "error",
            "domain": urlparse(base_url).netloc if base_url else "unknown",
            "robots_url": None,
            "error": str(e),
            "checked_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _ROBOTS_DECISIONS[company_id] = decision
        return decision


def save_robots_log(log_path: pathlib.Path):
    """Save robots.txt decisions to a log file."""
    ensure_dir(log_path.parent)
    
    log_data = {
        "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_companies": len(_ROBOTS_DECISIONS),
        "allowed": len([d for d in _ROBOTS_DECISIONS.values() if d.get("status") == "allowed"]),
        "disallowed": len([d for d in _ROBOTS_DECISIONS.values() if d.get("status") == "disallowed"]),
        "partially_allowed": len([d for d in _ROBOTS_DECISIONS.values() if d.get("status") == "partially_allowed"]),
        "errors": len([d for d in _ROBOTS_DECISIONS.values() if d.get("status") == "error"]),
        "decisions": list(_ROBOTS_DECISIONS.values()),
    }
    
    write_text(log_path, json.dumps(log_data, indent=2))
    return log_path


def can_fetch(url: str, user_agent: str = None) -> bool:
    """
    Check if a URL can be fetched according to robots.txt.
    
    Args:
        url: The URL to check
        user_agent: User agent string (defaults to UA from HEADERS)
    
    Returns:
        True if allowed, False if disallowed
    """
    if user_agent is None:
        user_agent = UA
    
    try:
        rp = get_robots_parser(url)
        return rp.can_fetch(user_agent, url)
    except Exception:
        # On error, default to allowing (permissive)
        return True


def discover_from_nav(base_url: str, homepage_html: str, section_key: str):
    """Collect candidate links from homepage anchors (same-domain), rank by regex on text+path."""
    s = soup(homepage_html)
    candidates = []
    for a in s.find_all("a", href=True):
        href = a["href"].strip()
        text = (a.get_text() or "").strip()
        url_abs = urljoin(base_url + "/", href)
        if not same_domain(url_abs, base_url):
            continue
        if SPAM_PATH.search(url_abs):
            continue
        # Check robots.txt before adding to candidates
        if not can_fetch(url_abs):
            continue
        candidates.append((url_abs, text))

    pattern = PATTERNS[section_key]

    def score(url_text_tuple):
        url_abs, text = url_text_tuple
        p = urlparse(url_abs)
        path = p.path or "/"
        t = text.lower()
        pl = path.lower()
        sc = 0.0
        if pattern.search(t):
            sc += 3.0
        if pattern.search(pl):
            sc += 2.0
        # shorter path preferred
        if pl in ("/", ""):
            sc -= 1.0
        sc += max(0.0, 1.0 - 0.25 * max(0, pl.count("/") - 1))
        # avoid query/fragment
        if p.query:
            sc -= 0.5
        if p.fragment:
            sc -= 0.2
        return sc

    ranked = sorted(candidates, key=score, reverse=True)
    seen, out = set(), []
    for u, _ in ranked:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:8]


def try_section(base_url: str, homepage_html: str, section_key: str):
    """Try canonical slugs first; then ranked nav-discovered candidates."""
    tried = []
    for slug in CANDIDATE_SLUGS[section_key]:
        url = base_url if slug == "" else urljoin(base_url + "/", slug)
        if url not in tried and not SPAM_PATH.search(url) and can_fetch(url):
            tried.append(url)
    tried.extend(u for u in discover_from_nav(base_url, homepage_html, section_key) if u not in tried)

    for u in tried:
        try:
            r = fetch(u, check_robots=True)
            if is_html_ok(r) and same_domain(r.url, base_url):
                return r.url.rstrip("/"), r.text, r.status_code
        except requests.RequestException as e:
            if "robots.txt disallows" in str(e):
                print(f"  ⚠️  robots.txt disallows: {u}")
            continue
        except Exception:
            continue
    return None, None, None


def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: pathlib.Path, content: str):
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def save_page(out_dir: pathlib.Path, section: str, url: str, html: str,
              company_name: str, status: int, pages_meta_fp):
    write_text(out_dir / f"{section}.html", html)
    write_text(out_dir / f"{section}.txt", clean_text(html))
    m = page_meta(html, url, company_name, status)
    write_text(out_dir / f"{section}.meta.json", json.dumps(m, indent=2))
    pages_meta_fp.write(json.dumps({
        "company_name": company_name,
        "section": section,
        "source_url": url,
        "crawled_at": m["crawled_at"],
        "status": status,
        "bytes": m["content_length"],
    }) + "\n")


def upload_dir_to_gcs(local_dir: pathlib.Path, bucket_name: str, prefix: str = ""):
    if not _HAS_GCS:
        raise RuntimeError("google-cloud-storage not installed. Add it to requirements.txt")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    for root, _, files in os.walk(local_dir):
        for name in files:
            lp = pathlib.Path(root) / name
            rel = lp.relative_to(local_dir)
            bucket.blob(str(pathlib.Path(prefix) / rel)).upload_from_filename(str(lp))


# ========================== adapters ==========================

def _seed_record(company_id: str):
    global _SEED_INDEX
    if _SEED_INDEX is None:
        if DEFAULT_SEED_PATH.exists():
            try:
                rows = read_seed(str(DEFAULT_SEED_PATH))
            except Exception:
                _SEED_INDEX = {}
            else:
                _SEED_INDEX = {row["company_id"]: row for row in rows}
        else:
            _SEED_INDEX = {}
    return (_SEED_INDEX or {}).get(company_id)


def _resolve_company_inputs(company_id=None, company=None, overrides=None):
    company = company or {}
    cid = company.get("company_id") or company_id or company.get("company_name", "")
    cid = slugify(cid or "")
    name = company.get("company_name") or company_id or cid
    website = (
        company.get("website")
        or company.get("homepage")
        or company.get("source_url")
        or company.get("url")
        or ""
    )

    overrides = overrides or {}
    override_url = overrides.get(cid)
    if override_url:
        website = normalize_base(override_url)

    if not website:
        seed_entry = _seed_record(cid)
        if seed_entry:
            name = seed_entry.get("company_name", name)
            website = seed_entry.get("website") or seed_entry.get("homepage") or website

    website = (website or "").strip()
    if website and not website.startswith("http"):
        website = "https://" + website.lstrip("/")
    website = website.rstrip("/")

    return {
        "company_id": cid or "company",
        "company_name": name or cid or "company",
        "website": website,
    }


class ScrapeCompanyError(Exception):
    """Raised for expected scrape failures (blocked host, 403, missing URL, etc.)."""

    def __init__(self, company_id: str, message: str, reason: str = "error"):
        super().__init__(message)
        self.company_id = company_id
        self.reason = reason


def _scrape_company_to_dir(record: dict, out_dir: pathlib.Path) -> dict:
    cid = record["company_id"]
    name = record["company_name"]
    base_url = record.get("website", "")
    if not base_url:
        raise ScrapeCompanyError(cid, "cannot scrape without a website URL", reason="missing_website")

    host = urlparse(base_url).netloc.lower()
    if blocked(host):
        raise ScrapeCompanyError(cid, f"seed website blocked ({base_url})", reason="blocked_host")

    # Check robots.txt status for this company
    robots_decision = check_robots_for_company(cid, name, base_url)
    if robots_decision.get("status") == "disallowed":
        print(f"  ⚠️  robots.txt disallows scraping for {name} ({base_url})")
        # Still try to scrape, but log the disallowance

    ensure_dir(out_dir)

    try:
        r0 = fetch(base_url)
    except Exception as exc:
        raise ScrapeCompanyError(
            cid, f"homepage fetch failed ({base_url}) -> {exc}", reason="homepage_fetch_failed"
        ) from exc

    if not is_html_ok(r0):
        status = getattr(r0, "status_code", None)
        raise ScrapeCompanyError(
            cid,
            f"homepage not HTML/200 ({base_url}) status={status}",
            reason="homepage_http_error",
        )

    homepage_final = r0.url.rstrip("/")
    final_host = urlparse(homepage_final).netloc.lower()
    if blocked(final_host):
        raise ScrapeCompanyError(
            cid, f"homepage resolved to blocked host ({homepage_final})", reason="blocked_redirect"
        )

    homepage_html = r0.text
    pages_meta_path = out_dir / "pages.jsonl"
    with open(pages_meta_path, "w", encoding="utf-8") as pages_fp:
        save_page(out_dir, "homepage", homepage_final, homepage_html, name, r0.status_code, pages_fp)
        manifest = {
            "company_id": cid,
            "company_name": name,
            "crawled_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sections": {"homepage": homepage_final},
        }

        for section in ["about", "product", "careers", "blog"]:
            url, html, status = try_section(homepage_final, homepage_html, section)
            if url and html:
                save_page(out_dir, section, url, html, name, status, pages_fp)
                manifest["sections"][section] = url
            else:
                manifest["sections"][section] = None

    write_text(out_dir / "manifest.json", json.dumps(manifest, indent=2))
    return {
        "company_id": cid,
        "company_name": name,
        "manifest_path": str(out_dir / "manifest.json"),
        "sections": manifest["sections"],
        "status": "success",
    }


def scrape_company(
    company_id=None,
    out_dir=None,
    *,
    company=None,
    overrides=None,
    output_dir=None,
    **_,
):
    if out_dir is None and output_dir is not None:
        out_dir = output_dir
    if out_dir is None:
        raise ValueError("scrape_company requires out_dir or output_dir")

    record = _resolve_company_inputs(company_id=company_id, company=company, overrides=overrides)
    out_path = pathlib.Path(out_dir)
    try:
        return _scrape_company_to_dir(record, out_path)
    except ScrapeCompanyError as exc:
        ensure_dir(out_path)
        failure_manifest = {
            "company_id": record["company_id"],
            "company_name": record["company_name"],
            "status": "failed",
            "reason": exc.reason,
            "message": str(exc),
            "crawled_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        write_text(out_path / "manifest.json", json.dumps(failure_manifest, indent=2))
        if not (out_path / "pages.jsonl").exists():
            write_text(out_path / "pages.jsonl", "")
        print(f"[scrape_company] {record['company_id']}: {exc.reason} ({exc})")
        return failure_manifest


# ========================== main ==========================

def main():
    ap = argparse.ArgumentParser(description="InvestIQ: Scrape & Store (robust)")
    ap.add_argument("--seed", default="data/seed/top_ai50_seed.json")
    ap.add_argument("--overrides", help="JSON map: company_id -> official base URL")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--company")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--run-mode", choices=["initial", "run"], default="initial")
    ap.add_argument("--gcs-bucket")
    args = ap.parse_args()

    companies = read_seed(args.seed)
    if args.company:
        companies = [c for c in companies if c["company_id"] == args.company]
    if args.limit and args.limit > 0:
        companies = companies[:args.limit]

    overrides = {}
    if args.overrides and os.path.exists(args.overrides):
        overrides = read_json(args.overrides)

    for idx, c in enumerate(companies, 1):
        cid = c["company_id"]
        name = c["company_name"]

        if args.run_mode == "initial":
            out_dir = pathlib.Path(args.out) / cid / "initial"
        else:
            ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
            out_dir = pathlib.Path(args.out) / cid / "runs" / ts

        base_display = overrides.get(cid) or c.get("website") or c.get("homepage") or "N/A"
        print(f"[{idx}/{len(companies)}] {name} -> {base_display}")

        result = scrape_company(company=c, out_dir=str(out_dir), overrides=overrides)
        if result.get("status") != "success":
            print(f"  !! {cid} skipped: {result.get('reason')} ({result.get('message')})")
            continue

        if args.gcs_bucket:
            prefix = f"raw/{cid}/" + ("initial" if args.run_mode == "initial" else f"runs/{out_dir.name}")
            print(f"  ↥ uploading to gs://{args.gcs_bucket}/{prefix}")
            upload_dir_to_gcs(out_dir, args.gcs_bucket, prefix=prefix)

        time.sleep(1.0)

    return 0


if __name__ == "__main__":
    sys.exit(main())
