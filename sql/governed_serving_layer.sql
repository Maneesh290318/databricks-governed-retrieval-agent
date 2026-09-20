-- Core governed serving layer used by the application.
-- Assumes corrections_health_demo.curated.diabetic_encounters and
-- corrections_health_demo.curated.knowledge_documents already exist.

CREATE OR REPLACE VIEW corrections_health_demo.curated.analyst_view AS
SELECT encounter_id, time_in_hospital, num_lab_procedures, num_medications,
       number_diagnoses, change, admission_type_desc, discharge_disposition_desc,
       admission_source_desc, readmitted
FROM corrections_health_demo.curated.diabetic_encounters;

CREATE OR REPLACE VIEW corrections_health_demo.curated.supervisor_view AS
SELECT admission_type_desc, discharge_disposition_desc, admission_source_desc, readmitted,
       COUNT(*) AS encounter_count,
       ROUND(AVG(time_in_hospital), 2) AS avg_time_in_hospital,
       ROUND(AVG(num_lab_procedures), 2) AS avg_lab_procedures,
       ROUND(AVG(num_medications), 2) AS avg_medications,
       ROUND(AVG(number_diagnoses), 2) AS avg_diagnoses,
       SUM(CASE WHEN change = 'Ch' THEN 1 ELSE 0 END) AS medication_adjustments
FROM corrections_health_demo.curated.diabetic_encounters
GROUP BY admission_type_desc, discharge_disposition_desc, admission_source_desc, readmitted;

CREATE OR REPLACE VIEW corrections_health_demo.curated.doctor_view AS
SELECT encounter_id, patient_nbr, race, gender, age, time_in_hospital,
       num_lab_procedures, num_medications, number_diagnoses,
       diag_1, diag_2, diag_3, max_glu_serum, A1Cresult, insulin, change,
       diabetesMed, readmitted, admission_type_desc, discharge_disposition_desc,
       admission_source_desc
FROM corrections_health_demo.curated.diabetic_encounters;

CREATE OR REPLACE VIEW corrections_health_demo.curated.nurse_view AS
SELECT encounter_id, time_in_hospital, num_lab_procedures, num_medications,
       max_glu_serum, A1Cresult, insulin, change, diabetesMed,
       admission_type_desc, discharge_disposition_desc, readmitted
FROM corrections_health_demo.curated.diabetic_encounters;

CREATE OR REPLACE FUNCTION corrections_health_demo.curated.get_analyst_data(encounter_id_filter BIGINT DEFAULT NULL)
RETURNS TABLE
RETURN
  SELECT * FROM corrections_health_demo.curated.analyst_view
  WHERE encounter_id_filter IS NULL OR encounter_id = encounter_id_filter
  LIMIT 100;

CREATE OR REPLACE FUNCTION corrections_health_demo.curated.get_supervisor_data(admission_type_filter STRING DEFAULT NULL)
RETURNS TABLE
RETURN
  SELECT * FROM corrections_health_demo.curated.supervisor_view
  WHERE admission_type_filter IS NULL OR admission_type_desc = admission_type_filter;

CREATE OR REPLACE FUNCTION corrections_health_demo.curated.get_doctor_data(encounter_id_filter BIGINT DEFAULT NULL)
RETURNS TABLE
RETURN
  SELECT * FROM corrections_health_demo.curated.doctor_view
  WHERE encounter_id_filter IS NULL OR encounter_id = encounter_id_filter
  LIMIT 100;

CREATE OR REPLACE FUNCTION corrections_health_demo.curated.get_nurse_data(encounter_id_filter BIGINT DEFAULT NULL)
RETURNS TABLE
RETURN
  SELECT * FROM corrections_health_demo.curated.nurse_view
  WHERE encounter_id_filter IS NULL OR encounter_id = encounter_id_filter
  LIMIT 100;

CREATE OR REPLACE FUNCTION corrections_health_demo.curated.search_policy_documents(
  query_text STRING,
  requester_role STRING
)
RETURNS TABLE
RETURN
  SELECT document_id, title, doc_type, content, search_score
  FROM vector_search(
    index => 'corrections_health_demo.curated.knowledge_documents_index',
    query_text => query_text,
    num_results => 15
  )
  WHERE array_contains(role_visibility, requester_role)
  LIMIT 5;
