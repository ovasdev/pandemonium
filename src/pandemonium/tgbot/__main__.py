"""Allow running as `python -m pandemonium.tgbot`."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from pandemonium.tgbot.main import cli

cli()
