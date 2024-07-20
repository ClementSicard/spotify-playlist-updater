import spotipy


class AutoUpdater:

    def __init__(self) -> None:
        self.client = spotipy.Spotify()
