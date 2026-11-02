-- Full sort reset hides current verdicts instead of deleting them.
-- Address lookups use status='DONE'; SUPERSEDED rows remain as history and
-- disappear from the address column until a new HYBRID run finishes.

ALTER TABLE public.hybrid_results
    DROP CONSTRAINT IF EXISTS hybrid_results_status_check;

ALTER TABLE public.hybrid_results
    ADD CONSTRAINT hybrid_results_status_check
    CHECK (status IN ('DONE', 'FAILED', 'SUPERSEDED'));

-- DINO fallback also feeds the address column while HYBRID has no verdict.
-- Old DINO runs must be hidden too, otherwise the address reappears from them
-- immediately after the HYBRID rows are superseded.
ALTER TABLE public.dino_runs
    DROP CONSTRAINT IF EXISTS dino_runs_status_check;

ALTER TABLE public.dino_runs
    ADD CONSTRAINT dino_runs_status_check
    CHECK (status IN ('PENDING', 'RUNNING', 'DONE', 'FAILED', 'SUPERSEDED'));

-- Rollback (only after making sure a new verdict exists for each photo):
-- UPDATE public.hybrid_results SET status = 'DONE' WHERE status = 'SUPERSEDED';
-- ALTER TABLE public.hybrid_results DROP CONSTRAINT hybrid_results_status_check;
-- ALTER TABLE public.hybrid_results
--     ADD CONSTRAINT hybrid_results_status_check
--     CHECK (status IN ('DONE', 'FAILED'));
-- UPDATE public.dino_runs SET status = 'DONE' WHERE status = 'SUPERSEDED';
-- ALTER TABLE public.dino_runs DROP CONSTRAINT dino_runs_status_check;
-- ALTER TABLE public.dino_runs
--     ADD CONSTRAINT dino_runs_status_check
--     CHECK (status IN ('PENDING', 'RUNNING', 'DONE', 'FAILED'));
