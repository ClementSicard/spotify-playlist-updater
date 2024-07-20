"""Main module for the application script."""


from src.client import AutoUpdater
from src.utils import pprint


def main() -> None:
    """Main entry point for the application script."""
    client = AutoUpdater()

    pprint(client.get_user_playlists()[:1])


if __name__ == "__main__":
    main()
