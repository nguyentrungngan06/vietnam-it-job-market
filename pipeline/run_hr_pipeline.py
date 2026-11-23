"""One-command pipeline: snapshots/raw CSV -> master & joined tables -> cleaned, scored, dashboard-ready tables."""
import argparse
from pathlib import Path

from recruitment_pipeline import run as run_recruitment_pipeline
from dashboard_data import run as build_dashboard


def main():
    p = argparse.ArgumentParser(description='HR market intelligence preparation pipeline')
    p.add_argument('--input', nargs='+', type=Path, help='CSV/XLSX scraped job input files (optional if using snapshots)')
    p.add_argument('--from-snapshots', action='store_true', default=False, help='Build masters & join directly from snapshots <= cutoff date')
    p.add_argument('--itviec-dir', type=Path, default=Path('snapshotsitviec'), help='ITViec snapshots directory')
    p.add_argument('--vnworks-dir', type=Path, default=Path('snapshotvnwork'), help='VietnamWorks snapshots directory')
    p.add_argument('--cutoff', type=str, default='2026-10-25', help='Snapshot cutoff date YYYY-MM-DD (default: 2026-10-25)')
    p.add_argument('--reference', type=Path, help='Optional workbook containing 233 canonical skill names')
    p.add_argument('--out', type=Path, default=Path('hr_pipeline_output'))
    args = p.parse_args()

    clean_dir = args.out / 'clean'
    dashboard_dir = args.out / 'dashboard'

    # Run recruitment pipeline (master creation, joining 2 tables, cleaning, scoring)
    run_recruitment_pipeline(
        inputs=args.input,
        reference=args.reference,
        out=args.out,
        from_snapshots=args.from_snapshots or not args.input,
        itviec_dir=args.itviec_dir,
        vnworks_dir=args.vnworks_dir,
        cutoff=args.cutoff
    )

    # Run dashboard mart builder
    build_dashboard(clean_dir / 'combine_clean.csv', clean_dir / 'job_skill_level.csv', dashboard_dir)

    print(f"\nPipeline successfully completed!")
    print(f"- Masters & Joined Tables: {(args.out / 'master').resolve() if (args.out / 'master').exists() else 'N/A'}")
    print(f"- Clean & Scored Data:    {clean_dir.resolve()}")
    print(f"- Dashboard Mart Tables:  {dashboard_dir.resolve()}")


if __name__ == '__main__':
    main()
