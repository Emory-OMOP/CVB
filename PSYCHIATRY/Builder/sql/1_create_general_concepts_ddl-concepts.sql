-- public.concept definition

-- Drop table

-- DROP TABLE public.concept;

--DROP TABLE public.concept;
CREATE TABLE IF NOT EXISTS public.concept
(
	concept_id INTEGER   ENCODE az64
	,concept_name VARCHAR(255)   ENCODE lzo
	,domain_id VARCHAR(20)   ENCODE lzo
	,vocabulary_id VARCHAR(20)   ENCODE lzo
	,concept_class_id VARCHAR(20)   ENCODE lzo
	,standard_concept VARCHAR(1)   ENCODE lzo
	,concept_code VARCHAR(50)   ENCODE lzo
	,valid_start_date DATE   ENCODE az64
	,valid_end_date DATE   ENCODE az64
	,invalid_reason VARCHAR(1)   ENCODE lzo
)
DISTSTYLE AUTO
;
ALTER TABLE public.concept owner to joan;