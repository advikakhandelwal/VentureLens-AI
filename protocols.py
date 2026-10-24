from datetime import datetime
from uuid import uuid4
import math
from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

from http_client import analyze_venture, extract_fields, free_chat

venture_protocol = Protocol(spec=chat_protocol_spec)

SESSION_KEY_PREFIX = "session:"


FIELD_QUESTIONS = {
    "idea": "What is your startup idea? Describe the product or service in a sentence or two.",
    "target_customers": "Who are your target customers?",
    "location": "Where will you operate (city or country)?",
    "price_min": "What is the lowest selling price of your products, in INR (₹)?",
    "price_max": "What is the highest selling price of your products, in INR (₹)?",
    "expected_monthly_sales_min": "What is the minimum number of sales you expect per month?",
    "expected_monthly_sales_max": "What is the maximum number of sales you expect per month?",
    "fixed_costs": "What are your total fixed costs per month in INR (₹), including rent, salaries and software?",
    "variable_cost_per_sale_min": "What is the lowest variable cost to deliver one sale, in INR (₹)?",
    "variable_cost_per_sale_max": "What is the highest variable cost to deliver one sale, in INR (₹)?",
}

FIELD_LABELS = {
    "idea": "Startup idea",
    "target_customers": "Target customers",
    "location": "Location",
    "price_min": "Lowest selling price",
    "price_max": "Highest selling price",
    "expected_monthly_sales_min": "Minimum monthly sales",
    "expected_monthly_sales_max": "Maximum monthly sales",
    "fixed_costs": "Monthly fixed costs",
    "variable_cost_per_sale_min": "Lowest variable cost per sale",
    "variable_cost_per_sale_max": "Highest variable cost per sale",
}

REQUIRED_FIELDS = [
    "idea",
    "price_min",
    "price_max",
    "expected_monthly_sales_min",
    "expected_monthly_sales_max",
    "fixed_costs",
    "variable_cost_per_sale_min",
    "variable_cost_per_sale_max",
]

OPTIONAL_FIELDS = ["target_customers", "location"]

NUMERIC_KEYS = {
    "price_min",
    "price_max",
    "expected_monthly_sales_min",
    "expected_monthly_sales_max",
    "fixed_costs",
    "variable_cost_per_sale_min",
    "variable_cost_per_sale_max",
}

TEXT_KEYS = {"idea", "target_customers", "location"}


RESET_COMMANDS = {"reset", "restart", "start over", "new evaluation", "new idea"}

INTRO = (
    "I am VentureLens AI, a startup idea evaluator. I calculate revenue, contribution per sale, break-even "
    "volume and estimated monthly profit or loss with exact Python math, then give a transparent score out of "
    "100, market and competition notes, key risks, three improvements, three next actions and a pursue / "
    "revise / validate recommendation."
)


def is_new_idea_message(text: str) -> bool:
    text = text.strip().lower()

    new_idea_phrases = (
        "i want to start",
        "i want to launch",
        "my new idea",
        "new business idea",
        "evaluate a new idea",
        "start a new business",
        "evaluate another idea",
        "another business idea",
        "different business idea",
        "new startup idea",
        "let's start a new idea",
        "let's evaluate another idea",
    )

    return any(phrase in text for phrase in new_idea_phrases)

@venture_protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
    )

    text = msg.text()
    if not text:
        return

    session_key = SESSION_KEY_PREFIX + sender
    state = ctx.storage.get(session_key) or {
        "fields": {},
        "stage": "collecting",
    }

    if (
        state.get("stage") == "evaluated"
        and is_new_idea_message(text)
    ):
        state = {
            "fields": {},
            "stage": "collecting",
        }
        ctx.storage.set(session_key, state)

        await send_text(
            ctx,
            sender,
            INTRO + "\n\nLet's begin:\n1. " + FIELD_QUESTIONS["idea"],
        )
        return

    fields = state.get("fields") or {}

    if text.strip().lower() in RESET_COMMANDS:
        ctx.storage.set(session_key, {"fields": {}, "stage": "collecting"})
        await send_text(ctx, sender, INTRO + "\n\nLet's begin:\n1. " + FIELD_QUESTIONS["idea"])
        return

    # If the user includes a new-idea prefix, remove it before extraction.
    input_text = text.strip()

    # Remove a leading agent mention, if present.
    if input_text.startswith("@") and " " in input_text:
        input_text = input_text.split(" ", 1)[1].strip()

    # Remove common new-idea prefixes.
    prefixes = (
        "new startup idea:",
        "new business idea:",
        "new idea:",
    )

    for prefix in prefixes:
        if input_text.lower().startswith(prefix):
            input_text = input_text[len(prefix):].strip()
            break

    try:
        raw = extract_fields(input_text, fields)
    except Exception as exc:
        ctx.logger.warning(f"Input extraction failed: {exc}")
        raw = {}

    extracted = coerce_fields(raw if isinstance(raw, dict) else {})
    if extracted:
        fields.update(extracted)
        state["fields"] = fields

    if not fields:
        state["stage"] = "collecting"
        ctx.storage.set(session_key, state)
        await send_text(ctx, sender, build_follow_up({}, missing_required({})))
        return

    if state.get("stage") == "evaluated" and not extracted:
        try:
            reply = free_chat(text, fields, state.get("last_report") or "")
        except Exception as exc:
            ctx.logger.warning(f"Follow-up chat failed: {exc}")
            reply = (
                "I could not process that just now. Send updated numbers (price per sale, expected monthly "
                "sales, monthly fixed costs, variable cost per sale) to re-run the evaluation, or say "
                "'reset' to start over."
            )
        await send_text(ctx, sender, reply)
        return

    missing = missing_required(fields)
    if missing:
        state["stage"] = "collecting"
        ctx.storage.set(session_key, state)
        await send_text(ctx, sender, build_follow_up(fields, missing))
        return

    report = build_report(ctx, fields)
    state["stage"] = "evaluated"
    state["last_report"] = report
    ctx.storage.set(session_key, state)
    await send_text(ctx, sender, report)


@venture_protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass




def coerce_fields(raw: dict) -> dict:
    cleaned = {}

    for key, value in raw.items():
        if key in NUMERIC_KEYS:
            number = None

            if isinstance(value, bool):
                continue
            elif isinstance(value, (int, float)):
                number = float(value)
            elif isinstance(value, str):
                try:
                    number = float(
                        value.replace("₹", "")
                        .replace("$", "")
                        .replace(",", "")
                        .strip()
                    )
                except ValueError:
                    continue

            if number is None or not math.isfinite(number):
                continue

            if key in {
                "price_min",
                "price_max",
                "expected_monthly_sales_min",
                "expected_monthly_sales_max",
            } and number <= 0:
                continue

            if key in {
                "expected_monthly_sales_min",
                "expected_monthly_sales_max",
            } and not number.is_integer():
                continue

            if key in {
                "fixed_costs",
                "variable_cost_per_sale_min",
                "variable_cost_per_sale_max",
            } and number < 0:
                continue

            cleaned[key] = number

        elif key in TEXT_KEYS:
            if value is None:
                continue

            text_value = str(value).strip()
            if text_value:
                cleaned[key] = text_value

    # Reject an invalid range instead of silently reversing it.
    range_pairs = [
        ("price_min", "price_max"),
        ("expected_monthly_sales_min", "expected_monthly_sales_max"),
        ("variable_cost_per_sale_min", "variable_cost_per_sale_max"),
    ]

    for minimum_key, maximum_key in range_pairs:
        minimum = cleaned.get(minimum_key)
        maximum = cleaned.get(maximum_key)

        if minimum is not None and maximum is not None and minimum > maximum:
            cleaned.pop(minimum_key, None)
            cleaned.pop(maximum_key, None)

    return cleaned

def missing_required(fields: dict) -> list:
    missing = []

    for key in REQUIRED_FIELDS:
        if key not in fields or fields[key] is None:
            missing.append(key)
        elif key in {"idea"} and not str(fields[key]).strip():
            missing.append(key)

    return missing


def _money(value: float) -> str:
    return f"₹{value:,.2f}"


def _count(value: float) -> str:
    return f"{value:,.0f}"


def _format_field(key: str, value) -> str:
    if key == "expected_monthly_sales":
        return f"{float(value):,.0f} sales/month"

    if key in {"price", "fixed_costs", "variable_cost_per_sale"}:
        suffix = "/month" if key == "fixed_costs" else ""
        return f"₹{float(value):,.2f}{suffix}"

    return str(value)


def build_follow_up(fields: dict, missing: list) -> str:
    lines = []
    known = [key for key in FIELD_LABELS if fields.get(key)]
    if known:
        lines.append("Noted. Here is what I have so far:")
        for key in known:
            lines.append(f"- {FIELD_LABELS[key]}: {_format_field(key, fields[key])}")
        lines.append("")
        lines.append("To run the evaluation I still need:")
        for index, key in enumerate(missing, start=1):
            lines.append(f"{index}. {FIELD_QUESTIONS[key]}")
    else:
        lines.append(INTRO)
        lines.append("")
        lines.append("Let's begin:")
        for index, key in enumerate(missing, start=1):
            lines.append(f"{index}. {FIELD_QUESTIONS[key]}")
        lines.append("")
        lines.append("Optional, but it sharpens the market and competition analysis:")
        for key in OPTIONAL_FIELDS:
            lines.append(f"- {FIELD_QUESTIONS[key]}")
    return "\n".join(lines)


def compute_financials(fields: dict) -> dict:
    price_min = float(fields["price_min"])
    price_max = float(fields["price_max"])

    sales_min = float(fields["expected_monthly_sales_min"])
    sales_max = float(fields["expected_monthly_sales_max"])

    fixed_costs = float(fields["fixed_costs"])

    variable_min = float(fields["variable_cost_per_sale_min"])
    variable_max = float(fields["variable_cost_per_sale_max"])

    # Use conservative assumptions for the lower estimate.
    revenue_min = price_min * sales_min
    revenue_max = price_max * sales_max

    profit_min = revenue_min - (variable_max * sales_min) - fixed_costs
    profit_max = revenue_max - (variable_min * sales_max) - fixed_costs

    # Use midpoint assumptions for the existing deterministic scoring.
    price = (price_min + price_max) / 2
    expected_sales = (sales_min + sales_max) / 2
    variable_cost = (variable_min + variable_max) / 2

    revenue = price * expected_sales
    contribution_per_sale = price - variable_cost
    total_variable_costs = variable_cost * expected_sales
    monthly_profit = revenue - total_variable_costs - fixed_costs

    if contribution_per_sale > 0:
        break_even_sales = fixed_costs / contribution_per_sale
        break_even_text = f"{math.ceil(break_even_sales):,} sales/month"
    else:
        break_even_sales = None
        break_even_text = (
            f"Not achievable under midpoint assumptions: price {_money(price)} "
            f"does not cover variable cost {_money(variable_cost)} per sale"
        )

    if price_min > variable_max:
        break_even_min = math.ceil(fixed_costs / (price_max - variable_min)) if price_max > variable_min else None
        break_even_max = math.ceil(fixed_costs / (price_min - variable_max))
    else:
        break_even_min = None
        break_even_max = None

    margin_ratio = contribution_per_sale / price if price > 0 else 0.0
    profit_margin = monthly_profit / revenue if revenue > 0 else 0.0

    return {
        "price": price,
        "price_min": price_min,
        "price_max": price_max,
        "expected_monthly_sales": expected_sales,
        "expected_monthly_sales_min": sales_min,
        "expected_monthly_sales_max": sales_max,
        "fixed_costs": fixed_costs,
        "variable_cost_per_sale": variable_cost,
        "variable_cost_per_sale_min": variable_min,
        "variable_cost_per_sale_max": variable_max,
        "monthly_revenue_min": revenue_min,
        "monthly_revenue_max": revenue_max,
        "monthly_profit_min": profit_min,
        "monthly_profit_max": profit_max,
        "monthly_revenue": revenue,
        "contribution_per_sale": contribution_per_sale,
        "total_variable_costs": total_variable_costs,
        "estimated_monthly_profit": monthly_profit,
        "break_even_sales_per_month": break_even_sales,
        "break_even_sales_min": break_even_min,
        "break_even_sales_max": break_even_max,
        "break_even_text": break_even_text,
        "contribution_margin_ratio": margin_ratio,
        "profit_margin_ratio": profit_margin,
    }

def compute_deterministic_score(fin: dict) -> dict:
    margin_ratio = fin["contribution_margin_ratio"]
    margin_points = 25.0 * max(0.0, min(margin_ratio, 0.5)) / 0.5

    break_even = fin["break_even_sales_per_month"]

    if break_even is None:
        break_even_points = 0.0
    else:
        expected_sales = fin["expected_monthly_sales"]
        low_sales = fin["expected_monthly_sales_min"]
        low_profit = fin["monthly_profit_min"]

        coverage = (
            break_even / expected_sales
            if expected_sales > 0
            else 2.0
        )

        if coverage <= 0.5:
            break_even_points = 25.0
        elif coverage <= 1.0:
            break_even_points = 25.0 - (coverage - 0.5) * 30.0
        else:
            break_even_points = max(
                0.0,
                10.0 - (coverage - 1.0) * 10.0
            )

        # Reduce the score when the conservative scenario makes a loss.
        if low_profit < 0 and low_sales < break_even:
            break_even_points = min(break_even_points, 15.0)

        break_even_points = max(0.0, min(25.0, break_even_points))

    profit_margin = fin["profit_margin_ratio"]
    monthly_profit = fin["estimated_monthly_profit"]
    low_profit = fin["monthly_profit_min"]

    if monthly_profit <= 0:
        profit_points = 0.0
    elif low_profit < 0:
        profit_points = 10.0 * min(profit_margin / 0.2, 1.0)
    elif profit_margin >= 0.2:
        profit_points = 25.0
    else:
        profit_points = 25.0 * profit_margin / 0.2

    return {
        "margin_quality": round(margin_points, 1),
        "break_even_feasibility": round(break_even_points, 1),
        "profitability": round(profit_points, 1),
    }


def _as_list(value, limit: int) -> list:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items[:limit]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def build_report(ctx: Context, fields: dict) -> str:
    fin = compute_financials(fields)
    parts = compute_deterministic_score(fin)
    subtotal = sum(parts.values())

    analysis = None
    try:
        analysis = analyze_venture(fields, fin, parts)
    except Exception as exc:
        ctx.logger.warning(f"Qualitative analysis failed: {exc}")

    qualitative = 0.0
    score_note = "Qualitative assessment unavailable in this run."
    market_text = ""
    competition_text = ""
    risks = []
    improvements = []
    actions = []
    recommendation = "VALIDATE"
    recommendation_reason = (
        "Qualitative analysis was unavailable; validate the core assumptions before deciding."
    )

    if isinstance(analysis, dict) and analysis:
        try:
            qualitative = max(
                0.0,
                min(25.0, float(analysis.get("qualitative_score", 0)))
            )
        except (TypeError, ValueError):
            qualitative = 0.0

        note = str(analysis.get("score_notes") or "").strip()
        if note:
            score_note = note

        market_text = str(analysis.get("market_analysis") or "").strip()
        competition_text = str(
            analysis.get("competition_analysis") or ""
        ).strip()

        if not fields.get("competitors"):
            competition_text = (
                "No competitor information was provided by the founder. "
                "Competitor claims have not been verified."
            )

        risks = _as_list(analysis.get("key_risks"), 3)
        improvements = _as_list(analysis.get("improvements"), 3)
        actions = _as_list(analysis.get("next_actions"), 3)

        candidate = str(
            analysis.get("recommendation") or ""
        ).strip().upper()

        if candidate in {"PURSUE", "REVISE", "VALIDATE"}:
            recommendation = candidate

        reason = str(
            analysis.get("recommendation_reason") or ""
        ).strip()

        if reason:
            recommendation_reason = reason

    total = int(round(min(100.0, subtotal + qualitative)))

    lines = ["VENTURE FINANCIALS (calculated)"]

    if fields.get("idea"):
        lines.append(f"Idea: {fields['idea']}")

    lines.append(
        f"Monthly revenue range: "
        f"{_money(fin['monthly_revenue_min'])} - "
        f"{_money(fin['monthly_revenue_max'])}"
    )

    lines.append(
        f"Estimated monthly profit/loss range: "
        f"{_money(fin['monthly_profit_min'])} - "
        f"{_money(fin['monthly_profit_max'])}"
    )

    lines.append(
        f"Selling price range: {_money(fin['price_min'])} - "
        f"{_money(fin['price_max'])}"
    )

    lines.append(
        f"Expected monthly sales: "
        f"{_count(fin['expected_monthly_sales_min'])} - "
        f"{_count(fin['expected_monthly_sales_max'])}"
    )

    lines.append(
        f"Variable cost per sale: "
        f"{_money(fin['variable_cost_per_sale_min'])} - "
        f"{_money(fin['variable_cost_per_sale_max'])}"
    )

    lines.append(
        f"Monthly fixed costs: {_money(fin['fixed_costs'])}"
    )

    lines.append(
        f"Midpoint contribution per sale: "
        f"{_money(fin['contribution_per_sale'])}"
    )

    lines.append(f"Break-even volume: {fin['break_even_text']}")

    lines.append("")
    lines.append(f"STARTUP SCORE: {total}/100")

    lines.append("")

    if fin["monthly_profit_min"] < 0:
        lines.append("FINANCIAL RISK WARNING")
        lines.append(
            f"The conservative scenario estimates a monthly loss of "
            f"{_money(abs(fin['monthly_profit_min']))}."
        )
        lines.append(
            "Validate customer demand and actual costs before committing "
            "to significant spending. The startup score does not guarantee viability."
        )
    else:
        lines.append(
            "The conservative financial scenario is profitable under the "
            "supplied assumptions. This does not confirm actual market demand."
        )

    coverage_text = ""

    if (
        fin["break_even_sales_per_month"] is not None
        and fin["expected_monthly_sales"] > 0
    ):
        coverage = (
            fin["break_even_sales_per_month"]
            / fin["expected_monthly_sales"]
        )
        coverage_text = (
            f" (break-even at {coverage * 100:.0f}% of midpoint expected sales)"
        )

    lines.append(
        f"- Margin quality: {parts['margin_quality']:.1f}/25 "
        f"(contribution margin "
        f"{fin['contribution_margin_ratio'] * 100:.0f}%)"
    )

    lines.append(
        f"- Break-even feasibility: "
        f"{parts['break_even_feasibility']:.1f}/25{coverage_text}"
    )

    lines.append(
        f"- Profitability: {parts['profitability']:.1f}/25 "
        f"(midpoint profit margin "
        f"{fin['profit_margin_ratio'] * 100:.0f}%)"
    )

    lines.append(
        f"- Qualitative assessment: {qualitative:.1f}/25 - {score_note}"
    )

    lines.append("")
    lines.append("MARKET & COMPETITION")

    if market_text or competition_text:
        if market_text:
            lines.append(market_text)
        if competition_text:
            lines.append(competition_text)
    else:
        lines.append(
            "No market or competitor evidence was provided, so I will not speculate. "
            "Tell me about your market and competitors and I will factor it into "
            "the next evaluation."
        )

    lines.append("")
    lines.append("KEY RISKS")

    if risks:
        for index, item in enumerate(risks, start=1):
            lines.append(f"{index}. {item}")
    else:
        lines.append("Risk analysis unavailable in this run.")

    lines.append("")
    lines.append("THREE IMPROVEMENTS")

    if improvements:
        for index, item in enumerate(improvements, start=1):
            lines.append(f"{index}. {item}")
    else:
        lines.append("Improvement suggestions unavailable in this run.")

    lines.append("")
    lines.append("THREE NEXT ACTIONS")

    if actions:
        for index, item in enumerate(actions, start=1):
            lines.append(f"{index}. {item}")
    else:
        lines.append("Next actions unavailable in this run.")

    lines.append("")
    lines.append(f"RECOMMENDATION: {recommendation}")

    if recommendation_reason:
        lines.append(recommendation_reason)

    lines.append("")
    lines.append(
        "Send updated numbers any time and I will recalculate, "
        "or say 'reset' to evaluate a new idea."
    )

    return "\n".join(lines)

def _text_chat(text: str) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    return ChatMessage(timestamp=datetime.utcnow(), msg_id=uuid4(), content=content)


async def send_text(ctx: Context, sender: str, text: str) -> None:
    await ctx.send(sender, _text_chat(text))

