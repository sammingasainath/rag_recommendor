-- Add additional duration fields to the assessments table
ALTER TABLE public.assessments 
  ADD COLUMN duration_min_minutes INTEGER NULL,
  ADD COLUMN duration_max_minutes INTEGER NULL,
  ADD COLUMN is_untimed BOOLEAN DEFAULT FALSE,
  ADD COLUMN is_variable_duration BOOLEAN DEFAULT FALSE;

-- Update existing data (using PL/pgSQL function for regex and conditionals)
CREATE OR REPLACE FUNCTION public.update_duration_fields()
RETURNS void AS $$
DECLARE
    assessment_record RECORD;
BEGIN
    FOR assessment_record IN SELECT id, duration_text FROM public.assessments LOOP
        -- Handle numeric values
        IF assessment_record.duration_text ~ '^\d+$' THEN
            UPDATE public.assessments 
            SET 
                duration_min_minutes = assessment_record.duration_text::integer,
                duration_max_minutes = assessment_record.duration_text::integer
            WHERE id = assessment_record.id;
            
        -- Handle max values
        ELSIF assessment_record.duration_text ~* '^\s*max\s+(\d+)\s*$' THEN
            UPDATE public.assessments 
            SET 
                duration_max_minutes = (regexp_matches(assessment_record.duration_text, 'max\s+(\d+)', 'i'))[1]::integer
            WHERE id = assessment_record.id;
            
        -- Handle range values (e.g., "15 to 35")
        ELSIF assessment_record.duration_text ~* '^\s*(\d+)\s+to\s+(\d+)\s*$' THEN
            UPDATE public.assessments 
            SET 
                duration_min_minutes = (regexp_matches(assessment_record.duration_text, '(\d+)\s+to', 'i'))[1]::integer,
                duration_max_minutes = (regexp_matches(assessment_record.duration_text, 'to\s+(\d+)', 'i'))[1]::integer
            WHERE id = assessment_record.id;
            
        -- Handle "Untimed"
        ELSIF assessment_record.duration_text ~* '^\s*untimed' THEN
            UPDATE public.assessments 
            SET is_untimed = TRUE
            WHERE id = assessment_record.id;
            
        -- Handle variable/TBC/etc.
        ELSIF assessment_record.duration_text ~* '^\s*(variable|tbc|n/a|-)\s*$' THEN
            UPDATE public.assessments 
            SET is_variable_duration = TRUE
            WHERE id = assessment_record.id;
            
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Execute the function
SELECT public.update_duration_fields(); 