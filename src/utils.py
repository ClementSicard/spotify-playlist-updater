"""Utility functions."""
import json

from typing import Sequence, TypeAlias

from loguru import logger


JSON: TypeAlias = dict[str, "JSON"] | Sequence["JSON"] | str | int | float | bool | None


def pprint(data: JSON) -> None:
    """Pretty print the data."""
    logger.info(json.dumps(data, indent=4))
