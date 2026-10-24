
import json
from unittest.mock import patch

from http_client import extract_fields


def test_extraction_returns_expected_fields():
    result = extract_fields(
        "My idea is lunch delivery for college students in Jaipur. "
        "Selling prices range from 80 to 100 rupees, "
        "expected monthly sales range from 400 to 500, "
        "fixed costs are 2000 rupees per month, "
        "and variable cost per order ranges from 20 to 30 rupees.",
        {},
    )

    assert isinstance(result, dict)
    assert result["idea"]
    assert result["price_min"] == 80
    assert result["price_max"] == 100
    assert result["expected_monthly_sales_min"] == 400
    assert result["expected_monthly_sales_max"] == 500
    assert result["fixed_costs"] == 2000
    assert result["variable_cost_per_sale_min"] == 20
    assert result["variable_cost_per_sale_max"] == 30


@patch("http_client._chat")
def test_extraction_handles_invalid_json(mock_chat):
    mock_chat.return_value = "This is not valid JSON"

    result = extract_fields("My startup idea is food delivery", {})

    assert result == {}


@patch("http_client._chat")
def test_extraction_rejects_unexpected_keys(mock_chat):
    mock_chat.return_value = json.dumps({
        "idea": "Food delivery",
        "unexpected_field": "invented data",
    })

    result = extract_fields("My startup idea is food delivery", {})

    assert result == {}


@patch("http_client._chat")
def test_extraction_handles_api_exception(mock_chat):
    mock_chat.side_effect = Exception("API connection failed")

    result = extract_fields("My startup idea is food delivery", {})

    assert result == {}
