-- HYBRID stores TOP-15 DINO candidates (v3.3/v3.5 reranking). The old check
-- allowed only ranks 1..5, so every FORCE_RERUN with rank 6 failed.
ALTER TABLE public.dino_candidates
    DROP CONSTRAINT IF EXISTS dino_candidates_rank_check;

ALTER TABLE public.dino_candidates
    ADD CONSTRAINT dino_candidates_rank_check
    CHECK (rank >= 1 AND rank <= 15);
