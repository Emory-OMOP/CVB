-- public.vocabulary definition

-- Drop table

-- DROP TABLE omop.vocabulary;

--DROP TABLE public.vocabulary;
CREATE TABLE IF NOT EXISTS public.vocabulary
(
	vocabulary_id VARCHAR(20)   ENCODE lzo
	,vocabulary_name VARCHAR(255)   ENCODE lzo
	,vocabulary_reference VARCHAR(255)   ENCODE lzo
	,vocabulary_version VARCHAR(255)   ENCODE lzo
	,vocabulary_concept_id INTEGER   ENCODE az64
)
DISTSTYLE AUTO
;
