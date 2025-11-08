-- Drop professionals table as it is not used for fetching collections
-- Collections are fetched directly from ChromaDB, not from this database table
-- This table was only used for storing metadata that is never read

-- Drop RLS policies first
DROP POLICY IF EXISTS "Users can view own professionals" ON public.professionals;
DROP POLICY IF EXISTS "Users can insert own professionals" ON public.professionals;
DROP POLICY IF EXISTS "Users can update own professionals" ON public.professionals;
DROP POLICY IF EXISTS "Users can delete own professionals" ON public.professionals;

-- Drop the trigger
DROP TRIGGER IF EXISTS update_professionals_updated_at ON public.professionals;

-- Drop indexes explicitly (though CASCADE will handle this)
DROP INDEX IF EXISTS idx_professionals_user_id;
DROP INDEX IF EXISTS idx_professionals_collection_name;

-- Drop the table (CASCADE will handle any remaining dependencies)
DROP TABLE IF EXISTS public.professionals CASCADE;

