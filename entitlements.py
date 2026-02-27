"""
Workcover entitlement calculator — VIC, NSW, QLD step-down rules.

Calculates weekly compensation based on state legislation, weeks since injury,
PIAWE, and current capacity.
"""

from __future__ import annotations

from datetime import date, timedelta
from dataclasses import dataclass

# ── State entitlement rules ──────────────────────────────────────────────────
# Each state defines step-down periods as a list of (week_threshold, rate, label).
# The rate applies FROM that week until the next threshold.

VIC_RULES = {
    "name": "Victoria",
    "legislation": "Workplace Injury Rehabilitation and Compensation Act 2013",
    "periods": [
        # (from_week, to_week, rate, label)
        (0, 13, 0.95, "First 13 weeks — 95% of PIAWE"),
        (13, 52, 0.80, "Weeks 14–52 — 80% of PIAWE"),
        (52, 78, 0.80, "Weeks 53–78 — 80% (if no work capacity)"),
        (78, 130, 0.80, "Weeks 79–130 — 80% (serious injury only)"),
    ],
    "max_weeks": 130,
    "notes": [
        "After 130 weeks, entitlements cease unless classified as a 'serious injury'.",
        "Workers with no current work capacity after 130 weeks must apply for serious injury certification.",
        "If worker has current work capacity, employer must provide suitable employment.",
        "Second entitlement review at 52 weeks — capacity assessment required.",
    ],
}

NSW_RULES = {
    "name": "New South Wales",
    "legislation": "Workers Compensation Act 1987 / Personal Injury Commission Act 2020",
    "periods": [
        (0, 13, 0.95, "First 13 weeks — 95% of PIAWE"),
        (13, 26, 0.80, "Weeks 14–26 — 80% of PIAWE"),
        (26, 52, 0.80, "Weeks 27–52 — 80% of PIAWE"),
        (52, 130, 0.80, "Weeks 53–130 — 80% (if capacity for work)"),
        (130, 260, 0.80, "Weeks 131–260 — 80% (WPI > 20% only)"),
    ],
    "max_weeks": 260,
    "notes": [
        "After 52 weeks, work capacity decisions apply — insurer assesses ability to work.",
        "Workers with no capacity who don't meet WPI threshold may lose entitlements at 130 weeks.",
        "Whole Person Impairment (WPI) > 20% required for payments beyond 130 weeks.",
        "Maximum weekly amount is capped by legislation (indexed annually).",
    ],
}

QLD_RULES = {
    "name": "Queensland",
    "legislation": "Workers' Compensation and Rehabilitation Act 2003",
    "periods": [
        (0, 26, 0.85, "First 26 weeks — 85% of PIAWE (Normal Weekly Earnings)"),
        (26, 52, 0.75, "Weeks 27–52 — 75% of PIAWE"),
        (52, 104, 0.70, "Weeks 53–104 — 70% of PIAWE (review required)"),
    ],
    "max_weeks": 104,
    "notes": [
        "QLD uses 'Normal Weekly Earnings' (NWE) which is similar to PIAWE.",
        "After 26 weeks, step-down to 75%. Worker must be actively rehabilitating.",
        "Entitlements generally cease at 104 weeks (2 years).",
        "Lump sum compensation may be available for permanent impairment.",
    ],
}

STATE_RULES = {
    "VIC": VIC_RULES,
    "NSW": NSW_RULES,
    "QLD": QLD_RULES,
}

# Also support TAS, SA, WA with generic rules
for _st in ("TAS", "SA", "WA"):
    STATE_RULES[_st] = {
        "name": _st,
        "legislation": "Contact state regulator for specific legislation",
        "periods": [
            (0, 13, 0.95, "First 13 weeks — ~95% of PIAWE (indicative)"),
            (13, 26, 0.85, "Weeks 14–26 — ~85% of PIAWE (indicative)"),
            (26, 52, 0.80, "Weeks 27–52 — ~80% of PIAWE (indicative)"),
        ],
        "max_weeks": 52,
        "notes": [
            f"These are indicative rates for {_st}. Check state-specific legislation.",
            "Consult your insurer or state regulator for exact entitlements.",
        ],
    }


@dataclass
class EntitlementResult:
    state: str
    piawe: float
    weeks_since_injury: int
    current_period_label: str
    current_rate: float
    weekly_compensation: float
    annual_compensation: float
    total_paid_estimate: float
    remaining_weeks: int
    max_weeks: int
    all_periods: list  # list of dicts with period breakdowns
    notes: list


def calculate_weeks_since_injury(date_of_injury: str | None) -> int | None:
    """Calculate weeks since injury date. Returns None if no date."""
    if not date_of_injury:
        return None
    try:
        doi = date.fromisoformat(date_of_injury)
        delta = date.today() - doi
        return max(0, delta.days // 7)
    except (ValueError, TypeError):
        return None


def get_current_rate(state: str, weeks: int) -> tuple[float, str]:
    """Get the current compensation rate and period label for a given state and week."""
    rules = STATE_RULES.get(state)
    if not rules:
        return 0.0, "Unknown state"

    current_rate = 0.0
    current_label = "Entitlements may have ceased"

    for from_wk, to_wk, rate, label in rules["periods"]:
        if from_wk <= weeks < to_wk:
            current_rate = rate
            current_label = label
            break
    else:
        # Past all defined periods
        if weeks >= rules["max_weeks"]:
            current_rate = 0.0
            current_label = f"Beyond {rules['max_weeks']} weeks — entitlements may have ceased"

    return current_rate, current_label


def calculate_entitlement(
    state: str,
    piawe: float | None,
    date_of_injury: str | None,
) -> EntitlementResult | None:
    """
    Calculate full entitlement breakdown for a worker.

    Returns None if insufficient data (no state, no PIAWE, no DOI).
    """
    if not state or not piawe or piawe <= 0:
        return None

    weeks = calculate_weeks_since_injury(date_of_injury)
    if weeks is None:
        return None

    rules = STATE_RULES.get(state)
    if not rules:
        return None

    current_rate, current_label = get_current_rate(state, weeks)
    weekly_comp = piawe * current_rate
    annual_comp = weekly_comp * 52

    # Calculate total paid estimate (sum across all periods up to current week)
    total_paid = 0.0
    all_periods = []
    for from_wk, to_wk, rate, label in rules["periods"]:
        if weeks <= from_wk:
            # Haven't reached this period yet
            wks_in_period = 0
            status = "Upcoming"
        elif weeks >= to_wk:
            # Completed this period
            wks_in_period = to_wk - from_wk
            status = "Completed"
        else:
            # Currently in this period
            wks_in_period = weeks - from_wk
            status = "Current"

        period_total = piawe * rate * wks_in_period

        all_periods.append({
            "label": label,
            "from_week": from_wk,
            "to_week": to_wk,
            "rate": rate,
            "rate_pct": f"{rate * 100:.0f}%",
            "weeks_in_period": wks_in_period,
            "weekly_amount": piawe * rate,
            "period_total": period_total,
            "status": status,
        })

        total_paid += period_total

    remaining = max(0, rules["max_weeks"] - weeks)

    return EntitlementResult(
        state=state,
        piawe=piawe,
        weeks_since_injury=weeks,
        current_period_label=current_label,
        current_rate=current_rate,
        weekly_compensation=weekly_comp,
        annual_compensation=annual_comp,
        total_paid_estimate=total_paid,
        remaining_weeks=remaining,
        max_weeks=rules["max_weeks"],
        all_periods=all_periods,
        notes=rules["notes"],
    )


# ── Premium Impact / Savings Calculator ──────────────────────────────────────

# Industry base rates by state (indicative averages for cleaning/facilities)
INDUSTRY_BASE_RATES = {
    "VIC": {"low": 1.0, "mid": 2.5, "high": 5.0},
    "NSW": {"low": 0.8, "mid": 2.2, "high": 4.5},
    "QLD": {"low": 0.7, "mid": 2.0, "high": 4.0},
    "TAS": {"low": 0.8, "mid": 2.2, "high": 4.0},
    "SA":  {"low": 0.8, "mid": 2.0, "high": 4.0},
    "WA":  {"low": 0.7, "mid": 1.8, "high": 3.5},
}


@dataclass
class PremiumSavingsResult:
    annual_wages: float
    current_rate: float
    current_premium: float
    # Scenario: improved management
    improved_rate: float
    improved_premium: float
    annual_savings: float
    savings_3yr: float
    savings_5yr: float
    reduction_pct: float
    # Breakdown
    scenarios: list  # list of dicts for different improvement levels


def calculate_premium_savings(
    annual_wages: float,
    current_rate: float,
    num_claims: int = 0,
    avg_claim_cost: float = 0,
    state: str = "VIC",
) -> PremiumSavingsResult:
    """
    Calculate potential premium savings from improved claim management.

    Experience rating: claims affect premiums for 3 years.
    Reducing claim frequency/duration directly lowers the experience modifier.

    Typical experience modifier range: 0.5 (excellent) to 2.0 (poor).
    """
    current_premium = annual_wages * (current_rate / 100)

    # Estimate total claim costs impact
    total_claim_costs = num_claims * avg_claim_cost if num_claims > 0 and avg_claim_cost > 0 else current_premium * 0.4

    # Build improvement scenarios
    scenarios = []
    for label, claim_reduction, duration_reduction in [
        ("Conservative (10% fewer claims, 15% shorter)", 0.10, 0.15),
        ("Moderate (20% fewer claims, 25% shorter)", 0.20, 0.25),
        ("Aggressive (35% fewer claims, 40% shorter)", 0.35, 0.40),
    ]:
        # Combined impact on claim costs
        combined_reduction = 1 - (1 - claim_reduction) * (1 - duration_reduction)

        # Premium impact: claims typically drive 40-60% of premium variation
        premium_impact_factor = 0.50  # claims influence ~50% of premium
        rate_reduction = current_rate * combined_reduction * premium_impact_factor
        new_rate = max(current_rate - rate_reduction, current_rate * 0.5)  # floor at 50% of current
        new_premium = annual_wages * (new_rate / 100)
        saving = current_premium - new_premium

        scenarios.append({
            "label": label,
            "claim_reduction": f"{claim_reduction * 100:.0f}%",
            "duration_reduction": f"{duration_reduction * 100:.0f}%",
            "new_rate": new_rate,
            "new_rate_pct": f"{new_rate:.2f}%",
            "new_premium": new_premium,
            "annual_savings": saving,
            "savings_3yr": saving * 3,
            "savings_5yr": saving * 5,
            "reduction_pct": (1 - new_rate / current_rate) * 100,
        })

    # Use moderate scenario as default
    moderate = scenarios[1]

    return PremiumSavingsResult(
        annual_wages=annual_wages,
        current_rate=current_rate,
        current_premium=current_premium,
        improved_rate=moderate["new_rate"],
        improved_premium=moderate["new_premium"],
        annual_savings=moderate["annual_savings"],
        savings_3yr=moderate["savings_3yr"],
        savings_5yr=moderate["savings_5yr"],
        reduction_pct=moderate["reduction_pct"],
        scenarios=scenarios,
    )


def get_step_down_timeline(state: str, piawe: float) -> list[dict]:
    """
    Generate a timeline of all step-downs for display.
    Returns list of dicts with week, rate, weekly_amount, cumulative.
    """
    rules = STATE_RULES.get(state)
    if not rules or not piawe:
        return []

    timeline = []
    cumulative = 0.0

    for from_wk, to_wk, rate, label in rules["periods"]:
        weekly = piawe * rate
        period_weeks = to_wk - from_wk
        period_total = weekly * period_weeks
        cumulative += period_total

        timeline.append({
            "period": label,
            "weeks": f"{from_wk + 1}–{to_wk}",
            "rate": f"{rate * 100:.0f}%",
            "weekly": weekly,
            "period_total": period_total,
            "cumulative": cumulative,
        })

    return timeline
