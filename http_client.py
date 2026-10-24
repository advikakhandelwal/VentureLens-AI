import json
import os
import time
from openai import OpenAI

MODEL = "asi1-mini"

# Agentverse injects ASI1_API_KEY and ASI1_BASE_URL into every hosted agent.
client = OpenAI(
    api_key=os.environ["ASI1_API_KEY"],
    base_url=os.environ["ASI1_BASE_URL"],
)



def _chat(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    start_time = time.perf_counter()

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
    )

    elapsed = time.perf_counter() - start_time
    print(f"[VentureLens] AI API call took {elapsed:.2f} seconds")

    return completion.choices[0].message.content or ""



def _parse_json_object(raw: str) -> dict:
    if not raw:
        return {}
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}



EXTRACTION_SYSTEM_PROMPT = (
    "You extract structured facts from a founder's message for a startup evaluation assistant. "
    "Return ONLY a JSON object with exactly these keys: "
    '{"idea": string, "target_customers": string, "location": string, '
    '"price_min": number, "price_max": number, '
    '"expected_monthly_sales_min": number, "expected_monthly_sales_max": number, '
    '"fixed_costs": number, '
    '"variable_cost_per_sale_min": number, "variable_cost_per_sale_max": number}. '
    "Use null for anything the founder did not explicitly state in the message. "
    "price_min and price_max are the lowest and highest selling prices in INR. "
    "expected_monthly_sales_min and expected_monthly_sales_max are the minimum "
    "and maximum expected monthly sales. "
    "fixed_costs is total monthly fixed costs in INR. "
    "variable_cost_per_sale_min and variable_cost_per_sale_max are the lowest "
    "and highest variable costs per sale in INR. "
    "Convert shorthand such as '2k' to 2000, '2 lakh' to 200000, "
    "and '₹2,000 a month' to 2000. "
    "Remove currency symbols and commas from numeric values in the JSON. "
    "Never assume that the lowest price or cost equals the highest. "
    "Never invent missing values. Return valid JSON only."
)

def extract_fields(user_message: str, known_fields: dict) -> dict:
    prompt = (
        f"Known fields so far: {json.dumps(known_fields or {})}\n"
        f"Founder message: {user_message}"
    )

    try:
        raw = _chat(EXTRACTION_SYSTEM_PROMPT, prompt, max_tokens=400)
    except Exception:
        return {}

    data = _parse_json_object(raw)

    
    allowed_keys = {
        "idea",
        "target_customers",
        "location",
        "price_min",
        "price_max",
        "expected_monthly_sales_min",
        "expected_monthly_sales_max",
        "fixed_costs",
        "variable_cost_per_sale_min",
        "variable_cost_per_sale_max",
    }

    if not isinstance(data, dict) or not set(data).issubset(allowed_keys):
        return {}

    return data


ANALYSIS_SYSTEM_PROMPT = (
    "You are VentureLens AI, a strict but fair and evidence-based startup analyst. "
    "You receive founder-provided inputs and financial results calculated by Python. "
    "Trust the Python financial results exactly. Never recalculate, contradict, or change them. "

    "Score the qualitative part from 0 to 25 using these five existing criteria, "
    "each worth 0 to 5 points: "
    "idea clarity, customer understanding, execution feasibility, "
    "evidence supporting demand, and risk awareness and validation readiness. "

    "Use the following scoring principles for all five criteria: "
    "0 means no usable information or an extremely serious demonstrated weakness; "
    "1 means very limited support; "
    "2 means partial support with important gaps; "
    "3 means reasonably good support with some gaps; "
    "4 means strong support with minor gaps; "
    "5 means excellent support for that specific criterion. "

    "Be fair to early-stage founders. Do not require a launched business, "
    "existing revenue, a completed product, or proven market traction to award "
    "good points for idea clarity, customer understanding, or execution feasibility. "
    "A clear problem, identifiable target customers, a plausible solution, "
    "and a realistic initial execution approach can earn meaningful partial or good credit. "

    "Judge each criterion independently. Missing demand validation must primarily "
    "limit the evidence supporting demand score; do not automatically penalize "
    "idea clarity, customer understanding, or execution feasibility for the same gap. "
    "For risk awareness and validation readiness, reward a sensible validation plan "
    "or clear awareness of risks when the founder actually provides that information. "

    "Distinguish information that is missing from evidence that a plan is weak. "
    "Do not assume that missing information proves the idea is bad or infeasible. "
    "However, do not award points for strengths that the provided inputs do not support. "
    "A plausible idea is not proof of market demand. "
    "Do not confuse a founder's sales forecast with proven customer demand. "
    "Do not claim that this score is a statistically validated prediction of startup success. "

    "Analyze the market using only the information provided. "
    "Do not invent market size, growth rates, demand, customer behavior, or statistics. "
    "Do not invent competitor names, prices, market shares, or features. "
    "If no competitor evidence was supplied, clearly say that competitor information "
    "was not provided and competitor claims have not been verified. "
    "Distinguish founder assumptions from verified facts. "

    "Return ONLY one valid JSON object with exactly these keys: "
    '{"qualitative_score": integer from 0 to 25, '
    '"score_notes": one short sentence explaining the score and major evidence gaps, '
    '"market_analysis": 2-4 sentences grounded in the provided inputs, '
    '"competition_analysis": 2-4 sentences grounded in provided competitor evidence, '
    '"key_risks": array of exactly 3 concise risk statements, '
    '"improvements": array of exactly 3 concrete improvements, '
    '"next_actions": array of exactly 3 actionable next steps, '
    '"recommendation": exactly one of "PURSUE", "REVISE", "VALIDATE", '
    '"recommendation_reason": 1-2 sentences explaining the recommendation}. '

    "Be conservative, specific, and honest about uncertainty. "
    "Plain JSON only. No Markdown fences or extra commentary."
)

def analyze_venture(fields: dict, financials: dict, score_parts: dict) -> dict:
    payload = {
        "founder_inputs": fields,
        "calculated_financials": financials,
        "deterministic_score_subtotal": score_parts,
        "remaining_points_available": 25,
    }


    try:
        raw = _chat(
            ANALYSIS_SYSTEM_PROMPT,
            json.dumps(payload),
            max_tokens=1800,
        )
    except Exception:
        return {}

    data = _parse_json_object(raw)

    required_keys = {
        "qualitative_score",
        "score_notes",
        "market_analysis",
        "competition_analysis",
        "key_risks",
        "improvements",
        "next_actions",
        "recommendation",
        "recommendation_reason",
    }

    if set(data.keys()) != required_keys:
        return {}

    score = data["qualitative_score"]
    if type(score) is not int or not 0 <= score <= 25:
        return {}

    if data["recommendation"] not in {"PURSUE", "REVISE", "VALIDATE"}:
        return {}

    text_keys = [
        "score_notes",
        "market_analysis",
        "competition_analysis",
        "recommendation_reason",
    ]

    if any(
        not isinstance(data[key], str) or not data[key].strip()
        for key in text_keys
    ):
        return {}

    list_keys = ["key_risks", "improvements", "next_actions"]
    invalid_values = {"n/a", "na", "unknown", "no data", "none", "null", "tbd"}

    for key in list_keys:
        value = data[key]

        if (
            not isinstance(value, list)
            or len(value) != 3
            or any(
                not isinstance(item, str)
                or not item.strip()
                or item.strip().lower() in invalid_values
                for item in value
            )
        ):
            return {}

    return data



FREE_CHAT_SYSTEM_PROMPT = (
    "You are VentureLens AI, a startup evaluation assistant on the Fetch.ai Agentverse. "
    "The founder has already received a full evaluation. Answer their follow-up briefly "
    "and honestly. Never invent market data, statistics or competitor evidence. "
    "If they want different results, tell them to send updated numbers "
    "(price per sale, expected monthly sales, monthly fixed costs, variable cost per sale) "
    "and the evaluation will be recalculated."
)


def free_chat(user_message: str, fields: dict, last_report: str) -> str:
    context = {
        "founder_inputs": fields,
        "last_evaluation": (last_report or "")[:3500],
    }
    reply = _chat(
        FREE_CHAT_SYSTEM_PROMPT,
        f"Context: {json.dumps(context)}\nFounder message: {user_message}",
        max_tokens=700,
    )
    return reply.strip() or "Could you rephrase that? You can also send updated numbers to re-run the evaluation."
