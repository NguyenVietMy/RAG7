-- Create professionals table to store collection metadata
CREATE TABLE IF NOT EXISTS public.professionals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    collection_name text NOT NULL,
    name text NOT NULL,
    description text,
    created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    UNIQUE(user_id, collection_name)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_professionals_user_id ON public.professionals(user_id);
CREATE INDEX IF NOT EXISTS idx_professionals_collection_name ON public.professionals(collection_name);

-- Enable RLS
ALTER TABLE public.professionals ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
DO $$
BEGIN
    -- Policy to allow users to view their own professionals
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'professionals' 
        AND policyname = 'Users can view own professionals'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can view own professionals" ON public.professionals
                FOR SELECT USING (auth.uid()::text = user_id::text)';
    END IF;

    -- Policy to allow users to insert their own professionals
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'professionals' 
        AND policyname = 'Users can insert own professionals'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can insert own professionals" ON public.professionals
                FOR INSERT WITH CHECK (auth.uid()::text = user_id::text)';
    END IF;

    -- Policy to allow users to update their own professionals
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'professionals' 
        AND policyname = 'Users can update own professionals'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can update own professionals" ON public.professionals
                FOR UPDATE USING (auth.uid()::text = user_id::text)';
    END IF;

    -- Policy to allow users to delete their own professionals
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'professionals' 
        AND policyname = 'Users can delete own professionals'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can delete own professionals" ON public.professionals
                FOR DELETE USING (auth.uid()::text = user_id::text)';
    END IF;
END
$$;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_professionals_updated_at ON public.professionals;
CREATE TRIGGER update_professionals_updated_at
    BEFORE UPDATE ON public.professionals
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

