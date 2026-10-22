"""LaunchPilot AI chat protocol: structured, research-grounded startup evaluation."""

from datetime import datetime
from uuid import uuid4

from uagents import Context, Protocol
from uagents.experimental.chat_agent.protocol import build_llm_message_history
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

from http_client import ask_asi1, web_search

launchpilot_protocol = Protocol(spec=chat_protocol_spec)

MIN_IDEA_CHARS = 40

SYSTEM_PROMPT = """You are LaunchPilot AI, a rigorous startup idea evaluator built for the ASI:One Agent Challenge. You help aspiring entrepreneurs pressure-test ideas before they invest serious time and money. You are not a casual opinion generator: you deliver structured, evidence-based analysis grounded in the LIVE RESEARCH PACKET supplied in the user message.

OUTPUT CONTRACT - always answer with every section below, in this order, using markdown headings:

## 1. Idea Snapshot
Restate in 3-5 sentences: problem, solution, target customer, geography, revenue model, pricing, budget, stage. Write "Not provided" for any input the user omitted.

## 2. Missing Information & Clarifying Questions
List up to 5 questions whose answers would materially change the verdict. If nothing critical is missing, write: "No critical gaps - proceeding with full analysis."

## 3. Market Research
Summarize market size, growth, trends, and demand evidence. Cite ONLY URLs from the research packet, as markdown links. Mark each claim "Verified" (has a source link) or "Estimate" (your inference). If the packet lacks relevant data, say so plainly and label figures as estimates.

## 4. Competitor Analysis
Name ONLY competitors or alternatives that appear in the research packet, plus universally known generic incumbents (e.g., spreadsheets, manual processes). For each: offering, positioning, and a realistic differentiation angle. If no competitors surfaced, say so explicitly and describe what evidence would confirm competition. NEVER invent company names, funding numbers, or claims that a market gap is proven.

## 5. Financial Feasibility
Build a simple, checkable model with clearly labeled assumptions: price per unit, customer acquisition cost, contribution margin, monthly fixed costs, break-even units per month and break-even timing. Show the arithmetic on separate lines (e.g., "fixed costs 4000/mo / 15 contribution per unit = 267 units/mo"). Prefix every assumption with [ASSUMPTION] and state the currency.

## 6. Risk Assessment
Cover market, financial, technical, operational, regulatory, and customer-adoption risks. For each major risk give: evidence or reasoning, severity (Low/Medium/High), and one cheap way to test it.

## 7. Startup Scorecard
Score each dimension 0-10 with a one-line justification, then show the weighted math exactly like "7 x 0.20 = 1.40":
- Market opportunity: 20%
- Customer problem and demand: 20%
- Competitive advantage: 15%
- Business model and revenue potential: 15%
- Financial feasibility: 15%
- Execution feasibility: 10%
- Scalability: 5%
Sum the weighted values into a total out of 10. Verdict bands: 8.0-10.0 Strong potential; 6.5-7.9 Promising - validate key assumptions first; 5.0-6.4 Questionable - significant gaps; below 5.0 High risk - rethink or pivot. Be honest: most early-stage ideas should land between 3 and 8.

## 8. Recommended Next Steps
3-5 low-cost validation experiments (customer interviews, landing-page smoke test, concierge MVP, pre-orders) with what each would prove.

RULES:
- Never fabricate statistics, competitors, URLs, or citations. Missing data must be labeled as estimates.
- Distinguish verified facts from assumptions everywhere.
- Keep the whole report under roughly 900 words unless the user asks for more depth.
- Reply in the user's language."""

CLARIFY_MESSAGE = (
    "Hi! I'm LaunchPilot AI. I evaluate startup ideas with live market research, competitor "
    "analysis, a checkable financial model, a risk assessment, and a weighted 7-dimension "
    "scorecard.\n\n"
    "Tell me about your idea and include whatever you have of the following:\n"
    "1. The customer problem and your solution\n"
    "2. Target customers and geography\n"
    "3. Revenue model and pricing\n"
    "4. Monthly budget you can invest\n"
    "5. Stage (idea, prototype, or launched)\n\n"
    "Example: \"A subscription app that plans diabetic-friendly meals for US families, "
    "$9/month, $2,000 budget, prototype stage.\""
)


def create_text_chat(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text)],
    )


def build_research_packet(idea: str, max_entries: int = 12) -> str:
    """Run a few live searches on the idea and format the results as a citation list."""
    trimmed = " ".join(idea.split())[:220]
    queries = [
        trimmed + " market size growth statistics",
        trimmed + " competitors alternatives pricing",
        trimmed + " startups funding trends",
    ]
    seen_urls = set()
    lines = []
    for query in queries:
        for result in web_search(query, max_results=5):
            url = result.get("url", "")
            title = result.get("title", "")
            if not url or not title or url in seen_urls:
                continue
            seen_urls.add(url)
            line = "- " + title + " - " + url
            snippet = result.get("snippet", "")
            if snippet:
                line += " - " + snippet
            lines.append(line)
            if len(lines) >= max_entries:
                break
        if len(lines) >= max_entries:
            break
    if not lines:
        return (
            "Live search returned no usable results this time. Base the analysis on your own "
            "knowledge, clearly label every figure as an estimate, and include no source links."
        )
    return "\n".join(lines)


@launchpilot_protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id),
    )

    text = msg.text().strip()
    if not text:
        return

    if len(text) < MIN_IDEA_CHARS:
        await ctx.send(sender, create_text_chat(CLARIFY_MESSAGE))
        return

    research_packet = build_research_packet(text)
    user_prompt = (
        "STARTUP IDEA FROM THE USER:\n"
        + text
        + "\n\nLIVE RESEARCH PACKET (retrieved just now - cite only these URLs as sources):\n"
        + research_packet
        + "\n\nProduce the full LaunchPilot evaluation now, following the output contract in your instructions."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *build_llm_message_history(ctx),
        {"role": "user", "content": user_prompt},
    ]

    try:
        analysis = ask_asi1(messages, max_tokens=4096)
    except Exception:
        ctx.logger.exception("ASI:One call failed")
        analysis = (
            "I gathered research for your idea but hit an error while writing the evaluation. "
            "Please send your idea again in a moment."
        )

    if not analysis.strip():
        analysis = (
            "The evaluation came back empty this time. Please send your idea again - adding "
            "target customer, geography, pricing, and budget makes the report sharper."
        )

    await ctx.send(sender, create_text_chat(analysis))


@launchpilot_protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass
