#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Universal LogStorm management entrypoint.

`python main.py` keeps the historical behavior and runs attendance analysis.
Additional subcommands provide one place for local application operations.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from analyzer import AttendanceService, DataLoader
from analyzer.reporters import ExcelReporter, SummaryReporter
from core import LogStormCore


class LogStormApp:
    def __init__(self, core: LogStormCore | None = None):
        self.core = core or LogStormCore.from_sources()
        self.records = []

    def run(self) -> None:
        print("=" * 80)
        print("LogStorm - Attendance Analysis")
        print("=" * 80)

        print("\n[1/4] Загрузка...")
        cli_settings = self.core.settings.cli
        if not os.path.exists(cli_settings.logs_file):
            raise FileNotFoundError(
                f"Файл логов не найден: {cli_settings.logs_file}. "
                "Укажите существующий путь через LOGSTORM_LOGS_FILE "
                "или core/settings.py."
            )
        df = DataLoader.load_logs(cli_settings.logs_file)

        if (
            cli_settings.person_mapping_file
            and os.path.exists(cli_settings.person_mapping_file)
        ):
            from analyzer import PersonMapper

            mapper = PersonMapper(cli_settings.person_mapping_file)
            prefs = mapper.convert_to_prefs_format()
        else:
            print("Маппинг не задан - используются дефолты")
            prefs = {}

        print(f"Загружено {len(df)} записей, {len(prefs)} профилей")
        df = DataLoader.filter_known_users(df, prefs)

        print("\n[2/4] Анализ...")
        service = AttendanceService(df, prefs)
        self.records = service.analyze_all()

        print("\n[3/4] Сводка...")
        summary = SummaryReporter(self.records)
        summary.print_summary()

        print("\n[4/4] Excel отчёт...")
        output_dir = os.path.dirname(cli_settings.output_excel_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        excel_reporter = ExcelReporter(self.records)
        excel_reporter.generate_report(cli_settings.output_excel_file)

        print("\n[OK] Анализ завершен!")
        print(f"Отчёт сохранён: {cli_settings.output_excel_file}")


def run_analyze(args: argparse.Namespace) -> None:
    core = LogStormCore.from_sources()
    if args.logs_file:
        core.settings.cli.logs_file = args.logs_file
    if args.mapping_file is not None:
        core.settings.cli.person_mapping_file = args.mapping_file
    if args.output_file:
        core.settings.cli.output_excel_file = args.output_file
    LogStormApp(core).run()


def run_api(args: argparse.Namespace) -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "uvicorn не установлен. Установите зависимости из requirements.txt."
        ) from exc

    from api.app import create_app

    app = create_app(db_path=args.db_path, api_token=args.api_token)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


def run_collector(args: argparse.Namespace) -> None:
    from collector.collector import main as collector_main

    collector_args = []
    if args.config:
        collector_args.extend(["--config", args.config])
    if args.once:
        collector_args.append("--once")
    if args.init:
        collector_args.append("--init")
    if args.backfill_images:
        collector_args.append("--backfill-images")
    if args.backfill_limit is not None:
        collector_args.extend(["--backfill-limit", str(args.backfill_limit)])
    if args.verbose:
        collector_args.append("--verbose")
    collector_main(collector_args)


def run_check(_: argparse.Namespace) -> None:
    from tools.check_environment import main as check_main

    check_main()


def run_collector_migrate(args: argparse.Namespace) -> None:
    from collector.migrate import migrate_collector_storage
    from core import build_settings

    settings = build_settings()
    target_db = args.target_db or settings.collector.sqlite_path

    def progress(label: str, copied: int) -> None:
        print(f"[collector-migrate] {label}: {copied}")

    counts = migrate_collector_storage(
        args.source_db,
        target_db,
        batch_size=args.batch_size,
        overwrite=args.overwrite,
        progress_callback=progress if args.verbose else None,
    )
    print(
        "[collector-migrate] done: "
        f"events={counts['events']}, "
        f"states={counts['states']}, "
        f"overrides={counts['overrides']}"
    )


def run_mapping(args: argparse.Namespace) -> None:
    from tools.manage_mapping import main as mapping_main

    mapping_main(args.mapping_file)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LogStorm management utility",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze = subparsers.add_parser(
        "analyze",
        help="Run attendance analysis and generate an Excel report",
    )
    analyze.add_argument("--logs-file", help="CSV, NDJSON or SQLite source")
    analyze.add_argument(
        "--mapping-file",
        help="Optional person mapping JSON. Use an empty string to disable.",
    )
    analyze.add_argument("--output-file", help="Excel report output path")
    analyze.set_defaults(func=run_analyze)

    api = subparsers.add_parser("api", help="Run LogStorm FastAPI server")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)
    api.add_argument("--db-path", help="Collector DB path or SQLAlchemy URL")
    api.add_argument("--api-token", help="Bearer token for API requests")
    api.add_argument("--reload", action="store_true")
    api.set_defaults(func=run_api)

    collector = subparsers.add_parser(
        "collector",
        help="Run collector commands",
    )
    collector.add_argument(
        "--config",
        "-c",
        help="Optional legacy collector override config",
    )
    collector.add_argument("--once", action="store_true")
    collector.add_argument("--init", action="store_true")
    collector.add_argument("--backfill-images", action="store_true")
    collector.add_argument("--backfill-limit", type=int)
    collector.add_argument("--verbose", "-v", action="store_true")
    collector.set_defaults(func=run_collector)

    collector_migrate = subparsers.add_parser(
        "collector-migrate",
        help="Migrate collector storage into the DB configured in project settings",
    )
    collector_migrate.add_argument("--source-db", required=True)
    collector_migrate.add_argument(
        "--target-db",
        help="Optional override for target DB URL/path. Defaults to project settings.",
    )
    collector_migrate.add_argument("--batch-size", type=int, default=1000)
    collector_migrate.add_argument("--overwrite", action="store_true")
    collector_migrate.add_argument("--verbose", "-v", action="store_true")
    collector_migrate.set_defaults(func=run_collector_migrate)

    check = subparsers.add_parser("check", help="Check local environment")
    check.set_defaults(func=run_check)

    mapping = subparsers.add_parser(
        "mapping",
        help="Run legacy person mapping utility",
    )
    mapping.add_argument("--mapping-file", help="Mapping JSON path")
    mapping.set_defaults(func=run_mapping)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        run_analyze(
            argparse.Namespace(
                logs_file=None,
                mapping_file=None,
                output_file=None,
            )
        )
        return
    args.func(args)


if __name__ == "__main__":
    main()
