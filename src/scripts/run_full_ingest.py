#!/usr/bin/env python3
"""
InvestIQ - Full Ingestion Script
Replaces: dags/ai50_full_ingest_dag.py

This script does the SAME thing as the Airflow DAG but as a simple Python script:
1. Reads company list from seed JSON
2. Creates folder structure for each company
3. Scrapes all company pages
4. Saves raw HTML and cleaned text

Usage:
    python scripts/run_full_ingest.py                    # All companies
    python scripts/run_full_ingest.py --limit 10         # First 10 only
    python scripts/run_full_ingest.py --company anthropic # Single company
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.scripts.utils.ingest import run_full_load_one


def load_company_list(seed_path: Path) -> List[Dict[str, Any]]:
    """Read seed JSON and normalize company_id."""
    print(f"📖 Loading companies from {seed_path}")
    
    data = json.loads(seed_path.read_text())
    companies = data["companies"] if isinstance(data, dict) and "companies" in data else data
    
    # Create slug for company_id if missing
    def slug(s: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")
    
    for c in companies:
        c["company_id"] = c.get("company_id") or slug(c.get("company_name", "unknown"))
    
    print(f"✓ Found {len(companies)} companies")
    return companies


def prep_company_folder(company: Dict[str, Any], data_dir: Path) -> Dict[str, Any]:
    """Create data/raw/<company_id>/initial folder."""
    out_dir = data_dir / "raw" / company["company_id"] / "initial"
    out_dir.mkdir(parents=True, exist_ok=True)
    company["out_dir"] = str(out_dir)
    return company


def scrape_company(company: Dict[str, Any], index: int, total: int) -> Dict[str, Any]:
    """Scrape a single company's pages."""
    company_name = company.get("company_name", company["company_id"])
    print(f"\n[{index}/{total}] 🔍 Scraping {company_name}...")
    
    try:
        meta_path = run_full_load_one(company, company["out_dir"])
        company["metadata_path"] = meta_path
        company["status"] = "success"
        print(f"  ✓ Success: {meta_path}")
    except Exception as e:
        company["status"] = "failed"
        company["error"] = str(e)
        print(f"  ✗ Failed: {e}")
    
    return company


def save_run_summary(results: List[Dict[str, Any]], output_path: Path):
    """Save summary of the ingestion run."""
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_companies": len(results),
        "successful": len([r for r in results if r.get("status") == "success"]),
        "failed": len([r for r in results if r.get("status") == "failed"]),
        "results": results
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2))
    print(f"\n📊 Summary saved to: {output_path}")
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="InvestIQ: Full company data ingestion")
    parser.add_argument("--seed", help="Path to specific seed JSON file")
    parser.add_argument("--seed-dir", default="data/seed", help="Directory containing seed JSON files")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    parser.add_argument("--limit", type=int, help="Limit to N companies per seed file (for testing)")
    parser.add_argument("--company", help="Scrape single company by name/ID")
    parser.add_argument("--output", default=None, 
                       help="Path to save run summary (default: data/logs/full_ingest_summary_YYYYMMDD_HHMMSS.json)")
    
    args = parser.parse_args()
    
    # Setup paths
    data_dir = PROJECT_ROOT / args.data_dir
    
    # Generate output path with datetime if not specified
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = PROJECT_ROOT / "data" / "logs" / f"full_ingest_summary_{timestamp}.json"
    else:
        output_path = PROJECT_ROOT / args.output
    
    # Determine which seed files to process
    seed_files = []
    if args.seed:
        # Single seed file specified
        seed_path = PROJECT_ROOT / args.seed
        if not seed_path.exists():
            print(f"❌ Error: Seed file not found: {seed_path}")
            sys.exit(1)
        seed_files = [seed_path]
    else:
        # Process all JSON files in seed directory
        seed_dir = PROJECT_ROOT / args.seed_dir
        if not seed_dir.exists():
            print(f"❌ Error: Seed directory not found: {seed_dir}")
            sys.exit(1)
        seed_files = sorted(seed_dir.glob("*.json"))
        if not seed_files:
            print(f"❌ Error: No JSON files found in: {seed_dir}")
            sys.exit(1)
    
    print("=" * 70)
    print("🚀 InvestIQ - Full Company Data Ingestion")
    print("=" * 70)
    print(f"Seed files to process: {len(seed_files)}")
    print(f"Data directory: {data_dir}")
    print()
    
    # Process each seed file
    all_results = []
    for seed_idx, seed_path in enumerate(seed_files, 1):
        print(f"\n{'=' * 70}")
        print(f"📄 Processing seed file {seed_idx}/{len(seed_files)}: {seed_path.name}")
        print(f"{'=' * 70}\n")
        
        # Load companies from this seed file
        companies = load_company_list(seed_path)
        
        # Filter if requested
        if args.company:
            company_lower = args.company.lower()
            companies = [
                c for c in companies 
                if company_lower in c.get("company_name", "").lower() 
                or company_lower in c.get("company_id", "").lower()
            ]
            if not companies:
                print(f"⚠️  No companies found matching: {args.company} in {seed_path.name}")
                continue
            print(f"📌 Filtering to company: {companies[0]['company_name']}")
        
        if args.limit:
            companies = companies[:args.limit]
            print(f"📌 Limited to first {args.limit} companies per seed file")
        
        total = len(companies)
        print(f"\n🎯 Will scrape {total} companies from {seed_path.name}\n")
        
        # Prep folders and scrape each company
        for i, company in enumerate(companies, 1):
            company = prep_company_folder(company, data_dir)
            result = scrape_company(company, i, total)
            all_results.append(result)
    
    # Save combined summary
    summary = save_run_summary(all_results, output_path)
    
    # Print final summary
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)
    print(f"Total companies: {summary['total_companies']}")
    print(f"✓ Successful: {summary['successful']}")
    print(f"✗ Failed: {summary['failed']}")
    
    if summary['failed'] > 0:
        print("\n❌ Failed companies:")
        for r in results:
            if r.get('status') == 'failed':
                print(f"  - {r.get('company_name', r['company_id'])}: {r.get('error', 'Unknown error')}")
    
    print("=" * 70)
    
    # Exit with error code if any failures
    sys.exit(0 if summary['failed'] == 0 else 1)


if __name__ == "__main__":
    main()

