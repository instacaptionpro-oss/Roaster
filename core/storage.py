"""
core/storage.py
===============
Cloudinary uploads for roast cards + battle cards.
Both stored permanently, delivered via CDN.
"""

import os, time
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "ddjoodecx"),
    api_key    = os.getenv("CLOUDINARY_API_KEY",    "738511258157834"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "xJKGug_zL3qlXKfXuT3litta2oM"),
    secure     = True
)


def upload_roast_card(image_bytes, session_id="anon") -> str:
    """
    Upload roast card (BytesIO or bytes) to Cloudinary.
    Returns secure CDN URL.
    """
    result = cloudinary.uploader.upload(
        image_bytes,
        folder        = "roaster-ai/roasts",
        public_id     = f"roast_{session_id}_{int(time.time())}",
        overwrite     = True,
        resource_type = "image",
        transformation = [
            {"quality": "auto:good"},
            {"fetch_format": "auto"}
        ]
    )
    return result["secure_url"]


def upload_battle_card(file_path: str, battle_id: str) -> str:
    """
    Upload battle result card (file path) to Cloudinary.
    Deletes temp file after upload.
    Returns secure CDN URL.
    """
    result = cloudinary.uploader.upload(
        file_path,
        folder        = "roaster-ai/battles",
        public_id     = f"battle_{battle_id}",
        overwrite     = True,
        resource_type = "image",
        transformation = [
            {"quality": "auto:best"},
            {"fetch_format": "auto"}
        ]
    )
    try:
        os.remove(file_path)
    except:
        pass
    return result["secure_url"]
