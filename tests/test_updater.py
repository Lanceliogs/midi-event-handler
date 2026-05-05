"""Tests for updater module."""

import pytest
from unittest.mock import patch, MagicMock

from midi_event_handler.tools.updater import FILENAME_PATTERN, get_latest_release_asset


@pytest.mark.parametrize(
    "filename",
    [
        "meh-0.5.1-setup.exe",
        "meh-v0.5.1-setup.exe",
        "meh-0.5.1.40f8b6b-setup.exe",
        "meh-v0.5.1.40f8b6b-setup.exe",
        "meh-0.5.1.40f8b6b.dirty-setup.exe",
        "meh-v0.5.1.40f8b6b.dirty-setup.exe",
        "meh-1.0.0-setup.exe",
        "meh-v1.0.0-setup.exe",
        "midi-event-handler-setup_0.5.0.exe",
        "midi-event-handler-setup_v0.5.0.exe",
        "midi-event-handler-setup_1.2.3-beta.exe",
        "midi-event-handler-setup_v1.2.3-beta.exe",
    ],
)
def test_filename_pattern_matches(filename):
    assert FILENAME_PATTERN.fullmatch(filename)


@pytest.mark.parametrize(
    "filename",
    [
        "meh-setup.exe",
        "other-app-0.5.1-setup.exe",
        "meh-0.5.1-setup.msi",
        "meh-0.5.1.exe",
        "readme.txt",
    ],
)
def test_filename_pattern_rejects(filename):
    assert not FILENAME_PATTERN.fullmatch(filename)


class TestGetLatestReleaseAsset:
    """Tests for GitHub release API integration."""

    MOCK_RELEASES = [
        {
            "tag_name": "v1.0.0",
            "prerelease": False,
            "body": "Release notes for 1.0.0",
            "assets": [
                {"name": "meh-1.0.0-setup.exe", "browser_download_url": "https://example.com/meh-1.0.0-setup.exe"}
            ],
        },
        {
            "tag_name": "v0.9.0",
            "prerelease": False,
            "body": "Release notes for 0.9.0",
            "assets": [
                {"name": "meh-0.9.0-setup.exe", "browser_download_url": "https://example.com/meh-0.9.0-setup.exe"}
            ],
        },
        {
            "tag_name": "v2.0.0-beta",
            "prerelease": True,
            "body": "Beta notes",
            "assets": [
                {"name": "meh-2.0.0-beta-setup.exe", "browser_download_url": "https://example.com/beta.exe"}
            ],
        },
    ]

    def _mock_response(self, releases):
        resp = MagicMock()
        resp.json.return_value = releases
        resp.raise_for_status = MagicMock()
        return resp

    @patch("midi_event_handler.tools.updater.get_updates_config", return_value={"prereleases": False})
    @patch("midi_event_handler.tools.updater.requests.get")
    def test_finds_newer_version(self, mock_get, _):
        mock_get.return_value = self._mock_response(self.MOCK_RELEASES)
        result = get_latest_release_asset("v0.5.0")

        assert result is not None
        url, name, tag, notes = result
        assert tag == "v1.0.0"
        assert "meh-1.0.0-setup.exe" in name

    @patch("midi_event_handler.tools.updater.get_updates_config", return_value={"prereleases": False})
    @patch("midi_event_handler.tools.updater.requests.get")
    def test_no_newer_version(self, mock_get, _):
        mock_get.return_value = self._mock_response(self.MOCK_RELEASES)
        result = get_latest_release_asset("v1.0.0")

        assert result is None

    @patch("midi_event_handler.tools.updater.get_updates_config", return_value={"prereleases": False})
    @patch("midi_event_handler.tools.updater.requests.get")
    def test_skips_prereleases(self, mock_get, _):
        mock_get.return_value = self._mock_response(self.MOCK_RELEASES)
        result = get_latest_release_asset("v1.5.0")

        assert result is None

    @patch("midi_event_handler.tools.updater.get_updates_config", return_value={"prereleases": True})
    @patch("midi_event_handler.tools.updater.requests.get")
    def test_includes_prereleases(self, mock_get, _):
        mock_get.return_value = self._mock_response(self.MOCK_RELEASES)
        result = get_latest_release_asset("v1.5.0")

        assert result is not None
        _, _, tag, _ = result
        assert tag == "v2.0.0-beta"

    @patch("midi_event_handler.tools.updater.get_updates_config", return_value={"prereleases": False})
    @patch("midi_event_handler.tools.updater.requests.get")
    def test_empty_releases(self, mock_get, _):
        mock_get.return_value = self._mock_response([])
        result = get_latest_release_asset("v0.1.0")

        assert result is None

    @patch("midi_event_handler.tools.updater.get_updates_config", return_value={"prereleases": False})
    @patch("midi_event_handler.tools.updater.requests.get")
    def test_handles_null_body(self, mock_get, _):
        releases = [
            {
                "tag_name": "v2.0.0",
                "prerelease": False,
                "body": None,
                "assets": [
                    {"name": "meh-2.0.0-setup.exe", "browser_download_url": "https://example.com/meh-2.0.0-setup.exe"}
                ],
            }
        ]
        mock_get.return_value = self._mock_response(releases)
        result = get_latest_release_asset("v0.1.0")

        assert result is not None
        _, _, tag, notes = result
        assert tag == "v2.0.0"
        assert notes == ""

    @patch("midi_event_handler.tools.updater.get_updates_config", return_value={"prereleases": False})
    @patch("midi_event_handler.tools.updater.requests.get")
    def test_skips_release_without_matching_asset(self, mock_get, _):
        releases = [
            {
                "tag_name": "v2.0.0",
                "prerelease": False,
                "body": "No exe",
                "assets": [{"name": "readme.txt", "browser_download_url": "https://example.com/readme.txt"}],
            }
        ]
        mock_get.return_value = self._mock_response(releases)
        result = get_latest_release_asset("v0.1.0")

        assert result is None
