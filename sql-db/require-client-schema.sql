\set ON_ERROR_STOP on

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_catalog.pg_class AS object
    JOIN pg_catalog.pg_namespace AS namespace
      ON namespace.oid = object.relnamespace
    WHERE namespace.nspname = 'public'
      AND object.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
  ) THEN
    RAISE EXCEPTION
      'public still contains relations; migrate them before enabling the client schema guardrail';
  END IF;
END
$$;

-- Fail closed when a client omits its service-specific schema. Clients must
-- override this default with a connection-level search_path.
ALTER ROLE services IN DATABASE services SET search_path TO '';
