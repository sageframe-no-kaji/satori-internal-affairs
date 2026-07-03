"""CLI entry point for Anamnesis case generation.

Usage (Mode 1 — automated):
    python -m anamnesis generate --diagnosis pneumothorax --difficulty beginner --tone clinical

Usage (Mode 2 — creative seed file):
    python -m anamnesis generate --seed-file seeds/example-pneumothorax.yaml

Usage (real LLM):
    python -m anamnesis generate --seed-file seeds/rich.yaml --provider openai --model gpt-4o

Run ``python -m anamnesis generate --help`` for full option reference.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from llm_client import ModelConfig, Provider

from anamnesis.pipeline import CaseGenerationPipeline
from anamnesis.seed import CreativeSeed, load_seed_file


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m anamnesis",
        description="Anamnesis — LLM-powered medical case generation pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a case definition")

    # ── Seed source (mutually exclusive) ─────────────────────────────────────
    seed_group = gen.add_mutually_exclusive_group()
    seed_group.add_argument(
        "--seed-file",
        metavar="PATH",
        help="Path to YAML seed file (Mode 2). Overrides --diagnosis/--difficulty/--tone.",
    )
    gen.add_argument(
        "--diagnosis",
        default=None,
        help="Diagnosis name (Mode 1, required without --seed-file)",
    )
    gen.add_argument(
        "--difficulty",
        default="intermediate",
        help="Difficulty level: beginner | intermediate | advanced (default: intermediate)",
    )
    gen.add_argument(
        "--tone",
        default="medical_mystery",
        dest="tone",
        help="Dramatic tone (default: medical_mystery)",
    )

    # ── Provider / model ──────────────────────────────────────────────────────
    gen.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "anthropic"],
        help="LLM provider (default: mock)",
    )
    gen.add_argument(
        "--model",
        default=None,
        help="Model name (default: provider-specific sensible default)",
    )
    gen.add_argument(
        "--api-key",
        default=None,
        dest="api_key",
        help="API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var)",
    )
    gen.add_argument(
        "--schema-path",
        default=None,
        dest="schema_path",
        help="Path to JSON schema file (required for non-mock providers)",
    )

    # ── Output ────────────────────────────────────────────────────────────────
    gen.add_argument(
        "--output-dir",
        default=None,
        dest="output_dir",
        help="Output directory (default: cases/generated/)",
    )
    gen.add_argument(
        "--no-save",
        action="store_true",
        dest="no_save",
        help="Generate but do not save to disk",
    )
    gen.add_argument(
        "--max-retries",
        type=int,
        default=3,
        dest="max_retries",
        help="Maximum simple retry attempts before repair (default: 3)",
    )

    # ── Verbosity ─────────────────────────────────────────────────────────────
    gen.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )

    return parser


def _resolve_api_key(args: argparse.Namespace) -> str | None:
    """Resolve API key from CLI flag or environment variable."""
    if args.api_key:
        return str(args.api_key)
    provider = args.provider
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY")
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_API_KEY")
    return None


def _default_model(provider: str) -> str:
    """Return a sensible default model name for each provider."""
    defaults = {
        "mock": "mock",
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
    }
    return defaults.get(provider, provider)


def _build_seed(args: argparse.Namespace) -> CreativeSeed:
    """Construct a CreativeSeed from CLI arguments."""
    if args.seed_file:
        path = Path(args.seed_file)
        return load_seed_file(path)

    if not args.diagnosis:
        raise ValueError(
            "Either --seed-file or --diagnosis is required.\nRun with --help for usage."
        )
    return CreativeSeed(
        diagnosis=args.diagnosis,
        difficulty=args.difficulty,
        dramatic_tone=args.tone,
    )


def _build_config(args: argparse.Namespace) -> ModelConfig:
    """Construct a ModelConfig from CLI arguments."""
    provider = Provider(args.provider)
    model = args.model or _default_model(args.provider)
    api_key = _resolve_api_key(args)
    schema_path = args.schema_path

    return ModelConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        schema_path=schema_path,
    )


def _print_result_summary(
    result: object,
    no_save: bool,
) -> None:
    """Print a human-readable result summary to stdout."""
    from anamnesis.result import GenerationResult  # local import to avoid circularity

    assert isinstance(result, GenerationResult)

    sep = "─" * 60
    print(sep)
    if result.success:
        print(f"✓ SUCCESS  (attempts: {result.attempts})")
        print(f"  Diagnosis : {result.seed.diagnosis}")
        print(f"  Difficulty: {result.seed.difficulty}")
        if result.case_path:
            print(f"  Saved to  : {result.case_path}")
        elif no_save:
            print("  (--no-save: case not written to disk)")
    else:
        print(f"✗ FAILED   (attempts: {result.attempts})")
        print(f"  Diagnosis : {result.seed.diagnosis}")
        print(f"  Errors ({len(result.errors)}):")
        for err in result.errors[:10]:
            print(f"    • {err}")
        if len(result.errors) > 10:
            print(f"    … and {len(result.errors) - 10} more errors")
    print(sep)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if args.command == "generate":
        try:
            seed = _build_seed(args)
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        try:
            config = _build_config(args)
        except ValueError as e:
            print(f"Config error: {e}", file=sys.stderr)
            return 1

        output_dir = Path(args.output_dir) if args.output_dir else None

        try:
            pipeline = CaseGenerationPipeline(config, output_dir=output_dir)
        except Exception as e:  # noqa: BLE001
            print(f"Pipeline init error: {e}", file=sys.stderr)
            return 1

        try:
            result = pipeline.generate(seed, max_retries=args.max_retries)
        except Exception as e:  # noqa: BLE001
            print(f"Generation error: {e}", file=sys.stderr)
            return 1

        if result.success and not args.no_save:
            try:
                path = pipeline.save(result)
                from anamnesis.result import _with_path  # noqa: PLC0415

                result = _with_path(result, path)
            except OSError as e:
                print(f"Save error: {e}", file=sys.stderr)
                return 1

        _print_result_summary(result, no_save=args.no_save)
        return 0 if result.success else 1

    # Unreachable due to required=True subparsers, but satisfies type checker
    return 1  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
