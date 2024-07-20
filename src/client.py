"""This module contains the class for the Spotify client."""

import collections
import os
from pathlib import Path

from typing import Any, Callable

from dotenv import load_dotenv
from loguru import logger
from spotipy import Spotify, SpotifyOAuth
from tqdm import tqdm


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
        self.client = Spotify(auth_manager=SpotifyOAuth(scope=scopes))

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

    def get_user_playlists(self) -> list[dict[str, Any]]:
        """Get the user's playlists.

        Args:
            limit (int): The number of playlists to get. Defaults to MAX_QUERY_LIMIT.

        Returns:
            list[dict[str, Any]]: The user's playlists.
        """
        resp = self._get_all_values(func=self.client.current_user_playlists)

        return [p for p in resp if not self.playlist_is_collaborative(p) and self.playlist_is_from_user(p)]

    def playlist_is_collaborative(self, playlist: dict[str, Any]) -> bool:
        """
        Returns True if the playlist is collaborative.

        Args:
            playlist (dict[str, Any]): The JSON object representing the playlist.

        Returns:
            bool: As above.
        """
        is_collab: bool = playlist["collaborative"]

        return is_collab

    def playlist_is_from_user(self, playlist: dict[str, Any]) -> bool:
        """Returns True if the playlist is owned by the user.

        Args:
            playlist (dict[str, Any]): The JSON object representing the playlist.

        Returns:
            bool: As above.
        """
        return playlist["owner"]["id"] == self.current_user["id"]  # type: ignore

    def get_artist_only_playlists(self, limit: int = MAX_QUERY_LIMIT) -> dict[str, Any]:
        """Get the user's playlists that contain only one artist.

        Args:
            limit (int): The number of playlists to get. Defaults to MAX_QUERY_LIMIT.

        Returns:
            dict[str, Any]: The user's playlists that contain only one artist.
        """
        playlists = self.get_user_playlists()
        artist_only_playlists: dict[str, Any] = collections.defaultdict(list)
        for playlist in tqdm(
            playlists,
            desc="Filtering for artist-only...",
            total=len(playlists),
        ):
            is_artist_only, unique_artist = self._is_artist_only_playlist(playlist)
            if is_artist_only:
                artist_only_playlists[unique_artist].append(playlist)  # type: ignore

        # If for a certain artist, there are multiple playlists with them only,
        # then we select the largest one.
        for artist in artist_only_playlists:
            artist_only_playlists[artist] = max(
                artist_only_playlists[artist],
                key=lambda p: p["tracks"]["total"],  # type: ignore
            )

        return artist_only_playlists

    def _get_all_values(
        self,
        func: Callable[..., Any],
        limit: int = MAX_QUERY_LIMIT,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Exhausts an iterator to get all values of a function call to Spotify API.

        Args:
            func (Callable): The function to call many times
            limit (int, optional): The max number of elements to return in a single query.
            Defaults to MAX_QUERY_LIMIT.

        Raises:
            ValueError: If the limit is larger than MAX_QUERY_LIMIT.
            ValueError: If a response to the query is None.

        Returns:
            list[dict[str, Any]]: The full list of returned values.
        """
        if limit > MAX_QUERY_LIMIT:
            raise ValueError("The limit must be less than or equal to 50.")
        values = []
        offset = 0
        total = float("inf")
        while offset < total:
            response = func(limit=limit, offset=offset, **kwargs)
            if response is None:
                raise ValueError(f"Error while running {func.__qualname__}")
            total = response["total"]
            offset += limit
            values.extend(response["items"])

        return values

    def _is_artist_only_playlist(self, playlist: dict[str, Any], threshold: float = 0.9) -> tuple[bool, str | None]:
        """Check if the playlist contains only one artist.

        Args:
            playlist (dict[str, Any]): The playlist to check, in a Json format.
            threhsold (float): Percentage of songs from the artists from which we
            consider the playlist to be of a single artist. Defaults to 0.9.

        Returns:
            tuple[bool, str | None]: True if the artist is from only artist, False otherwise,
            and the artist if True, else None.
        """

        id_ = playlist["id"]
        artists_count: dict[str, int] = collections.defaultdict(int)
        albums_count: dict[str, int] = collections.defaultdict(int)

        track_details = self.get_all_playlist_items(playlist_id=id_)

        if track_details is None:
            raise ValueError(f"Could not get the tracks for playlist {id_}.")

        total = len(track_details)
        if total == 0 or total < 15:
            return False, None

        for track_raw in track_details:
            track = track_raw["track"]
            for artist in track["artists"]:
                artists_count[artist["name"]] += 1
            albums_count[track["album"]["name"]] += 1

        # If the playlist was created for a single album, it is not
        # a per-artist playlist.
        if len(albums_count.values()) == 1:
            return False, None

        is_unique_artist = max(artists_count.values()) >= threshold * total
        most_present = max(artists_count, key=artists_count.get)  # type: ignore

        return is_unique_artist, most_present

    def get_all_playlist_items(
        self,
        playlist_id: str,
        fields: str = "total,items(track(artists(name),album.name)",
    ) -> list[dict[str, Any]]:
        """Get all the items in a playlist.

        Args:
            playlist_id (str): The Spotify ID of the playlist.
            fields (str): The fields to get from the playlist.
                Defaults to "total,items(track(artists(name),album.name)".

        Returns:
            list[dict[str, Any]]: The items in the playlist.
        """
        return self._get_all_values(
            func=self.client.playlist_items,
            playlist_id=playlist_id,
            fields=fields,
        )
