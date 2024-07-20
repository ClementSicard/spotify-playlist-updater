"""This module contains the class for the Spotify client."""

import os
from pathlib import Path

from typing import Any

import spotipy
from dotenv import load_dotenv
from loguru import logger


DEFAULT_ENV_PATH = Path(__file__).parent.parent / ".env"

SCOPES = {
    "playlist-read-private",
    "playlist-modify-private",
    "playlist-modify-public",
    "playlist-read-collaborative",
}

MAX_QUERY_LIMIT = 50


class AutoUpdater:
    """Class for the Spotify client."""

    def __init__(self, env_path: Path = DEFAULT_ENV_PATH) -> None:
        """Initialize the Spotify client."""
        self._env_path = env_path
        self._setup_client()
        self.current_user = self.client.me()
        if not self.current_user:
            raise RuntimeError("Could not get the current user.")

        logger.success(f"Client created for user '{self.current_user['id']}'")

    def _setup_client(self) -> None:
        """Setup the client with the environment variables."""
        if not self._env_path.exists():
            raise FileNotFoundError(f"Environment file not found at {self._env_path}")
        load_dotenv(self._env_path)
        self._assert_env_var_set()
        scopes = self._get_client_scopes()

        # The client is created with the environment variables
        self.client = spotipy.Spotify(auth_manager=spotipy.SpotifyOAuth(scope=scopes))

    def _assert_env_var_set(self) -> None:
        """Assert that the environment variables are set."""
        var_names = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]
        for var in var_names:
            if not os.getenv(var):
                raise RuntimeError(f"{var} not set.")

    def _get_client_scopes(self) -> str:
        """Get the scopes for the client.

        Returns a string concatenation of the scopes, separated by a space.

        Returns:
            str: The well-formatted scopes for the client.
        """
        return " ".join(SCOPES)

    def get_user_playlists(self, limit: int = MAX_QUERY_LIMIT) -> list[dict[str, Any]]:
        """Get the user's playlists.

        Args:
            limit (int): The number of playlists to get. Defaults to MAX_QUERY_LIMIT.

        Returns:
            list[dict[str, Any]]: The user's playlists.
        """
        if limit > MAX_QUERY_LIMIT:
            raise ValueError("The limit must be less than or equal to 50.")
        playlists = []
        offset = 0
        total = float("inf")
        while offset < total:
            response = self.client.current_user_playlists(limit=limit, offset=offset)
            if response is None:
                raise ValueError("Could not get the user's playlists.")
            total = response["total"]
            offset += limit
            playlists.extend(response["items"])

        return playlists
