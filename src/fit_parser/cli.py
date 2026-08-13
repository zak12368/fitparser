"""Command-line interface and entry point for the FIT parser.

Usage:
    python -m fit_parser
    python -m fit_parser --output custom_output.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from fit_parser.logger import get_logger
from fit_parser.parsers import batch_process_directory

logger = get_logger(__name__)


def main() -> None:
    """Main entry point for the FIT parser CLI."""
    parser = argparse.ArgumentParser(
        prog="fit-parser",
        description="Parse Apple Watch Fitness+ .fit files into structured JSON.",
    )
    parser.add_argument(
        "--input",
        "-i",
        default=None,
        help="Directory containing .fit files (overrides FIT_FOLDER env var).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="processed_workouts_final.json",
        help="Output JSON file path (default: processed_workouts_final.json).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    # Load environment variables from .env file (project root = 3 levels up)
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=str(env_path))

    fit_folder = args.input or os.getenv("FIT_FOLDER")
    if not fit_folder:
        logger.error("No input directory specified. Set FIT_FOLDER env var or use --input.")
        sys.exit(1)

    if not os.path.isdir(fit_folder):
        logger.error("Directory not found: %s", fit_folder)
        sys.exit(1)

    all_workouts = batch_process_directory(fit_folder)

    if all_workouts:
        output_path = Path(args.output).resolve()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([w.to_dict() for w in all_workouts], f, indent=4, ensure_ascii=False)
        logger.info("All data saved to %s (%d workouts)", output_path, len(all_workouts))
    else:
        logger.error("No files were processed successfully.")
        sys.exit(1)


if __name__ == "__main__":
    main()
