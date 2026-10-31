"""
Opportunity Scoring & Ranking Tool (§22 Agent Decision-Making Logic)
Implements normalized multicriteria priority scoring:
Priority = 0.35*I + 0.25*C + 0.20*F + 0.20*E
Where:
- I = Business impact score (0–100)
- C = Confidence score (0–100)
- F = Feasibility score (0–100)
- E = Urgency score (0–100)
All scores are normalized to 0–100.
"""
from typing import Dict, Any, Optional, Tuple


def calculate_normalized_priority(
    impact_score: float,
    confidence_score: float,
    feasibility_score: float,
    urgency_score: float,
    weights: Optional[Dict[str, float]] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    Computes normalized opportunity priority score:
    Priority = 0.35*I + 0.25*C + 0.20*F + 0.20*E
    All component scores are clamped to [0, 100].
    """
    w = weights or {
        "impact": 0.35,
        "confidence": 0.25,
        "feasibility": 0.20,
        "urgency": 0.20
    }
    I = min(100.0, max(0.0, float(impact_score)))
    C = min(100.0, max(0.0, float(confidence_score)))
    F = min(100.0, max(0.0, float(feasibility_score)))
    E = min(100.0, max(0.0, float(urgency_score)))

    score = (w["impact"] * I) + (w["confidence"] * C) + (w["feasibility"] * F) + (w["urgency"] * E)
    rounded_score = round(score, 1)

    breakdown = {
        "priority_score": rounded_score,
        "impact_score": round(I, 1),
        "confidence_score": round(C, 1),
        "feasibility_score": round(F, 1),
        "urgency_score": round(E, 1),
        "weights": w,
        "formula": "Priority = 0.35*I + 0.25*C + 0.20*F + 0.20*E",
        "components": {
            "I": round(I, 1),
            "C": round(C, 1),
            "F": round(F, 1),
            "E": round(E, 1)
        }
    }
    return rounded_score, breakdown


def score_opportunity(
    insight: Dict[str, Any],
    expected_impact_revenue: float,
    confidence: float,
    urgency_factor: float = 1.0,
    feasibility: float = 90.0,
    impact_benchmark: float = 100000.0
) -> Dict[str, Any]:
    """
    Computes priority_score and normalized opportunity priority:
    Priority = 0.35*I + 0.25*C + 0.20*F + 0.20*E
    Normalized components:
    - I = min(100, (expected_impact_revenue / impact_benchmark) * 100)
    - C = confidence * 100 (if <= 1.0) else confidence
    - F = feasibility (0-100, default 90.0)
    - E = min(100, urgency_factor * 68.0) if urgency_factor <= 2.0 else urgency_factor
    """
    confidence_clamped = min(max(confidence, 0.0), 1.0)
    legacy_priority = round(expected_impact_revenue * confidence_clamped * urgency_factor, 2)

    # Normalize I (Impact Score: 0-100)
    I = min(100.0, max(0.0, (expected_impact_revenue / max(1.0, impact_benchmark)) * 100.0))

    # Normalize C (Confidence Score: 0-100)
    C = (confidence * 100.0) if confidence <= 1.0 else confidence

    # Normalize F (Feasibility Score: 0-100)
    F = (feasibility * 100.0) if feasibility <= 1.0 else feasibility

    # Normalize E (Urgency Score: 0-100)
    E = (urgency_factor * 68.0) if urgency_factor <= 2.0 else urgency_factor

    norm_score, breakdown = calculate_normalized_priority(I, C, F, E)

    return {
        "expected_impact_revenue": round(expected_impact_revenue, 2),
        "confidence": confidence_clamped,
        "urgency_factor": urgency_factor,
        "priority_score": legacy_priority,
        "normalized_priority": norm_score,
        "priority_normalized": norm_score,
        "impact_score": breakdown["impact_score"],
        "confidence_score": breakdown["confidence_score"],
        "feasibility_score": breakdown["feasibility_score"],
        "urgency_score": breakdown["urgency_score"],
        "weights": breakdown["weights"],
        "formula": breakdown["formula"],
        "components": breakdown["components"]
    }

