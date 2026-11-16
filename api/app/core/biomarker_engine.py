"""
AegisMed Deterministic Biomarker & Clinical Metric Engine.
Stage 2 of the AegisMed Healthcare Knowledge Navigator pipeline.

Performs deterministic, guideline-grounded evaluation of patient clinical metrics
(HbA1c, Blood Pressure, eGFR, LDL-C, LVEF, Creatinine) against peer-reviewed consensus
(ADA 2024, KDIGO 2024, ACC/AHA 2024, HFSA) to eliminate AI hallucinations regarding numerical values.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import re


class BiomarkerEvaluation(BaseModel):
    metric_name: str
    raw_value: str
    numeric_value: Optional[float] = None
    unit: str
    classification: str
    clinical_stage: str
    guideline_source: str
    estimated_metric: Optional[str] = None
    clinical_implication: str
    actionable_guidance: str
    is_critical_alert: bool = False


class ComprehensiveBiomarkerReport(BaseModel):
    evaluations: List[BiomarkerEvaluation] = Field(default_factory=list)
    multi_marker_synergies: List[str] = Field(default_factory=list)
    has_critical_alert: bool = False
    context_synthesis: str = ""


def parse_numeric(val_str: str) -> Optional[float]:
    """Extract the first valid float from a string."""
    match = re.search(r"([0-9]+(\.[0-9]+)?)", str(val_str))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def evaluate_hba1c(raw_val: str) -> BiomarkerEvaluation:
    num = parse_numeric(raw_val)
    if num is None:
        return BiomarkerEvaluation(
            metric_name="HbA1c",
            raw_value=raw_val,
            unit="%",
            classification="Unparsed Value",
            clinical_stage="Unspecified",
            guideline_source="ADA Standards of Care 2024",
            clinical_implication="HbA1c reflects 3-month average plasma glucose.",
            actionable_guidance="Verify lab value with healthcare provider."
        )

    # Nathan et al. / ADA eAG formula: eAG (mg/dL) = 28.7 * A1c - 46.7
    eag = round(28.7 * num - 46.7)
    eag_str = f"Estimated Average Glucose (eAG): ~{eag} mg/dL ({round(eag / 18.018, 1)} mmol/L)"

    if num < 5.7:
        stage = "Normal (Non-Diabetic)"
        classification = "Optimal Glycemic Range"
        implication = "Glycated hemoglobin is within healthy reference range. No evidence of chronic hyperglycemia."
        guidance = "Maintain balanced nutrition and regular physical activity."
        critical = False
    elif 5.7 <= num <= 6.4:
        stage = "Prediabetes (Impaired Glucose Tolerance)"
        classification = "High Risk for Type 2 Diabetes"
        implication = f"Indicates insulin resistance with elevated risk of cardiovascular disease. {eag_str}."
        guidance = "Lifestyle intervention (7% body weight loss, 150 min/wk moderate exercise) can reduce progression risk by up to 58% (DPP trial)."
        critical = False
    elif 6.5 <= num <= 7.0:
        stage = "Type 2 Diabetes - Target Range"
        classification = "Well-Controlled Glycemia"
        implication = f"Meets ADA primary adult target (<7.0%), significantly lowering microvascular complication risk. {eag_str}."
        guidance = "Continue current guideline therapy (Metformin ± SGLT2i/GLP-1 RA) and semi-annual surveillance."
        critical = False
    elif 7.1 <= num <= 8.5:
        stage = "Type 2 Diabetes - Suboptimal Control"
        classification = "Moderately Elevated Glycemia"
        implication = f"Above guideline target, accelerating microvascular damage (retinopathy, nephropathy, neuropathy). {eag_str}."
        guidance = "Evaluate pharmacotherapy intensification (adding SGLT2i or GLP-1 RA with proven cardiorenal benefit)."
        critical = False
    else:
        stage = "Type 2 Diabetes - Marked Hyperglycemia"
        classification = "Severely Elevated Glycemia"
        implication = f"Markedly above target with imminent risk of osmotic symptoms, hyperosmolar state, and rapid end-organ damage. {eag_str}."
        guidance = "Urgent provider evaluation for dual oral therapy or insulin initiation."
        critical = True

    return BiomarkerEvaluation(
        metric_name="HbA1c",
        raw_value=raw_val,
        numeric_value=num,
        unit="%",
        classification=classification,
        clinical_stage=stage,
        guideline_source="ADA Standards of Care 2024 (Section 6)",
        estimated_metric=eag_str,
        clinical_implication=implication,
        actionable_guidance=guidance,
        is_critical_alert=critical
    )


def evaluate_blood_pressure(raw_val: str) -> BiomarkerEvaluation:
    match = re.search(r"([0-9]{2,3})\s*[/]\s*([0-9]{2,3})", str(raw_val))
    if not match:
        return BiomarkerEvaluation(
            metric_name="Blood Pressure",
            raw_value=raw_val,
            unit="mmHg",
            classification="Unparsed Value",
            clinical_stage="Unspecified",
            guideline_source="ACC/AHA 2024 Hypertension Guidelines",
            clinical_implication="Blood pressure requires systolic/diastolic pair.",
            actionable_guidance="Record seated blood pressure after 5 minutes of rest."
        )

    sbp = int(match.group(1))
    dbp = int(match.group(2))

    if sbp > 180 or dbp > 120:
        stage = "Hypertensive Crisis"
        classification = "Severe Life-Threatening Elevation"
        implication = "Immediate risk of acute target organ damage (stroke, encephalopathy, acute coronary syndrome, aortic dissection, pulmonary edema)."
        guidance = "🚨 EMERGENCY: If accompanied by chest pain, shortness of breath, blurry vision, or numbness, call 911 immediately. Otherwise seek urgent same-day medical care."
        critical = True
    elif sbp >= 140 or dbp >= 90:
        stage = "Stage 2 Hypertension"
        classification = "Moderate to Severe Hypertension"
        implication = "Significantly increases long-term risk of myocardial infarction, stroke, heart failure, and chronic kidney disease."
        guidance = "Guideline standard: Initiation of 2 first-line antihypertensive agents of different classes (e.g. ACEi/ARB + CCB or Thiazide) plus sodium restriction (<2,000 mg/day)."
        critical = False
    elif 130 <= sbp <= 139 or 80 <= dbp <= 89:
        stage = "Stage 1 Hypertension"
        classification = "Mild Hypertension"
        implication = "Elevated vascular resistance predisposing to arterial stiffening."
        guidance = "Calculate 10-year ASCVD risk. If ≥10%, initiate pharmacotherapy; if <10%, 3-6 month trial of intensive lifestyle modifications (DASH diet, weight reduction)."
        critical = False
    elif 120 <= sbp <= 129 and dbp < 80:
        stage = "Elevated Blood Pressure"
        classification = "Prehypertension"
        implication = "Blood pressure is trending higher than optimal, signaling vascular changes."
        guidance = "Non-pharmacological therapy: DASH dietary pattern, sodium reduction, potassium supplementation, 150 min aerobic exercise/week."
        critical = False
    else:
        stage = "Normal Blood Pressure"
        classification = "Optimal Cardiovascular Range"
        implication = "Systolic and diastolic pressures are within healthy physiological limits."
        guidance = "Maintain heart-healthy lifestyle and annual screening."
        critical = False

    return BiomarkerEvaluation(
        metric_name="Blood Pressure",
        raw_value=raw_val,
        numeric_value=float(sbp),
        unit="mmHg",
        classification=classification,
        clinical_stage=stage,
        guideline_source="ACC/AHA/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA 2024 Guidelines",
        estimated_metric=f"Systolic: {sbp} mmHg / Diastolic: {dbp} mmHg (Mean Arterial Pressure: {round((2*dbp + sbp)/3, 1)} mmHg)",
        clinical_implication=implication,
        actionable_guidance=guidance,
        is_critical_alert=critical
    )


def evaluate_egfr(raw_val: str) -> BiomarkerEvaluation:
    num = parse_numeric(raw_val)
    if num is None:
        return BiomarkerEvaluation(
            metric_name="eGFR",
            raw_value=raw_val,
            unit="mL/min/1.73m2",
            classification="Unparsed Value",
            clinical_stage="Unspecified",
            guideline_source="KDIGO 2024 Clinical Practice Guideline for CKD",
            clinical_implication="Estimated Glomerular Filtration Rate measures renal filtration efficiency.",
            actionable_guidance="Repeat with serum creatinine and urine albumin-to-creatinine ratio (uACR)."
        )

    if num >= 90:
        stage = "KDIGO Stage G1"
        classification = "Normal or High Kidney Function"
        implication = "Glomerular filtration rate is preserved. In the absence of proteinuria or structural abnormalities, renal function is normal."
        guidance = "Annual surveillance if hypertensive or diabetic."
        critical = False
    elif 60 <= num <= 89:
        stage = "KDIGO Stage G2"
        classification = "Mildly Decreased Kidney Function"
        implication = "Mild reduction in filtration. Common in healthy aging; assess uACR to rule out active nephropathy."
        guidance = "Maintain BP control (<130/80 mmHg) and avoid frequent high-dose NSAID usage."
        critical = False
    elif 45 <= num <= 59:
        stage = "KDIGO Stage G3a"
        classification = "Mild to Moderately Decreased Kidney Function"
        implication = "Established chronic kidney filtration impairment. Paxlovid requires renal dose reduction (150mg/100mg). SGLT2i provides proven nephroprotection."
        guidance = "Adjust renally cleared medications. Monitor serum Cr/K+ every 3-6 months. SGLT2i and ACEi/ARB recommended if albuminuria is present."
        critical = False
    elif 30 <= num <= 44:
        stage = "KDIGO Stage G3b"
        classification = "Moderately to Severely Decreased Kidney Function"
        implication = "Significant renal compromise. Metformin dose must be reduced (max 1,000 mg/day). Dual RAS blockade strictly contraindicated due to hyperkalemia risk."
        guidance = "Nephrology co-management, close monitoring of mineral metabolism, electrolytes, and hemoglobin."
        critical = False
    elif 15 <= num <= 29:
        stage = "KDIGO Stage G4"
        classification = "Severely Decreased Kidney Function"
        implication = "Advanced CKD. Metformin and SGLT2i initiation contraindicated. High risk of progression to end-stage renal disease."
        guidance = "Mandatory nephrology referral and preparation for renal replacement therapy / kidney transplant evaluation."
        critical = True
    else:
        stage = "KDIGO Stage G5"
        classification = "Kidney Failure / End-Stage Renal Disease"
        implication = "Filtration severely compromised with toxic metabolite accumulation and fluid overload."
        guidance = "🚨 Urgent nephrology management. Evaluation for hemodialysis, peritoneal dialysis, or kidney transplantation."
        critical = True

    return BiomarkerEvaluation(
        metric_name="eGFR",
        raw_value=raw_val,
        numeric_value=num,
        unit="mL/min/1.73m2",
        classification=classification,
        clinical_stage=stage,
        guideline_source="KDIGO 2024 Clinical Practice Guideline for Chronic Kidney Disease",
        estimated_metric=f"Staging: {stage}",
        clinical_implication=implication,
        actionable_guidance=guidance,
        is_critical_alert=critical
    )


def evaluate_ldl(raw_val: str) -> BiomarkerEvaluation:
    num = parse_numeric(raw_val)
    if num is None:
        return BiomarkerEvaluation(
            metric_name="LDL-C",
            raw_value=raw_val,
            unit="mg/dL",
            classification="Unparsed Value",
            clinical_stage="Unspecified",
            guideline_source="ACC/AHA 2018/2022 Cholesterol Guidelines",
            clinical_implication="Low-density lipoprotein cholesterol drives atherosclerotic plaque.",
            actionable_guidance="Repeat with full fasting lipid profile."
        )

    if num < 70:
        stage = "Optimal / Very High Risk Target"
        classification = "Excellent Cardiovascular Protection"
        implication = "Meets stringent secondary prevention targets for patients with established ASCVD or diabetes with organ damage."
        guidance = "Maintain current lipid-lowering therapy and Mediterranean/heart-healthy nutrition."
        critical = False
    elif 70 <= num <= 99:
        stage = "Optimal"
        classification = "Desirable Range for Primary Prevention"
        implication = "Low atherogenic lipid burden in general adult populations."
        guidance = "Continue dietary saturated fat restriction (<7% of calories)."
        critical = False
    elif 100 <= num <= 129:
        stage = "Near Optimal / Borderline"
        classification = "Mildly Elevated"
        implication = "Slight atherogenic excess. May warrant statin therapy if 10-year ASCVD risk is ≥7.5% or in diabetic patients aged 40-75."
        guidance = "Lifestyle optimization with soluble fiber, plant stanols, and reassessment in 3-6 months."
        critical = False
    elif 130 <= num <= 159:
        stage = "Borderline High"
        classification = "Moderately Elevated Atherogenic Risk"
        implication = "Accelerates arterial plaque formation. Statin indicated for diabetic patients and those with intermediate ASCVD risk."
        guidance = "Moderate-intensity statin therapy (e.g. Atorvastatin 20mg or Rosuvastatin 10mg) per ACC/AHA algorithm."
        critical = False
    elif 160 <= num <= 189:
        stage = "High"
        classification = "Significantly Elevated Atherogenic Risk"
        implication = "Strongly predictive of premature coronary artery disease and ischemic events."
        guidance = "Statin therapy strongly recommended along with comprehensive cardiac risk factor modification."
        critical = False
    else:
        stage = "Very High (Severe Primary Hypercholesterolemia)"
        classification = "Severe Familial / Genetic Risk Level"
        implication = "Rule out Familial Hypercholesterolemia (FH). Extremely high lifetime cardiovascular event rate."
        guidance = "Immediate high-intensity statin therapy (Atorvastatin 80mg or Rosuvastatin 40mg) ± Ezetimibe ± PCSK9 inhibitor. Family cascade screening."
        critical = True

    return BiomarkerEvaluation(
        metric_name="LDL-C",
        raw_value=raw_val,
        numeric_value=num,
        unit="mg/dL",
        classification=classification,
        clinical_stage=stage,
        guideline_source="ACC/AHA 2018/2022 Multisociety Cholesterol Guidelines",
        estimated_metric=f"LDL Level: {num} mg/dL ({round(num * 0.02586, 2)} mmol/L)",
        clinical_implication=implication,
        actionable_guidance=guidance,
        is_critical_alert=critical
    )


def evaluate_lvef(raw_val: str) -> BiomarkerEvaluation:
    num = parse_numeric(raw_val)
    if num is None:
        return BiomarkerEvaluation(
            metric_name="LVEF",
            raw_value=raw_val,
            unit="%",
            classification="Unparsed Value",
            clinical_stage="Unspecified",
            guideline_source="ACC/AHA/HFSA 2022 Heart Failure Guidelines",
            clinical_implication="Left Ventricular Ejection Fraction measures systolic pump function.",
            actionable_guidance="Verify with transthoracic echocardiogram (TTE)."
        )

    if num >= 50:
        stage = "Normal / HFpEF (Preserved Ejection Fraction)"
        classification = "Preserved Systolic Pump Function"
        implication = "Left ventricle contracts normally. If heart failure symptoms are present, classification is HFpEF, where SGLT2 inhibitors and diuretic decongestion are guideline-indicated."
        guidance = "Blood pressure control, SGLT2 inhibitor (Dapagliflozin/Empagliflozin), and loop diuretics for fluid overload."
        critical = False
    elif 41 <= num <= 49:
        stage = "HFmrEF (Mildly Reduced Ejection Fraction)"
        classification = "Mild Systolic Impairment"
        implication = "Borderline systolic function. Benefits from guideline-directed medical therapy (ARNI, Beta-blocker, MRA, SGLT2i)."
        guidance = "Initiate or titrate GDMT; monitor repeat echocardiography at 6-12 months."
        critical = False
    else:
        stage = "HFrEF (Reduced Ejection Fraction)"
        classification = "Significant Systolic Dysfunction"
        implication = "Severely reduced contractile function. Class I guideline mandate for 4-pillar GDMT to reduce mortality and hospitalization."
        guidance = "Quadruple GDMT therapy: 1) ARNI (Sacubitril/Valsartan), 2) Evidence-based Beta-blocker (Carvedilol/Metoprolol succinate), 3) MRA (Spironolactone/Eplerenone), 4) SGLT2i."
        critical = True

    return BiomarkerEvaluation(
        metric_name="LVEF",
        raw_value=raw_val,
        numeric_value=num,
        unit="%",
        classification=classification,
        clinical_stage=stage,
        guideline_source="ACC/AHA/HFSA 2022 Heart Failure Guidelines (Universal Definition)",
        estimated_metric=f"Systolic Staging: {stage}",
        clinical_implication=implication,
        actionable_guidance=guidance,
        is_critical_alert=critical
    )


def evaluate_clinical_metrics(clinical_metrics: Dict[str, Any]) -> ComprehensiveBiomarkerReport:
    """
    Main evaluation pipeline that inspects all extracted metrics, evaluates them
    deterministically, and detects multi-marker cardiorenal metabolic synergies.
    """
    evaluations: List[BiomarkerEvaluation] = []
    synergies: List[str] = []
    has_critical = False

    metric_lookup = {k.lower(): v for k, v in clinical_metrics.items()}

    # 1. Evaluate individual biomarkers
    for k, v in clinical_metrics.items():
        k_low = k.lower()
        if "hba1c" in k_low:
            res = evaluate_hba1c(str(v))
            evaluations.append(res)
            if res.is_critical_alert:
                has_critical = True
        elif any(bp_k in k_low for bp_k in ["bp", "blood_pressure", "blood pressure"]):
            res = evaluate_blood_pressure(str(v))
            evaluations.append(res)
            if res.is_critical_alert:
                has_critical = True
        elif "egfr" in k_low:
            res = evaluate_egfr(str(v))
            evaluations.append(res)
            if res.is_critical_alert:
                has_critical = True
        elif any(ldl_k in k_low for ldl_k in ["ldl", "ldl-c", "cholesterol"]):
            res = evaluate_ldl(str(v))
            evaluations.append(res)
            if res.is_critical_alert:
                has_critical = True
        elif "lvef" in k_low:
            res = evaluate_lvef(str(v))
            evaluations.append(res)
            if res.is_critical_alert:
                has_critical = True

    # 2. Multi-Marker Synergies
    hba1c_eval = next((e for e in evaluations if e.metric_name == "HbA1c"), None)
    bp_eval = next((e for e in evaluations if e.metric_name == "Blood Pressure"), None)
    egfr_eval = next((e for e in evaluations if e.metric_name == "eGFR"), None)
    ldl_eval = next((e for e in evaluations if e.metric_name == "LDL-C"), None)

    # Synergy A: Diabetes + Kidney Dysfunction
    if hba1c_eval and egfr_eval:
        if (hba1c_eval.numeric_value or 0) >= 6.5 and (egfr_eval.numeric_value or 100) < 60:
            synergies.append(
                "Cardiorenal Metabolic Synergy (Diabetic Kidney Disease): Concomitant elevated HbA1c and reduced eGFR strictly mandates SGLT2 inhibitor (Dapagliflozin/Empagliflozin) therapy for renal preservation per joint ADA/KDIGO consensus."
            )

    # Synergy B: Hypertension + Kidney Dysfunction
    if bp_eval and egfr_eval:
        if (bp_eval.numeric_value or 0) >= 130 and (egfr_eval.numeric_value or 100) < 60:
            synergies.append(
                "Renovascular Synergy: Elevated blood pressure accelerates glomerular hyperfiltration damage. First-line therapy requires RAS inhibition with ACEi or ARB (target SBP <120-130 mmHg per KDIGO 2024). Strictly avoid NSAIDs."
            )

    # Synergy C: Diabetes + High LDL (ASCVD Risk Multiplier)
    if hba1c_eval and ldl_eval:
        if (hba1c_eval.numeric_value or 0) >= 6.5 and (ldl_eval.numeric_value or 0) >= 70:
            synergies.append(
                "ASCVD Multiplier: Diabetes confers high cardiovascular risk; ACC/AHA guidelines mandate moderate-to-high intensity statin therapy targeting LDL-C <70 mg/dL (or ≥50% reduction)."
            )

    # 3. Compile context synthesis for LLM prompt injection
    synthesis_lines = []
    if evaluations:
        synthesis_lines.append("### DETERMINISTIC CLINICAL BIOMARKER EVALUATIONS:")
        for ev in evaluations:
            synthesis_lines.append(f"- **{ev.metric_name} ({ev.raw_value})**: {ev.clinical_stage} [{ev.classification}]")
            synthesis_lines.append(f"  * Guideline: {ev.guideline_source}")
            synthesis_lines.append(f"  * Clinical Reality: {ev.clinical_implication}")
            synthesis_lines.append(f"  * Direct Action: {ev.actionable_guidance}")
        if synergies:
            synthesis_lines.append("\n### CLINICAL SYNERGIES & TRIANGULATION:")
            for syn in synergies:
                synthesis_lines.append(f"- ⚠️ {syn}")

    return ComprehensiveBiomarkerReport(
        evaluations=evaluations,
        multi_marker_synergies=synergies,
        has_critical_alert=has_critical,
        context_synthesis="\n".join(synthesis_lines)
    )
