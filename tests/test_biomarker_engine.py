"""
Unit tests for the AegisMed Deterministic Biomarker Engine & Metric Evaluator.
Verifies zero-hallucination mathematical staging against ADA 2024, ACC/AHA 2024, KDIGO 2024 guidelines.
"""

import pytest
from app.core.biomarker_engine import (
    evaluate_hba1c,
    evaluate_blood_pressure,
    evaluate_egfr,
    evaluate_ldl,
    evaluate_lvef,
    evaluate_clinical_metrics
)
from app.services.rag_engine import process_clinical_query
from app.models.enums import UserMode


def test_hba1c_normal_and_prediabetes():
    normal = evaluate_hba1c("5.4%")
    assert normal.clinical_stage == "Normal (Non-Diabetic)"
    assert normal.is_critical_alert is False
    assert "Estimated Average Glucose" in (normal.estimated_metric or "")

    predia = evaluate_hba1c("6.0%")
    assert predia.clinical_stage == "Prediabetes (Impaired Glucose Tolerance)"
    assert "DPP trial" in predia.actionable_guidance


def test_hba1c_suboptimal_and_critical():
    subopt = evaluate_hba1c("8.2%")
    assert subopt.clinical_stage == "Type 2 Diabetes - Suboptimal Control"
    assert "SGLT2i or GLP-1 RA" in subopt.actionable_guidance

    crit = evaluate_hba1c("11.5%")
    assert crit.clinical_stage == "Type 2 Diabetes - Marked Hyperglycemia"
    assert crit.is_critical_alert is True


def test_blood_pressure_staging():
    norm = evaluate_blood_pressure("118/76 mmHg")
    assert norm.clinical_stage == "Normal Blood Pressure"

    elev = evaluate_blood_pressure("126/78")
    assert elev.clinical_stage == "Elevated Blood Pressure"

    s1 = evaluate_blood_pressure("134/84")
    assert s1.clinical_stage == "Stage 1 Hypertension"

    s2 = evaluate_blood_pressure("146/92")
    assert s2.clinical_stage == "Stage 2 Hypertension"

    crisis = evaluate_blood_pressure("190/125")
    assert crisis.clinical_stage == "Hypertensive Crisis"
    assert crisis.is_critical_alert is True


def test_egfr_kdigo_staging():
    g1 = evaluate_egfr("95 mL/min/1.73m2")
    assert g1.clinical_stage == "KDIGO Stage G1"

    g3a = evaluate_egfr("52")
    assert g3a.clinical_stage == "KDIGO Stage G3a"
    assert "Paxlovid" in g3a.clinical_implication

    g4 = evaluate_egfr("24")
    assert g4.clinical_stage == "KDIGO Stage G4"
    assert g4.is_critical_alert is True


def test_ldl_and_lvef_evaluations():
    ldl_high = evaluate_ldl("165 mg/dL")
    assert ldl_high.clinical_stage == "High"

    ldl_extreme = evaluate_ldl("210 mg/dL")
    assert "Very High" in ldl_extreme.clinical_stage
    assert ldl_extreme.is_critical_alert is True

    hfref = evaluate_lvef("35%")
    assert "HFrEF" in hfref.clinical_stage
    assert "GDMT" in hfref.actionable_guidance


def test_multi_marker_synergies():
    metrics = {
        "HbA1c": "8.2%",
        "eGFR": "48 mL/min/1.73m2",
        "blood_pressure": "145/92 mmHg"
    }
    report = evaluate_clinical_metrics(metrics)
    assert len(report.evaluations) == 3
    assert len(report.multi_marker_synergies) >= 2
    # Check diabetic kidney disease synergy
    assert any("Diabetic Kidney Disease" in syn for syn in report.multi_marker_synergies)
    # Check renovascular synergy
    assert any("Renovascular Synergy" in syn for syn in report.multi_marker_synergies)


def test_rag_pipeline_biomarker_synthesis():
    query = "My HbA1c is 8.2% and my eGFR is 48, what does this mean for my kidneys?"
    res_patient = process_clinical_query(query, UserMode.PATIENT)
    assert res_patient is not None
    assert "Your Lab Numbers & Measurements" in res_patient.answer
    assert "HbA1c" in res_patient.answer
    assert "eGFR" in res_patient.answer

    res_clinician = process_clinical_query(query, UserMode.PROFESSIONAL)
    assert res_clinician is not None
    assert "Deterministic Biomarker Stratification" in res_clinician.answer
