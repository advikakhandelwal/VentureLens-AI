
from unittest.mock import patch

from http_client import analyze_venture


def valid_analysis():
    return {
        "qualitative_score": 18,
        "score_notes": "Some evidence exists, but demand needs validation.",
        "market_analysis": "The founder's target market has not been independently verified.",
        "competition_analysis": "No competitor information was provided.",
        "key_risks": ["Demand is unverified", "Costs may rise", "Sales may be lower"],
        "improvements": ["Interview customers", "Test pricing", "Run a pilot"],
        "next_actions": ["Interview 10 users", "Test a landing page", "Track pilot results"],
        "recommendation": "VALIDATE",
        "recommendation_reason": "Validate customer demand before investing.",
    }


@patch("http_client._chat")
def test_analysis_accepts_valid_response(mock_chat):
    import json

    mock_chat.return_value = json.dumps(valid_analysis())

    result = analyze_venture(
        {"idea": "Student meal delivery"},
        {"monthly_revenue": 10000},
        {"profitability": 10},
    )

    assert result["qualitative_score"] == 18
    assert result["recommendation"] == "VALIDATE"


@patch("http_client._chat")
def test_analysis_rejects_invalid_score(mock_chat):
    import json

    analysis = valid_analysis()
    analysis["qualitative_score"] = 40
    mock_chat.return_value = json.dumps(analysis)

    result = analyze_venture(
        {"idea": "Student meal delivery"},
        {"monthly_revenue": 10000},
        {"profitability": 10},
    )

    assert result == {}
    

@patch("http_client._chat")
def test_analysis_rejects_missing_required_field(mock_chat):
    import json

    analysis = valid_analysis()
    del analysis["recommendation_reason"]
    mock_chat.return_value = json.dumps(analysis)

    result = analyze_venture(
        {"idea": "Student meal delivery"},
        {"monthly_revenue": 10000},
        {"profitability": 10},
    )

    assert result == {}



@patch("http_client._chat")
def test_analysis_rejects_extra_field(mock_chat):
    import json

    analysis = valid_analysis()
    analysis["invented_market_size"] = "₹500 crore"
    mock_chat.return_value = json.dumps(analysis)

    result = analyze_venture(
        {"idea": "Student meal delivery"},
        {"monthly_revenue": 10000},
        {"profitability": 10},
    )

    assert result == {}


    
@patch("http_client._chat")
def test_analysis_rejects_invalid_json(mock_chat):
    mock_chat.return_value = "This is not valid JSON"

    result = analyze_venture(
        {"idea": "Student meal delivery"},
        {"monthly_revenue": 10000},
        {"profitability": 10},
    )

    assert result == {}



@patch("http_client._chat")
def test_analysis_handles_api_exception(mock_chat):
    mock_chat.side_effect = Exception("API connection failed")

    result = analyze_venture(
        {"idea": "Student meal delivery"},
        {"monthly_revenue": 10000},
        {"profitability": 10},
    )

    assert result == {}
    
@patch("http_client._chat")
def test_analysis_rejects_placeholder_risks(mock_chat):
    import json

    analysis = valid_analysis()
    analysis["key_risks"] = ["N/A", "Unknown", "No data"]
    mock_chat.return_value = json.dumps(analysis)

    result = analyze_venture(
        {"idea": "Student meal delivery"},
        {"monthly_revenue": 10000},
        {"profitability": 10},
    )

    assert result == {}


