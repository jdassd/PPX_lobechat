#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helpers to generate platform icon files (.png / .ico / .icns)
from the project root logo.png into pyapp/icon/.

This keeps the app icons in sync and avoids maintaining
multiple copies of the same artwork.
"""

import os
from typing import Optional

try:
    from PIL import Image
except Exception:  # Pillow not installed or broken
    Image = None  # type: ignore


def _get_paths() -> tuple[str, str, str]:
    """Return (root_dir, icon_dir, root_logo_path)."""
    icon_dir = os.path.dirname(os.path.abspath(__file__))
    pyapp_dir = os.path.dirname(icon_dir)
    root_dir = os.path.dirname(pyapp_dir)
    root_logo = os.path.join(root_dir, "logo.png")
    return root_dir, icon_dir, root_logo


def _open_root_logo(root_logo: str) -> Optional["Image.Image"]:
    """Open the root logo.png if possible."""
    if Image is None:
        print("[icon] Pillow not available, skip icon generation.")
        return None

    if not os.path.exists(root_logo):
        print(f"[icon] Root logo not found, skip icon generation: {root_logo}")
        return None

    try:
        img = Image.open(root_logo)
        # Force RGBA so transparency behaves consistently across formats.
        return img.convert("RGBA")
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[icon] Failed to open root logo {root_logo}: {exc}")
        return None


def _save_png(img: "Image.Image", icon_dir: str) -> None:
    """Generate pyapp/icon/logo.png (Linux, generic PNG)."""
    target = os.path.join(icon_dir, "logo.png")
    try:
        # 128x128 is a common Linux icon size; scale if needed.
        png_img = img.resize((128, 128))
        png_img.save(target, format="PNG")
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[icon] Failed to save PNG icon {target}: {exc}")


def _save_ico(img: "Image.Image", icon_dir: str) -> None:
    """Generate pyapp/icon/logo.ico (Windows installer / exe)."""
    target = os.path.join(icon_dir, "logo.ico")
    try:
        # 256x256 works well for modern Windows icons.
        ico_img = img.resize((256, 256))
        ico_img.save(target, format="ICO")
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[icon] Failed to save ICO icon {target}: {exc}")


def _save_icns(img: "Image.Image", icon_dir: str) -> None:
    """Generate pyapp/icon/logo.icns (macOS app / DMG badge)."""
    target = os.path.join(icon_dir, "logo.icns")
    try:
        # Use a reasonably large size so macOS has room to scale.
        icns_img = img.resize((512, 512))
        icns_img.save(target, format="ICNS")
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[icon] Failed to save ICNS icon {target}: {exc}")


def generate_logo_icons() -> None:
    """
    Generate .png / .ico / .icns icons from the project root logo.png.

    This is inexpensive, so it can be called at the start of build /
    packaging scripts to ensure icons are always up to date.
    """
    _, icon_dir, root_logo = _get_paths()

    if Image is None:
        print("[icon] Pillow not available, skip icon generation.")
        return

    img = _open_root_logo(root_logo)
    if img is None:
        return

    os.makedirs(icon_dir, exist_ok=True)

    _save_png(img, icon_dir)
    _save_ico(img, icon_dir)
    _save_icns(img, icon_dir)

