CREATE TABLE photos (
    photo_id         TEXT PRIMARY KEY,

    source_path      TEXT NOT NULL,
    filename         TEXT NOT NULL,

    sha256           CHAR(64) NOT NULL UNIQUE,

    container_format TEXT NOT NULL,
    frame_count      INTEGER NOT NULL,

    width            INTEGER NOT NULL,
    height           INTEGER NOT NULL,

    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
