from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Iterable, Set

from app.db.session import SessionLocal
from app.models.models import Run, Citation, Domain
from app.services.normalization import normalize_domain


def _load_project_domains(db, project_id: str, extra_domains: Iterable[str]) -> Set[str]:
    db_domains = [normalize_domain(d.domain) for d in db.query(Domain).filter(Domain.project_id == project_id).all()]
    extras = [normalize_domain(d) for d in (extra_domains or [])]
    return {d for d in (db_domains + extras) if d}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Citation.is_ours and Run counts for a project")
    parser.add_argument("--project", required=True, help="Project ID (e.g., prj_9e828878)")
    parser.add_argument("--extra-domains", nargs="*", default=[], help="Extra domains to consider as ours (will not be persisted to Domain table)")
    parser.add_argument("--dry-run", action="store_true", help="Do not commit changes, only print summary")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        project_id = args.project
        ours = _load_project_domains(db, project_id, args.extra_domains)
        if not ours:
            print(f"[WARN] No domains found for project {project_id}. Use --extra-domains or add Domains in the app.")
        else:
            print(f"[INFO] Domains used for matching: {sorted(ours)}")

        # Map run_id -> updates
        run_updates = defaultdict(lambda: {"citations": 0, "ours": 0, "domains": set()})

        # Fetch all citations for runs that belong to the project
        # Approach: get run ids first to avoid joining large tables unnecessarily
        run_ids = [rid for (rid,) in db.query(Run.id).filter(Run.project_id == project_id).all()]
        print(f"[INFO] Found {len(run_ids)} runs in project {project_id}")
        if not run_ids:
            return

        # Iterate citations in batches to avoid huge memory usage
        BATCH = 5000
        total_cits = 0
        updated_is_ours = 0
        updated_domains = 0

        def process_batch(batch_ids: list[str]):
            nonlocal total_cits, updated_is_ours, updated_domains
            if not batch_ids:
                return
            cits = (
                db.query(Citation)
                .filter(Citation.run_id.in_(batch_ids))
                .order_by(Citation.run_id.asc(), Citation.id.asc())
                .all()
            )
            for c in cits:
                total_cits += 1
                # normalize domain from URL/domain
                domain_norm = normalize_domain(c.url or c.domain or "")
                if domain_norm and c.domain != domain_norm:
                    c.domain = domain_norm
                    updated_domains += 1
                # compute is_ours
                is_ours = bool(domain_norm and domain_norm in ours)
                if bool(c.is_ours) != is_ours:
                    c.is_ours = is_ours
                    updated_is_ours += 1
                # aggregate per run
                ru = run_updates[c.run_id]
                ru["citations"] += 1
                if domain_norm:
                    ru["domains"].add(domain_norm)
                if is_ours:
                    ru["ours"] += 1

        # Process in chunks
        for i in range(0, len(run_ids), BATCH):
            process_batch(run_ids[i : i + BATCH])

        print(f"[INFO] Citations scanned: {total_cits}")
        print(f"[INFO] Citations domain normalized updates: {updated_domains}")
        print(f"[INFO] Citations is_ours updates: {updated_is_ours}")

        # Update runs counters
        runs_with_updates = 0
        for rid, agg in run_updates.items():
            r = db.get(Run, rid)
            if not r:
                continue
            # recompute and set
            new_citations_count = int(agg["citations"])
            new_our_count = int(agg["ours"])
            new_unique_domains = int(len(agg["domains"]))
            changed = False
            if (r.citations_count or 0) != new_citations_count:
                r.citations_count = new_citations_count
                changed = True
            if (r.our_citations_count or 0) != new_our_count:
                r.our_citations_count = new_our_count
                changed = True
            if (r.unique_domains_count or 0) != new_unique_domains:
                r.unique_domains_count = new_unique_domains
                changed = True
            if changed:
                runs_with_updates += 1
        print(f"[INFO] Runs with counter updates: {runs_with_updates}")

        if args.dry_run:
            db.rollback()
            print("[DRY-RUN] Rolled back. No changes committed.")
        else:
            db.commit()
            print("[OK] Changes committed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
