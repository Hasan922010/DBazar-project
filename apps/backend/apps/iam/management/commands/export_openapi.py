"""
Django management command `export_openapi`:
Exports the full OpenAPI 3.1.0 schema from `config.api_router.api_router`
to `packages/contracts/openapi.yaml` (and `openapi.json`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand

from config.api_router import api_router
import config.urls  # noqa: F401 - ensures all domain API routes are imported and registered


class Command(BaseCommand):
    help = "Export DBazar Contract-First OpenAPI 3.1.0 specification to packages/contracts/openapi.yaml"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--output",
            type=str,
            default=str(getattr(settings, "OPENAPI_CONTRACT_PATH")),
            help="Target path for openapi.yaml",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        schema = api_router.generate_openapi_schema()

        yaml_text = yaml.safe_dump(schema, sort_keys=False, allow_unicode=True)
        output_path.write_text(yaml_text, encoding="utf-8")

        json_path = output_path.with_suffix(".json")
        json_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported OpenAPI 3.1.0 contract ({len(schema.get('paths', {}))} paths) to {output_path}"
            )
        )
