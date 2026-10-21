"""Background billboard branch: detect billboards, crop them, run QWEN.

One photo may show two comparable side-by-side billboards: each becomes its
own crop and QWEN call, then the results are merged into one photo_qwen row.
Runs only in the deferred worker (BILLBOARD_DETECT; the QWEN_PHOTO job takes
the crops as its input) and is independent from INGEST, DINO, HYBRID and the
full-frame QWEN_PHOTO fallback.
"""
