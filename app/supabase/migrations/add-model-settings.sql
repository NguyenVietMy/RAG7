-- Add chat model setting to rag_settings table
ALTER TABLE public.rag_settings 
ADD COLUMN IF NOT EXISTS chat_model text DEFAULT 'gpt-4o-mini';

-- Update existing rows with default if they don't have a value
UPDATE public.rag_settings 
SET chat_model = COALESCE(chat_model, 'gpt-4o-mini')
WHERE chat_model IS NULL;

