-- Create document_summaries table to store hierarchical document summaries
-- Used for cost-efficient document summarization and enhanced RAG queries

CREATE TABLE IF NOT EXISTS public.document_summaries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_name text NOT NULL,
    filename text NOT NULL,
    summary text NOT NULL,
    chunks_processed int,
    llm_calls_made int,
    model_used text,
    created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
    UNIQUE(collection_name, filename)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_document_summaries_lookup 
    ON public.document_summaries(collection_name, filename);

-- Create index for collection queries
CREATE INDEX IF NOT EXISTS idx_document_summaries_collection 
    ON public.document_summaries(collection_name);

-- Enable RLS (but allow all for local app)
ALTER TABLE public.document_summaries ENABLE ROW LEVEL SECURITY;

-- Allow all operations for local app
DROP POLICY IF EXISTS "Allow all for local app" ON public.document_summaries;
CREATE POLICY "Allow all for local app" ON public.document_summaries
    FOR ALL USING (true) WITH CHECK (true);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_document_summaries_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_document_summaries_updated_at ON public.document_summaries;
CREATE TRIGGER update_document_summaries_updated_at
    BEFORE UPDATE ON public.document_summaries
    FOR EACH ROW
    EXECUTE FUNCTION public.update_document_summaries_updated_at();

