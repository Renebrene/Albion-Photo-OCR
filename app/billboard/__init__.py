"""Background billboard branch: detect a billboard, crop it, run QWEN on the crop.

Runs only in the deferred worker (job types BILLBOARD_DETECT and QWEN_CROP) and
is independent from INGEST, DINO, HYBRID and the full-frame QWEN_PHOTO path.
"""
