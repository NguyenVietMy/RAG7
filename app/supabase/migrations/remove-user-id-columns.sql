-- Remove user_id columns from tables for local app (no multi-user support needed)

-- Drop triggers and indexes on user_rag_settings before dropping table
DROP TRIGGER IF EXISTS update_user_rag_settings_timestamp ON public.user_rag_settings;
DROP INDEX IF EXISTS idx_user_rag_settings_user_id;

-- Drop RLS policies on user_rag_settings
DROP POLICY IF EXISTS "Users can view own RAG settings" ON public.user_rag_settings;
DROP POLICY IF EXISTS "Users can insert own RAG settings" ON public.user_rag_settings;
DROP POLICY IF EXISTS "Users can update own RAG settings" ON public.user_rag_settings;
DROP POLICY IF EXISTS "Users can delete own RAG settings" ON public.user_rag_settings;

-- Remove user_id from chats table (CASCADE will handle foreign key constraint)
ALTER TABLE public.chats DROP COLUMN IF EXISTS user_id CASCADE;

-- Drop user_rag_settings table and recreate as rag_settings (single config for local app)
DROP TABLE IF EXISTS public.user_rag_settings CASCADE;

CREATE TABLE IF NOT EXISTS public.rag_settings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    rag_n_results int NOT NULL DEFAULT 3,
    rag_similarity_threshold float NOT NULL DEFAULT 0.0,
    rag_max_context_tokens int NOT NULL DEFAULT 2000,
    created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Insert default config if none exists
INSERT INTO public.rag_settings (rag_n_results, rag_similarity_threshold, rag_max_context_tokens)
SELECT 3, 0.0, 2000
WHERE NOT EXISTS (SELECT 1 FROM public.rag_settings);

-- Enable RLS (but allow all for local app)
ALTER TABLE public.rag_settings ENABLE ROW LEVEL SECURITY;

-- Allow all operations for local app
DROP POLICY IF EXISTS "Allow all for local app" ON public.rag_settings;
CREATE POLICY "Allow all for local app" ON public.rag_settings
    FOR ALL USING (true) WITH CHECK (true);

-- Create trigger to update updated_at timestamp for rag_settings
CREATE OR REPLACE FUNCTION public.update_rag_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_rag_settings_updated_at ON public.rag_settings;
CREATE TRIGGER update_rag_settings_updated_at
    BEFORE UPDATE ON public.rag_settings
    FOR EACH ROW
    EXECUTE FUNCTION public.update_rag_settings_updated_at();

-- Update indexes for chats (remove user_id indexes)
DROP INDEX IF EXISTS idx_chats_user_id;
DROP INDEX IF EXISTS idx_chats_user_updated;
DROP INDEX IF EXISTS idx_chats_last_message;

-- Create new indexes without user_id
CREATE INDEX IF NOT EXISTS idx_chats_updated ON public.chats(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_last_message ON public.chats(last_message_at DESC) WHERE is_archived = FALSE;

-- Update RLS policies for chats (allow all for local app)
DROP POLICY IF EXISTS "Users can view own chats" ON public.chats;
DROP POLICY IF EXISTS "Users can insert own chats" ON public.chats;
DROP POLICY IF EXISTS "Users can update own chats" ON public.chats;
DROP POLICY IF EXISTS "Users can delete own chats" ON public.chats;

CREATE POLICY "Allow all for local app" ON public.chats
    FOR ALL USING (true) WITH CHECK (true);

-- Update RLS policies for messages (allow all for local app)
DROP POLICY IF EXISTS "Users can view own messages" ON public.messages;
DROP POLICY IF EXISTS "Users can insert own messages" ON public.messages;
DROP POLICY IF EXISTS "Users can update own messages" ON public.messages;
DROP POLICY IF EXISTS "Users can delete own messages" ON public.messages;

CREATE POLICY "Allow all for local app" ON public.messages
    FOR ALL USING (true) WITH CHECK (true);

-- Drop users table (no longer needed for local app)
-- Note: This should be done after dropping foreign key constraints
DROP TABLE IF EXISTS public.users CASCADE;

