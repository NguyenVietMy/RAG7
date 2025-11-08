-- Create chats table to store chat sessions
CREATE TABLE IF NOT EXISTS public.chats (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title text NOT NULL,
    collection_name text,  -- Optional: which knowledge base collection to use
    created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    last_message_at timestamp with time zone,
    message_count int DEFAULT 0,
    is_archived boolean DEFAULT FALSE,
    title_refined boolean DEFAULT FALSE  -- Flag to track if title was AI-generated
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON public.chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_user_updated ON public.chats(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_last_message ON public.chats(user_id, last_message_at DESC) WHERE is_archived = FALSE;
CREATE INDEX IF NOT EXISTS idx_chats_collection_name ON public.chats(collection_name) WHERE collection_name IS NOT NULL;

-- Enable RLS
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for chats
DO $$
BEGIN
    -- Policy to allow users to view their own chats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'chats' 
        AND policyname = 'Users can view own chats'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can view own chats" ON public.chats
                FOR SELECT USING (auth.uid()::text = user_id::text)';
    END IF;

    -- Policy to allow users to insert their own chats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'chats' 
        AND policyname = 'Users can insert own chats'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can insert own chats" ON public.chats
                FOR INSERT WITH CHECK (auth.uid()::text = user_id::text)';
    END IF;

    -- Policy to allow users to update their own chats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'chats' 
        AND policyname = 'Users can update own chats'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can update own chats" ON public.chats
                FOR UPDATE USING (auth.uid()::text = user_id::text)';
    END IF;

    -- Policy to allow users to delete their own chats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'chats' 
        AND policyname = 'Users can delete own chats'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can delete own chats" ON public.chats
                FOR DELETE USING (auth.uid()::text = user_id::text)';
    END IF;
END
$$;

-- Create messages table to store chat messages
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
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for messages
DO $$
BEGIN
    -- Policy to allow users to view messages from their own chats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'messages' 
        AND policyname = 'Users can view own messages'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can view own messages" ON public.messages
                FOR SELECT USING (
                    EXISTS (
                        SELECT 1 FROM public.chats 
                        WHERE chats.id = messages.chat_id 
                        AND chats.user_id::text = auth.uid()::text
                    )
                )';
    END IF;

    -- Policy to allow users to insert messages to their own chats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'messages' 
        AND policyname = 'Users can insert own messages'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can insert own messages" ON public.messages
                FOR INSERT WITH CHECK (
                    EXISTS (
                        SELECT 1 FROM public.chats 
                        WHERE chats.id = messages.chat_id 
                        AND chats.user_id::text = auth.uid()::text
                    )
                )';
    END IF;

    -- Policy to allow users to update messages in their own chats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'messages' 
        AND policyname = 'Users can update own messages'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can update own messages" ON public.messages
                FOR UPDATE USING (
                    EXISTS (
                        SELECT 1 FROM public.chats 
                        WHERE chats.id = messages.chat_id 
                        AND chats.user_id::text = auth.uid()::text
                    )
                )';
    END IF;

    -- Policy to allow users to delete messages from their own chats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'messages' 
        AND policyname = 'Users can delete own messages'
    ) THEN
        EXECUTE 'CREATE POLICY "Users can delete own messages" ON public.messages
                FOR DELETE USING (
                    EXISTS (
                        SELECT 1 FROM public.chats 
                        WHERE chats.id = messages.chat_id 
                        AND chats.user_id::text = auth.uid()::text
                    )
                )';
    END IF;
END
$$;

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

