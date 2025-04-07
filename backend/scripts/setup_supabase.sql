-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pg_net SCHEMA public;

-- Create the assessments table
CREATE TABLE IF NOT EXISTS public.assessments (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT,
    remote_testing BOOLEAN DEFAULT FALSE,
    adaptive_irt BOOLEAN DEFAULT FALSE,
    test_types TEXT[],
    description TEXT,
    job_levels TEXT[],
    duration_text TEXT,
    duration_minutes INTEGER,
    languages TEXT[],
    key_features TEXT[],
    source TEXT,
    embedding public.vector(768),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Update table schema if needed
DO $$
BEGIN
    -- Check if duration_min_minutes exists
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'assessments' AND column_name = 'duration_min_minutes') THEN
        -- Convert duration_min_minutes to duration_minutes
        ALTER TABLE public.assessments ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;
        UPDATE public.assessments SET duration_minutes = duration_min_minutes WHERE duration_minutes IS NULL;
        ALTER TABLE public.assessments DROP COLUMN duration_min_minutes;
    END IF;
    
    -- Check if duration_max_minutes exists
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'assessments' AND column_name = 'duration_max_minutes') THEN
        ALTER TABLE public.assessments DROP COLUMN duration_max_minutes;
    END IF;
    
    -- Check if is_untimed exists
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'assessments' AND column_name = 'is_untimed') THEN
        ALTER TABLE public.assessments DROP COLUMN is_untimed;
    END IF;
    
    -- Check if is_variable_duration exists
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'assessments' AND column_name = 'is_variable_duration') THEN
        ALTER TABLE public.assessments DROP COLUMN is_variable_duration;
    END IF;
END $$;

-- Create function to update timestamp
CREATE OR REPLACE FUNCTION public.trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS set_timestamp ON public.assessments;

-- Create trigger for updating timestamp
CREATE TRIGGER set_timestamp
    BEFORE UPDATE ON public.assessments
    FOR EACH ROW
    EXECUTE FUNCTION public.trigger_set_timestamp();

-- Create indexes
DROP INDEX IF EXISTS idx_assessments_embedding;
DROP INDEX IF EXISTS idx_assessments_job_levels;
DROP INDEX IF EXISTS idx_assessments_test_types;
DROP INDEX IF EXISTS idx_assessments_duration;
DROP INDEX IF EXISTS idx_assessments_languages;

CREATE INDEX IF NOT EXISTS idx_assessments_embedding ON public.assessments USING hnsw (embedding public.vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_assessments_job_levels ON public.assessments USING GIN (job_levels);
CREATE INDEX IF NOT EXISTS idx_assessments_test_types ON public.assessments USING GIN (test_types);
CREATE INDEX IF NOT EXISTS idx_assessments_duration ON public.assessments (duration_minutes);
CREATE INDEX IF NOT EXISTS idx_assessments_languages ON public.assessments USING GIN (languages);

-- Create function to generate embedding input
CREATE OR REPLACE FUNCTION public.assessment_embedding_input(rec assessments)
RETURNS text
LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE AS $$
BEGIN
    RETURN '# ' || rec.name || E'\n\n' ||
           'Description: ' || COALESCE(rec.description, '') || E'\n\n' ||
           'Key Features: ' || array_to_string(COALESCE(rec.key_features, ARRAY[]::text[]), ', ') || E'\n\n' ||
           'Test Types: ' || array_to_string(COALESCE(rec.test_types, ARRAY[]::text[]), ', ') || E'\n\n' ||
           'Job Levels: ' || array_to_string(COALESCE(rec.job_levels, ARRAY[]::text[]), ', ');
END;
$$;

-- Create function for vector similarity search with filters
DROP FUNCTION IF EXISTS public.match_assessments(public.vector, float, int, text[], integer, text[], text[], boolean);
DROP FUNCTION IF EXISTS public.match_assessments(public.vector, float, int);

CREATE OR REPLACE FUNCTION public.match_assessments(
    query_embedding public.vector(768),
    match_threshold float,
    match_count int,
    filter_job_levels text[] DEFAULT NULL,
    filter_max_duration integer DEFAULT NULL,
    filter_test_types text[] DEFAULT NULL,
    filter_languages text[] DEFAULT NULL,
    filter_remote_testing boolean DEFAULT NULL
)
RETURNS TABLE (
    id integer,
    name text,
    url text,
    description text,
    remote_testing boolean,
    adaptive_irt boolean,
    test_types text[],
    job_levels text[],
    duration_text text,
    duration_minutes integer,
    languages text[],
    key_features text[],
    source text,
    similarity float
)
LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT
        a.id,
        a.name,
        a.url,
        a.description,
        a.remote_testing,
        a.adaptive_irt,
        a.test_types,
        a.job_levels,
        a.duration_text,
        a.duration_minutes,
        a.languages,
        a.key_features,
        a.source,
        1 - (a.embedding <=> query_embedding) AS similarity
    FROM public.assessments a
    WHERE a.embedding IS NOT NULL
        AND (1 - (a.embedding <=> query_embedding)) >= match_threshold
        AND (filter_job_levels IS NULL OR a.job_levels && filter_job_levels)
        AND (filter_max_duration IS NULL OR a.duration_minutes <= filter_max_duration)
        AND (filter_test_types IS NULL OR a.test_types && filter_test_types)
        AND (filter_languages IS NULL OR a.languages && filter_languages)
        AND (filter_remote_testing IS NULL OR a.remote_testing = filter_remote_testing)
    ORDER BY similarity DESC
    LIMIT match_count;
$$;

-- Enable RLS (Row Level Security)
ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if exists
DROP POLICY IF EXISTS "Enable read access for all users" ON public.assessments;

-- Create policy for public read access
CREATE POLICY "Enable read access for all users" ON public.assessments
    FOR SELECT
    TO public
    USING (true);
