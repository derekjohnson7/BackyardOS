"""
BackyardOS Advisor Worker

Runs a single local AI analysis cycle.
Scheduling will be handled separately.
"""

import logging
import os
import sys
from datetime import datetime, timezone

# Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-nemo")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("backyardos.advisor")


def run_advisor_cycle():
    """Execute one BackyardOS advisor analysis cycle."""

    started_at = datetime.now(timezone.utc)

    logger.info("Starting BackyardOS advisor cycle")
    logger.info("Model: %s", OLLAMA_MODEL)

    # TODO: Load verified sensor findings
    # TODO: Request an Ollama interpretation
    # TODO: Validate the response
    # TODO: Persist validated insights

    logger.info("Advisor worker initialized")
    logger.info("Cycle started at: %s", started_at.isoformat())


def main():
    try:
        run_advisor_cycle()
    except Exception:
        logger.exception("Advisor cycle failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
