-- Create user_rag_settings table to store RAG configuration per user
CREATE TABLE IF NOT EXISTS public.user_rag_settings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    rag_n_results integer DEFAULT 3 NOT NULL CHECK (rag_n_results > 0 AND rag_n_results <= 100),
    rag_similarity_threshold double precision DEFAULT 0.0 CHECK (rag_similarity_threshold >= 0.0 AND rag_similarity_threshold <= 1.0),
    rag_max_context_tokens integer DEFAULT 2000 NOT NULL CHECK (rag_max_context_tokens > 0 AND rag_max_context_tokens <= 10000),
    created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    UNIQUE(user_id)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_user_rag_settings_user_id ON public.user_rag_settings(user_id);

-- Enable RLS
ALTER TABLE public.user_rag_settings ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
DO $$
BEGIN
    -- Policy to allow users to view their own settings
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'user_rag_settings' 
        AND policyname = 'Users can view own RAG settings'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can view own RAG settings" ON public.user_rag_settings
                FOR SELECT USING (auth.uid()::text = user_id::text)';
    END IF;

    -- Policy to allow users to insert their own settings
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'user_rag_settings' 
        AND policyname = 'Users can insert own RAG settings'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can insert own RAG settings" ON public.user_rag_settings
                FOR INSERT WITH CHECK (auth.uid()::text = user_id::text)';
    END IF;

    -- Policy to allow users to update their own settings
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'user_rag_settings' 
        AND policyname = 'Users can update own RAG settings'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can update own RAG settings" ON public.user_rag_settings
                FOR UPDATE USING (auth.uid()::text = user_id::text)';
    END IF;

    -- Policy to allow users to delete their own settings
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'user_rag_settings' 
        AND policyname = 'Users can delete own RAG settings'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can delete own RAG settings" ON public.user_rag_settings
                FOR DELETE USING (auth.uid()::text = user_id::text)';
    END IF;
END
$$;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_rag_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_user_rag_settings_timestamp ON public.user_rag_settings;
CREATE TRIGGER update_user_rag_settings_timestamp
    BEFORE UPDATE ON public.user_rag_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_user_rag_settings_updated_at();

