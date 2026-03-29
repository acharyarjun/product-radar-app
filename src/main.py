"""Product Radar CLI — discovery, analysis, reports, Notion, persistence."""

from __future__ import annotations

import argparse
from datetime import date

import httpx
from loguru import logger

from src.analyzers import viability
from src.config import load_app_config, project_root, setup_logging
from src.git_ops import maybe_git_commit
from src.models import ViabilityStatus
from src.reporters import console, csv_export, daily_report, notion_register
from src.scheduler import run_scheduled_loop
from src.scrapers import aliexpress, amazon_es, http_utils, temu
from src.storage.database import get_session_factory, save_analysis, source_urls_with_notion
from src.storage.memory import load_memory, mark_run, save_memory, stable_key


def run_pipeline() -> None:
    root = project_root()
    cfg, env = load_app_config(root)
    setup_logging(cfg)
    memory_path = root / "memory.json"
    mem = load_memory(memory_path)
    db_path = root / cfg.storage.sqlite_path
    sf = get_session_factory(db_path)
    notion_done = source_urls_with_notion(sf)

    analyses: list = []
    with httpx.Client(headers=http_utils.browser_headers(), follow_redirects=True, timeout=30.0) as client:
        cats = cfg.radar.categories
        per = max(1, cfg.radar.max_products_per_run // max(1, len(cats)))
        discovered: list = []
        if cfg.sources.aliexpress.enabled:
            discovered.extend(
                aliexpress.fetch_products_for_categories(cfg, client, cats, per)
            )
        discovered.extend(temu.fetch_temu_products(cfg))

        new_products = []
        for p in discovered:
            if stable_key(p.source_url) in mem.seen_source_urls:
                continue
            new_products.append(p)
        new_products = new_products[: cfg.radar.max_products_per_run]
        logger.info("{} new products to analyze (of {} discovered)", len(new_products), len(discovered))

        for p in new_products:
            try:
                comps = amazon_es.search_competitors(cfg, client, p.name)
                an = viability.build_analysis(cfg, p, comps)
                analyses.append(an)
                save_analysis(sf, an)
                mem.seen_source_urls.add(stable_key(p.source_url))
            except Exception as e:  # noqa: BLE001
                logger.exception("Analysis failed for {}: {}", p.name, e)

    run_d = date.today()
    if analyses:
        daily_report.write_daily_report(root, cfg, analyses, run_d)
        csv_export.write_csv_export(root, cfg, analyses, run_d)
    else:
        logger.warning("No new analyses; skipping file reports")
    console.print_summary(analyses)

    registered_urls = set(notion_done)
    for u in registered_urls:
        mem.seen_source_urls.add(stable_key(u))

    notion_map = notion_register.register_analyses(
        cfg, env, analyses, run_d, registered_urls
    )
    for url, page_id in notion_map.items():
        for an in analyses:
            if an.product.source_url == url:
                save_analysis(sf, an, notion_page_id=page_id)
                break

    viable_n = sum(1 for a in analyses if a.viability == ViabilityStatus.VIABLE)
    mark_run(mem)
    save_memory(memory_path, mem)

    msg = f"Daily radar: {run_d.isoformat()} - {viable_n} productos viables"
    maybe_git_commit(root, cfg, msg)


def main() -> None:
    parser = argparse.ArgumentParser(description="Product Radar agent")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run daily at config schedule (blocking)",
    )
    args = parser.parse_args()
    if args.schedule:

        def job() -> None:
            run_pipeline()

        cfg, _ = load_app_config(project_root())
        setup_logging(cfg)
        run_scheduled_loop(cfg, job)
    else:
        run_pipeline()


if __name__ == "__main__":
    main()