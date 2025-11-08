-- Create chats and messages tables without user_id dependency
-- This migration creates the final schema directly

-- Create chats table (without user_id)
CREATE TABLE IF NOT EXISTS public.chats (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    collection_name text,  -- Optional: which knowledge base collection to use
    created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    last_message_at timestamp with time zone,
    message_count int DEFAULT 0,
    is_archived boolean DEFAULT FALSE,
    title_refined boolean DEFAULT FALSE  -- Flag to track if title was AI-generated
);

-- Create indexes for chats
CREATE INDEX IF NOT EXISTS idx_chats_updated ON public.chats(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_last_message ON public.chats(last_message_at DESC) WHERE is_archived = FALSE;
CREATE INDEX IF NOT EXISTS idx_chats_collection_name ON public.chats(collection_name) WHERE collection_name IS NOT NULL;

-- Create messages table
CREATE TABLE IF NOT EXISTS public.messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id uuid NOT NULL REFERENCES public.chats(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content text NOT NULL,
    tokens_used int,  -- For cost tracking
    created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Create indexes for messages
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON public.messages(chat_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON public.messages(created_at);

-- Enable RLS
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (allow all for local app)
DROP POLICY IF EXISTS "Allow all for local app" ON public.chats;
CREATE POLICY "Allow all for local app" ON public.chats
    FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all for local app" ON public.messages;
CREATE POLICY "Allow all for local app" ON public.messages
    FOR ALL USING (true) WITH CHECK (true);

-- Function to update chat's updated_at and last_message_at
CREATE OR REPLACE FUNCTION public.update_chat_on_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.chats
    SET 
        updated_at = timezone('utc'::text, now()),
        last_message_at = timezone('utc'::text, now()),
        message_count = (
            SELECT COUNT(*) FROM public.messages 
            WHERE chat_id = NEW.chat_id
        )
    WHERE id = NEW.chat_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update chat metadata when message is inserted
DROP TRIGGER IF EXISTS update_chat_on_message_insert ON public.messages;
CREATE TRIGGER update_chat_on_message_insert
    AFTER INSERT ON public.messages
    FOR EACH ROW
    EXECUTE FUNCTION public.update_chat_on_message();

-- Function to update updated_at timestamp for chats
CREATE OR REPLACE FUNCTION public.update_chats_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at for chats
DROP TRIGGER IF EXISTS update_chats_updated_at ON public.chats;
CREATE TRIGGER update_chats_updated_at
    BEFORE UPDATE ON public.chats
    FOR EACH ROW
    EXECUTE FUNCTION public.update_chats_updated_at();

