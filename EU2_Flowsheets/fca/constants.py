"""Clinical dictionaries for FCA attribute extraction.

All pattern matching is deterministic regex + dictionary (no ML)
for reproducibility. Patterns are applied in order; first match wins
within each family.
"""

from __future__ import annotations

import re
from typing import NamedTuple, Optional


class LateralityMatch(NamedTuple):
    laterality: str
    body_region: Optional[str]


# --- Laterality patterns (applied to DISP_NAME) ---
# Order matters: more specific patterns first.
LATERALITY_PATTERNS: list[tuple[re.Pattern, LateralityMatch]] = [
    (re.compile(r'\bRLE\b'),        LateralityMatch('right', 'lower_extremity')),
    (re.compile(r'\bLLE\b'),        LateralityMatch('left',  'lower_extremity')),
    (re.compile(r'\bRUE\b'),        LateralityMatch('right', 'upper_extremity')),
    (re.compile(r'\bLUE\b'),        LateralityMatch('left',  'upper_extremity')),
    (re.compile(r'\bR\s+(?:Leg|Thigh|Knee|Ankle|Foot|Calf)\b', re.I),
                                     LateralityMatch('right', 'lower_extremity')),
    (re.compile(r'\bL\s+(?:Leg|Thigh|Knee|Ankle|Foot|Calf)\b', re.I),
                                     LateralityMatch('left',  'lower_extremity')),
    (re.compile(r'\bR\s+(?:Arm|Hand|Wrist|Elbow|Shoulder)\b', re.I),
                                     LateralityMatch('right', 'upper_extremity')),
    (re.compile(r'\bL\s+(?:Arm|Hand|Wrist|Elbow|Shoulder)\b', re.I),
                                     LateralityMatch('left',  'upper_extremity')),
    (re.compile(r'\bRight\b', re.I), LateralityMatch('right', None)),
    (re.compile(r'\bLeft\b', re.I),  LateralityMatch('left',  None)),
    (re.compile(r'\bBilateral\b', re.I), LateralityMatch('bilateral', None)),
    # Shorthand R/L at start of name (e.g., "R Pedal Pulse")
    (re.compile(r'^R\s'),            LateralityMatch('right', None)),
    (re.compile(r'^L\s'),            LateralityMatch('left',  None)),
]


# --- Body site patterns ---
# Maps regex → canonical body site name.
BODY_SITE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Extremities (specific)
    (re.compile(r'\b(?:RLE|LLE|[RL]\s*(?:Leg|Thigh|Knee|Ankle|Foot|Calf)|Lower\s+Extrem)', re.I),
     'lower_extremity'),
    (re.compile(r'\b(?:RUE|LUE|[RL]\s*(?:Arm|Hand|Wrist|Elbow|Shoulder)|Upper\s+Extrem)', re.I),
     'upper_extremity'),
    # Head/face
    (re.compile(r'\b(?:Pupil|Eye|Ocular|Facial|Face|Head|Scalp|Ear|Oral|Mouth)\b', re.I),
     'head_face'),
    # Chest/thorax
    (re.compile(r'\b(?:Chest|Thorax|Thoracic|Lung|Pulmonary|Breath\s+Sound|Cardiac|Heart)\b', re.I),
     'chest'),
    # Abdomen
    (re.compile(r'\b(?:Abdomen|Abdominal|Bowel|Gastric|GI|Stomach|Liver|Spleen)\b', re.I),
     'abdomen'),
    # Pelvis/perineum
    (re.compile(r'\b(?:Pelvi[cs]|Perineal|Perineum|Vaginal|Cervical|Uterine|Fundal)\b', re.I),
     'pelvis'),
    # Spine/back
    (re.compile(r'\b(?:Spine|Spinal|Lumbar|Thoracolumbar|Cervical\s+Spine|Back)\b', re.I),
     'spine'),
    # Skin (general)
    (re.compile(r'\b(?:Skin|Wound|Incision|Dressing|Stoma)\b', re.I),
     'skin'),
    # Neck
    (re.compile(r'\b(?:Neck|Throat|Trachea|Trach)\b', re.I),
     'neck'),
    # Digits
    (re.compile(r'\b(?:Finger|Thumb|Toe|Digit)\b', re.I),
     'digit'),
    # Generalized / whole body
    (re.compile(r'\b(?:General(?:ized)?|Whole\s+Body|Total\s+Body)\b', re.I),
     'generalized'),
]


# --- Assessment type patterns ---
# Maps regex → canonical assessment type.
ASSESSMENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Vascular
    (re.compile(r'\bEdema\b', re.I),             'edema'),
    (re.compile(r'\bPulse[s]?\b', re.I),         'pulse'),
    (re.compile(r'\bCapillary\s+Refill\b', re.I), 'capillary_refill'),
    (re.compile(r'\bColor\b', re.I),             'color'),
    (re.compile(r'\bTemp(?:erature)?(?:/Moisture)?\b', re.I), 'temperature'),
    (re.compile(r'\bCyanosis\b', re.I),          'cyanosis'),
    (re.compile(r'\bPerfusion\b', re.I),         'perfusion'),
    # Neurological
    (re.compile(r'\bMotor\s+(?:Response|Strength|Function)\b', re.I), 'motor'),
    (re.compile(r'\bSensation\b', re.I),         'sensation'),
    (re.compile(r'\bPupil\s+(?:Size|React\w*|Shape)\b', re.I), 'pupil'),
    (re.compile(r'\bReflexe?s?\b', re.I),        'reflex'),
    (re.compile(r'\bConsciousness\b|Level\s+of\s+Conscious', re.I), 'consciousness'),
    (re.compile(r'\bOrientation\b', re.I),       'orientation'),
    (re.compile(r'\bNeuro\b', re.I),             'neuro_general'),
    (re.compile(r'\bGCS\b|Glasgow|Best\s+(?:Eye|Verbal|Motor)\s+Response', re.I), 'gcs'),
    (re.compile(r'\bNIH\s+Stroke\s+Scale\b|NIHSS\b', re.I), 'stroke_scale'),
    (re.compile(r'\bRASS\b|Richmond\s+Agitation', re.I), 'rass'),
    (re.compile(r'\bCAM[\s-]?ICU\b|Confusion\s+Assessment', re.I), 'delirium_screening'),
    (re.compile(r'\bC-?SSRS\b|Columbia\s+Suicide', re.I), 'suicide_risk'),
    (re.compile(r'\bTrain\s+of\s+Four\b', re.I), 'train_of_four'),
    (re.compile(r'\bGrasp\b|Grip\s+Strength', re.I), 'grip_strength'),
    (re.compile(r'\bFacial\s+(?:Symmetry|Expression)\b', re.I), 'facial_assessment'),
    (re.compile(r'\bMuscle\s+Tension\b', re.I),  'muscle_tone'),
    (re.compile(r'\bVocalization\b', re.I),       'vocalization'),
    (re.compile(r'\bBody\s+Movement', re.I),      'body_movement'),
    (re.compile(r'\bBraden\b|Sensory\s+Perception|Friction\s+and\s+Shear', re.I), 'braden'),
    (re.compile(r'\bMorse\b', re.I),             'morse_fall_risk'),
    # Respiratory
    (re.compile(r'\bBreath\s+Sound', re.I),      'breath_sounds'),
    (re.compile(r'\bRespiratory\b', re.I),       'respiratory_general'),
    (re.compile(r'\bCough\b', re.I),             'cough'),
    (re.compile(r'\bSputum\b', re.I),            'sputum'),
    (re.compile(r'\bO2\s+(?:Device|Delivery|Method)\b', re.I), 'o2_delivery'),
    # Cardiac
    (re.compile(r'\bCardiac\s+Rhythm\b', re.I),  'cardiac_rhythm'),
    (re.compile(r'\bHeart\s+Sound', re.I),       'heart_sounds'),
    # Skin/wound
    (re.compile(r'\bWound\b', re.I),             'wound'),
    (re.compile(r'\bSkin\s+(?:Integrity|Condition|Color|Turgor)\b', re.I), 'skin_assessment'),
    (re.compile(r'\bDressing\b', re.I),          'dressing'),
    (re.compile(r'\bPressure\s+(?:Injury|Ulcer)\b', re.I), 'pressure_injury'),
    # GI/GU
    (re.compile(r'\bBowel\s+Sound', re.I),       'bowel_sounds'),
    (re.compile(r'\bBowel\s+Incontinence\b', re.I), 'bowel_function'),
    (re.compile(r'\bUrine\b', re.I),             'urine'),
    (re.compile(r'\bStool\b', re.I),             'stool'),
    (re.compile(r'\bDrainage\b', re.I),          'drainage'),
    # Pain
    (re.compile(r'\bPain\s+(?:Score|Level|Scale|Rating)\b', re.I), 'pain_score'),
    (re.compile(r'\bPain\s+Location\b', re.I),   'pain_location'),
    (re.compile(r'\bPain\b', re.I),              'pain_general'),
    # Functional / Rehab
    (re.compile(r'\bMobility\b', re.I),          'mobility'),
    (re.compile(r'\bAmbulation\b', re.I),        'ambulation'),
    (re.compile(r'\bADL\b|Activities\s+of\s+Daily', re.I), 'adl'),
    (re.compile(r'\bFall\s+Risk\b', re.I),       'fall_risk'),
    (re.compile(r'\bGait\b', re.I),              'gait'),
    (re.compile(r'\bBalance\b', re.I),           'balance'),
    (re.compile(r'\bToilet\w*\b', re.I),         'toileting'),
    (re.compile(r'\bBath(?:ing|e)?\b|Shower\b', re.I), 'bathing'),
    (re.compile(r'\bGrooming\b', re.I),          'grooming'),
    (re.compile(r'\bSelf[\s-]?Care\b', re.I),   'self_care'),
    # Speech/Swallowing/Cognition
    (re.compile(r'\bSwallow\w*\b|Dysphagia\b', re.I), 'swallowing'),
    (re.compile(r'\bSpeech\b', re.I),            'speech'),
    (re.compile(r'\bCogniti\w+\b', re.I),        'cognition'),
    (re.compile(r'\bMemory\b', re.I),            'memory'),
    (re.compile(r'\bAttention\b', re.I),         'attention'),
    (re.compile(r'\bVision\b|Visual\s+Acuity', re.I), 'vision'),
    (re.compile(r'\bHearing\b', re.I),           'hearing'),
    # Clinical findings
    (re.compile(r'\bSeizure\b', re.I),           'seizure'),
    (re.compile(r'\bHeadache\b', re.I),          'headache'),
    (re.compile(r'\bAnxiety\b', re.I),           'anxiety'),
    (re.compile(r'\bDepression\b', re.I),        'depression'),
    (re.compile(r'\bNausea\b', re.I),            'nausea'),
    (re.compile(r'\bDyspnea\b|Shortness\s+of\s+Breath', re.I), 'dyspnea'),
    (re.compile(r'\bTremor\b', re.I),            'tremor'),
    (re.compile(r'\bFever\b|Febrile\b', re.I),  'fever'),
    (re.compile(r'\bDelirium\b', re.I),          'delirium'),
    (re.compile(r'\bFatigue\b', re.I),           'fatigue'),
    (re.compile(r'\bDizziness\b|Vertigo\b', re.I), 'dizziness'),
    (re.compile(r'\bApnea\b', re.I),             'apnea'),
    # Intake/Output
    (re.compile(r'\bIntake\b', re.I),            'intake'),
    (re.compile(r'\bOutput\b', re.I),            'output'),
    # OB/Fetal
    (re.compile(r'\bContraction\b', re.I),       'contraction'),
    (re.compile(r'\bVariability\b', re.I),       'fetal_variability'),
    # Position/Posture
    (re.compile(r'\b(?:Body|Patient)\s+Position\b', re.I), 'body_position'),
    # Braden subscales (catch remaining: Moisture, Activity, Nutrition)
    (re.compile(r'\bMoisture\b', re.I),          'braden'),
    (re.compile(r'\bOut\s+of\s+Bed\s+Activity\b', re.I), 'braden'),
    (re.compile(r'\bNutrition\b', re.I),         'braden'),
    # Severity/calculated scores (generic fallback)
    (re.compile(r'\bSeverity\s*\(Calculated\)', re.I), 'pain_score'),
    # Ventilator compliance (CPOT subscale)
    (re.compile(r'\bComplica?nce\s+with\s+the\s+Ventilator\b', re.I), 'ventilator_compliance'),
    # Within-defined-limits (WDL) assessments
    (re.compile(r'\(WDL\)', re.I),               'wdl_screening'),
    # Vital signs (for completeness — most are atomic)
    (re.compile(r'\bBP\b|Blood\s+Pressure', re.I), 'blood_pressure'),
    (re.compile(r'\bHR\b|Heart\s+Rate', re.I),  'heart_rate'),
    (re.compile(r'\bRR\b|Resp(?:iratory)?\s+Rate', re.I), 'respiratory_rate'),
    (re.compile(r'\bSpO2\b|Pulse\s+Ox', re.I),  'spo2'),
    (re.compile(r'\bWeight\b', re.I),            'weight'),
    (re.compile(r'\bHeight\b', re.I),            'height'),
    (re.compile(r'\bBMI\b', re.I),               'bmi'),
]


# --- VAL_TYPE_C code mapping ---
# From IP_FLO_GP_DATA.VAL_TYPE_C (FLO/825)
VAL_TYPE_LABELS: dict[int | None, str] = {
    1:  'numeric',
    2:  'string',
    3:  'category',
    4:  'blood_pressure',
    5:  'weight',
    6:  'height',
    7:  'temperature',
    8:  'custom_list',
    9:  'date',
    10: 'time',
    None: 'unknown',
}


# --- ROW_TYP_C code mapping ---
ROW_TYPE_LABELS: dict[int | None, str] = {
    1:  'data',
    2:  'group',
    3:  'formula',
    4:  'extension',
    5:  'charge',
    6:  'infusion',
    7:  'lda',
    8:  'properties',
    9:  'acuity',
    10: 'image',
    11: 'trip',
    None: 'data',  # NULL = presumed data row
}


# --- Template category classification patterns ---
# Applied to TEMPLATE_NAME. Order: most specific first.
TEMPLATE_CATEGORY_PATTERNS: list[tuple[re.Pattern, str]] = [
    # OB/Labor & Delivery
    (re.compile(r'\b(?:OB|OBSTETRIC|L&D|LABOR|DELIVERY|POSTPARTUM|ANTEPARTUM|MFM|EPIDURAL)\b', re.I),
     'ob_labor_delivery'),
    # Oncology
    (re.compile(r'\b(?:ONCBCN|ONCOLOGY|CHEMO|INFUSION|STEM\s+CELL|APHERESIS)\b', re.I),
     'oncology'),
    # Behavioral Health
    (re.compile(r'\b(?:BH|BEHAVIORAL|PSYCH|NEUROFLOW|SUICIDE|SAFETY\s+PLAN)\b', re.I),
     'behavioral_health'),
    # Anesthesia
    (re.compile(r'\b(?:AN\s|ANESTHES|SEDATION|PACU|PRE-?OP|POST-?OP|INTRA-?OP|PERI-?OP)\b', re.I),
     'anesthesia'),
    # Surgery/OR
    (re.compile(r'\b(?:OR\s|SURG|OPERATIVE)\b', re.I),
     'surgery'),
    # ICU/Critical Care
    (re.compile(r'\b(?:ICU|CRITICAL\s+CARE|MICU|SICU|NICU|PICU|VENTILAT)\b', re.I),
     'critical_care'),
    # ED/Emergency
    (re.compile(r'\b(?:ED\s|EMERGENCY|TRIAGE|TRAUMA)\b', re.I),
     'emergency'),
    # Cardiology/Cardiovascular
    (re.compile(r'\b(?:CARDIAC|CARDIOV|CV\s|CATH\s*LAB|ECG|EKG|ECHO|HEART)\b', re.I),
     'cardiology'),
    # Respiratory/Pulmonary
    (re.compile(r'\b(?:PULMON|RESPIRATORY|VENT\s|AIRWAY|BRONCH)\b', re.I),
     'respiratory'),
    # Neurology
    (re.compile(r'\b(?:NEURO(?!FLOW)|STROKE|SEIZURE|EEG)\b', re.I),
     'neurology'),
    # Rehabilitation
    (re.compile(r'\b(?:REHAB|PT\s|OT\s|IRF|PHYSIC(?:AL)?\s+THER|OCCUPAT)\b', re.I),
     'rehabilitation'),
    # Endoscopy/GI
    (re.compile(r'\b(?:ENDOSCOP|GI\s|GASTRO|COLONOSCOP)\b', re.I),
     'endoscopy_gi'),
    # Dialysis/Renal
    (re.compile(r'\b(?:DIALYS|RENAL|NEPHRO|HEMODIAL)\b', re.I),
     'dialysis_renal'),
    # Transplant
    (re.compile(r'\b(?:TRANSPLANT|ORGAN\s+DONOR)\b', re.I),
     'transplant'),
    # Wound care
    (re.compile(r'\b(?:WOUND|OSTOMY|PRESSURE\s+INJURY|SKIN\s+ASSESSMENT)\b', re.I),
     'wound_care'),
    # Vital signs / general assessment
    (re.compile(r'\b(?:VITAL|DATA\s+RECORD|ASSESSMENT|DAILY\s+CARE)\b', re.I),
     'vitals_assessment'),
    # Intake/Output
    (re.compile(r'\b(?:INTAKE|OUTPUT|I\s*[&/]\s*O)\b', re.I),
     'intake_output'),
    # Pain
    (re.compile(r'\b(?:PAIN)\b', re.I),
     'pain'),
    # Medication/Infusion
    (re.compile(r'\b(?:MED(?:ICATION)?|INFUSION|DRIP|IV\s)\b', re.I),
     'medication'),
    # Home monitoring / telehealth
    (re.compile(r'\b(?:MYCHART|HOME\s+MONITOR|TELEHEALTH|REMOTE)\b', re.I),
     'home_monitoring'),
    # Perfusion
    (re.compile(r'\b(?:PERF(?:USION)?|BYPASS|ECMO|PUMP)\b', re.I),
     'perfusion'),
    # Quality/Core Measures
    (re.compile(r'\b(?:CORE\s+MEASURE|QUALITY|QC\s)\b', re.I),
     'quality_measures'),
    # Fall prevention
    (re.compile(r'\b(?:FALL)\b', re.I),
     'fall_prevention'),
    # Nutrition
    (re.compile(r'\b(?:NUTRIT|DIET|FEEDING|BREAST\s*FEED|FORMULA)\b', re.I),
     'nutrition'),
    # Diabetes
    (re.compile(r'\b(?:DIABET|GLUCOSE|INSULIN|A1C)\b', re.I),
     'diabetes'),
    # Tobacco/Substance
    (re.compile(r'\b(?:TOB|TOBACCO|SMOKING|ALCOHOL|SUBSTANCE)\b', re.I),
     'tobacco_substance'),
]


# --- Value domain classification patterns ---
# Applied to sets of custom list values to classify the value domain.
VALUE_DOMAIN_PATTERNS: dict[str, list[re.Pattern]] = {
    'ordinal_severity': [
        re.compile(r'\b(?:None|Mild|Moderate|Severe|Trace)\b', re.I),
        re.compile(r'\b(?:1\+|2\+|3\+|4\+)\b'),
        re.compile(r'\b(?:Absent|Slight|Marked)\b', re.I),
    ],
    'present_absent': [
        re.compile(r'\b(?:Present|Absent)\b', re.I),
        re.compile(r'\b(?:Yes|No)\b', re.I),
        re.compile(r'\b(?:Positive|Negative)\b', re.I),
    ],
    'ordinal_quality': [
        re.compile(r'\b(?:Normal|Abnormal|WDL|WNL)\b', re.I),
        re.compile(r'\b(?:Good|Fair|Poor)\b', re.I),
    ],
    'categorical_type': [
        re.compile(r'\b(?:Regular|Irregular)\b', re.I),
        re.compile(r'\b(?:Clear|Cloudy|Bloody|Purulent)\b', re.I),
    ],
    'lateralized_location': [
        re.compile(r'\b(?:Right|Left|Bilateral)\b', re.I),
        re.compile(r'\b(?:Upper|Lower|Anterior|Posterior|Medial|Lateral)\b', re.I),
    ],
    'likert_agreement': [
        re.compile(r'\b(?:Strongly\s+Agree|Agree|Neutral|Disagree|Strongly\s+Disagree)\b', re.I),
    ],
    'likert_frequency': [
        re.compile(r'\b(?:Always|Often|Sometimes|Rarely|Never)\b', re.I),
    ],
}

# Minimum fraction of list values that must match a domain pattern
VALUE_DOMAIN_MIN_MATCH_RATIO = 0.5


# --- OMOP qualifier concept mappings ---
# Pre-coordinated SNOMED anatomic site concepts for body_site + laterality.
# These combine body region and laterality in one concept, avoiding
# fact_relationship for simple anatomic qualification.
QUALIFIER_CONCEPTS: dict[tuple[str | None, str | None], int] = {
    # Lower extremity — verified via OHDSI vocab search
    ('lower_extremity', 'right'):     4179565,   # Entire right lower extremity (SNOMED 362784000)
    ('lower_extremity', 'left'):      4180483,   # Entire left lower extremity (SNOMED 362785004)
    # Upper extremity
    ('upper_extremity', 'right'):     4180344,   # Entire right upper extremity (SNOMED 362728000)
    ('upper_extremity', 'left'):      4180345,   # Entire left upper extremity (SNOMED 362729008)
    # Chest/lung (for breath sounds laterality)
    ('chest', 'right'):               4141610,   # Right lung structure (SNOMED 3341006)
    ('chest', 'left'):                4195613,   # Left lung structure (SNOMED 44029006)
    # Head/face (laterality for eyes, ears, pupils)
    ('head_face', 'right'):           4179426,   # Entire right half of face (SNOMED 362626009)
    ('head_face', 'left'):            4177717,   # Entire left half of face (SNOMED 362627000)
    # Generic laterality qualifier (when body region unknown)
    (None, 'right'):                  4080761,   # Right (SNOMED 24028007) — Qualifier Value
    (None, 'left'):                   4300877,   # Left (SNOMED 7771000) — Qualifier Value
    (None, 'bilateral'):              4080761,   # TODO: no standard "Bilateral" qualifier found; using Right as placeholder
}
