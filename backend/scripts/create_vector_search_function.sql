-- Enable the pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing function
DROP FUNCTION IF EXISTS public.match_assessments(public.vector, float, int, text[], integer, text[], text[], boolean);
DROP FUNCTION IF EXISTS public.match_assessments(public.vector, float, int);

-- Create function for vector similarity search with filters
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

-- Create an index on the embedding column for better performance (if not already exists)
CREATE INDEX IF NOT EXISTS assessments_embedding_idx ON public.assessments USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100); 