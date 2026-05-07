from __future__ import annotations

from scripts.sync_readme_gallery import (
    END_MARKER,
    START_MARKER,
    build_gallery,
    replace_gallery_block,
)


def test_build_gallery_uses_grouped_screenshot_paths() -> None:
    gallery = build_gallery()

    assert "docs/screenshots/readme/v3-login.png" in gallery
    assert "docs/screenshots/webui/webui-admin.png" in gallery
    assert "docs/screenshots/v3-login.png" not in gallery


def test_replace_gallery_block_swaps_only_marker_region() -> None:
    source = f"before\n{START_MARKER}\nold\n{END_MARKER}\nafter\n"

    updated = replace_gallery_block(source, "new-gallery")

    assert updated == f"before\n{START_MARKER}\nnew-gallery\n{END_MARKER}\nafter\n"
