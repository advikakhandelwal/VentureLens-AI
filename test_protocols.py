
from protocols import (
    coerce_fields,
    missing_required,
    compute_financials,
    compute_deterministic_score,
    build_follow_up,
    is_new_idea_message,
)
from unittest.mock import Mock, patch


def sample_fields():
    return {
        "idea": "Lunch delivery",
        "price_min": 100,
        "price_max": 100,
        "expected_monthly_sales_min": 100,
        "expected_monthly_sales_max": 100,
        "fixed_costs": 2000,
        "variable_cost_per_sale_min": 30,
        "variable_cost_per_sale_max": 30,
    }


def test_valid_fields_are_converted_to_numbers():
    fields = coerce_fields({
        "idea": "Lunch delivery",
        "price_min": "80",
        "price_max": "100",
        "expected_monthly_sales_min": "100",
        "expected_monthly_sales_max": "200",
        "fixed_costs": "2000",
        "variable_cost_per_sale_min": "20",
        "variable_cost_per_sale_max": "30",
    })

    assert fields["price_min"] == 80.0
    assert fields["price_max"] == 100.0
    assert fields["expected_monthly_sales_min"] == 100.0
    assert fields["expected_monthly_sales_max"] == 200.0
    assert fields["fixed_costs"] == 2000.0
    assert fields["variable_cost_per_sale_min"] == 20.0
    assert fields["variable_cost_per_sale_max"] == 30.0


def test_invalid_negative_cost_is_rejected():
    fields = coerce_fields({
        "idea": "Lunch delivery",
        "price_min": 100,
        "price_max": 100,
        "expected_monthly_sales_min": 100,
        "expected_monthly_sales_max": 100,
        "fixed_costs": -2000,
        "variable_cost_per_sale_min": 30,
        "variable_cost_per_sale_max": 30,
    })

    assert "fixed_costs" not in fields


def test_missing_required_fields_are_detected():
    missing = missing_required({"idea": "Lunch delivery"})

    assert "price_min" in missing
    assert "price_max" in missing
    assert "expected_monthly_sales_min" in missing
    assert "expected_monthly_sales_max" in missing
    assert "fixed_costs" in missing
    assert "variable_cost_per_sale_min" in missing
    assert "variable_cost_per_sale_max" in missing


def test_financial_calculations():
    result = compute_financials(sample_fields())

    assert result["monthly_revenue"] == 10000
    assert result["monthly_revenue_min"] == 10000
    assert result["monthly_revenue_max"] == 10000
    assert result["contribution_per_sale"] == 70
    assert result["total_variable_costs"] == 3000
    assert result["estimated_monthly_profit"] == 5000
    assert result["monthly_profit_min"] == 5000
    assert result["monthly_profit_max"] == 5000
    assert result["break_even_text"] == "29 sales/month"


def test_break_even_is_not_possible_when_cost_per_sale_is_too_high():
    fields = sample_fields()
    fields["variable_cost_per_sale_min"] = 120
    fields["variable_cost_per_sale_max"] = 120

    result = compute_financials(fields)

    assert result["contribution_per_sale"] == -20
    assert result["break_even_text"].startswith("Not achievable")


def test_deterministic_score_has_expected_structure():
    financials = compute_financials(sample_fields())

    score = compute_deterministic_score(financials)

    assert isinstance(score, dict)
    assert "margin_quality" in score
    assert "break_even_feasibility" in score
    assert "profitability" in score


def test_follow_up_asks_for_missing_financial_details():
    fields = {
        "idea": "Lunch delivery for college students"
    }

    missing = [
        "price_min",
        "price_max",
        "expected_monthly_sales_min",
        "expected_monthly_sales_max",
        "fixed_costs",
        "variable_cost_per_sale_min",
        "variable_cost_per_sale_max",
    ]

    message = build_follow_up(fields, missing)

    assert "Lunch delivery for college students" in message
    assert "lowest selling price" in message.lower()
    assert "highest selling price" in message.lower()
    assert "minimum number of sales" in message.lower()
    assert "maximum number of sales" in message.lower()
    assert "fixed costs per month" in message.lower()
    assert "lowest variable cost" in message.lower()
    assert "highest variable cost" in message.lower()


def test_report_does_not_invent_competitor_evidence():
    fields = sample_fields()
    fields["idea"] = "A student-focused meal delivery service"
    fields["variable_cost_per_sale_min"] = 60
    fields["variable_cost_per_sale_max"] = 60

    fake_analysis = {
        "qualitative_score": 15,
        "score_notes": "More customer validation is needed.",
        "market_analysis": "The target market has not been independently verified.",
        "competition_analysis": "Swiggy and Zomato are the main competitors.",
        "key_risks": ["Demand is unverified", "Costs may rise", "Sales may be lower"],
        "improvements": ["Interview students", "Test pricing", "Pilot deliveries"],
        "next_actions": ["Interview 10 students", "Run a small pilot", "Track costs"],
        "recommendation": "VALIDATE",
        "recommendation_reason": "Validate demand before investing.",
    }

    fake_context = Mock()

    with patch("protocols.analyze_venture", return_value=fake_analysis):
        from protocols import build_report
        report = build_report(fake_context, fields)

    assert "No competitor information was provided by the founder." in report
    assert "Competitor claims have not been verified." in report
    assert "Swiggy and Zomato are the main competitors." not in report
    assert "Monthly revenue range:" in report
    assert "Estimated monthly profit/loss range:" in report


def test_new_idea_message_is_detected():
    assert is_new_idea_message(
        "I want to start a clothing business in Jaipur"
    )

    assert not is_new_idea_message(
        "What if I increase my price to 120?"
    )
