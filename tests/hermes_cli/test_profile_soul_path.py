"""SOUL.md writers must stay inside the resolved profile directory.

``confined_profile_file`` is the shared gate used by PUT /api/profiles/{name}/soul
and ``profiles.configure``. A crafted filename (``../``, nested paths) must
raise before any write; a valid ``SOUL.md`` resolves under the profile dir.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.profiles import confined_profile_file


class TestConfinedProfileFile:
    def test_soul_resolves_inside_the_profile_dir(self, tmp_path: Path):
        soul = confined_profile_file(tmp_path, "SOUL.md")

        assert soul == (tmp_path / "SOUL.md").resolve()
        assert soul.parent == tmp_path.resolve()

    @pytest.mark.parametrize(
        "filename",
        ["../SOUL.md", "..", ".", "subdir/SOUL.md", "a\\b", "", "../etc/passwd"],
    )
    def test_escape_names_are_rejected(self, tmp_path: Path, filename: str):
        with pytest.raises(ValueError, match="Invalid profile file name|outside the profile"):
            confined_profile_file(tmp_path, filename)

    def test_rejected_name_does_not_create_a_file(self, tmp_path: Path):
        with pytest.raises(ValueError):
            confined_profile_file(tmp_path, "../SOUL.md")

        assert list(tmp_path.iterdir()) == []
        assert not (tmp_path.parent / "SOUL.md").exists()
