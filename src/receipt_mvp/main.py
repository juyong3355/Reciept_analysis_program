from __future__ import annotations

import argparse
import json
from pathlib import Path

from receipt_mvp import __version__
from receipt_mvp.models import ReceiptRecord
from receipt_mvp.services.logging_utils import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="receipt-mvp", description="영수증 자동 처리 MVP")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    schema = subparsers.add_parser("schema", help="표준 ReceiptRecord JSON Schema 출력")
    schema.add_argument("--output", type=Path, help="Schema 저장 경로")
    subparsers.add_parser("gui", help="데스크톱 사용자 인터페이스 실행")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    if args.command == "schema":
        payload = json.dumps(ReceiptRecord.model_json_schema(), ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload)
        return 0
    if args.command == "gui":
        from receipt_mvp.ui.app import run_gui

        return run_gui()
    if args.command is None:
        build_parser().print_help()
        return 0
    return 2

