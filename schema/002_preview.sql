CREATE TABLE photo_previews (
    photo_id          TEXT PRIMARY KEY
                      REFERENCES photos(photo_id)
                      ON DELETE CASCADE,

    small_path        TEXT NOT NULL,
    middle_path       TEXT NOT NULL,

    small_width       INTEGER NOT NULL,
    small_height      INTEGER NOT NULL,

    middle_width      INTEGER NOT NULL,
    middle_height     INTEGER NOT NULL,

    small_created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    middle_created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
