"""Stable transcoding presets shared by API, worker and UI contract."""

PROFILES = {
    "strong_720p": {
        "label": "Сильно · 720p",
        "width": 1280,
        "height": 720,
        "crf": 27,
        "audio_bitrate": "96k",
    },
    "standard_1080p": {
        "label": "Стандартно · 1080p",
        "width": 1920,
        "height": 1080,
        "crf": 23,
        "audio_bitrate": "128k",
    },
    "light_1440p": {
        "label": "Легко · 1440p",
        "width": 2560,
        "height": 1440,
        "crf": 20,
        "audio_bitrate": "160k",
    },
}
