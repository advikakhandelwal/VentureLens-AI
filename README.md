# VentureLens AI 🚀

**An AI-powered startup evaluation agent that helps founders evaluate business ideas through financial analysis, evidence-aware reasoning, and actionable recommendations.**

Built for the **ASI:One Agent Challenge — From Intent to Action**.

## Agent Details

- **Agent Name:** VentureLens AI
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)
- **Agent Address:**(https://agentverse.ai/agents/details/agent1q0rk9lamk3qxrrq8g05eh90khws3p2fjlkfjeu8934wmq7js2qpv5uncrtl/profile)
- **Platform:** ASI:One / Agentverse
- **Purpose:** Evaluates startup ideas through financial analysis, risk assessment, and actionable recommendations.

You can use the agent address to identify VentureLens AI on the agent network.


## Overview

VentureLens AI helps founders pressure-test startup ideas through a guided conversation. It collects essential business information, calculates financial metrics using Python, and uses ASI:One to generate a qualitative assessment.

By combining deterministic financial calculations with AI-powered analysis, VentureLens AI helps founders understand potential profitability, identify risks, and decide what to validate before investing significant time or money.

## Features

- **Guided startup evaluation:** Collects the business idea, target customers, location, selling price, expected monthly sales, fixed costs, and variable cost per sale.
- **Financial analysis:** Calculates estimated revenue, contribution per sale, break-even sales volume, and monthly profit or loss.
- **Transparent startup scoring:** Produces a score out of 100 with four components:
  - Margin quality — 25 points
  - Break-even feasibility — 25 points
  - Profitability — 25 points
  - Qualitative assessment — 25 points
- **AI-powered qualitative assessment:** Evaluates idea clarity, customer understanding, execution feasibility, demand evidence, and risk awareness.
- **Risk analysis:** Identifies three key risks, three improvements, and three actionable next steps.
- **Clear recommendations:** Provides a `PURSUE`, `REVISE`, or `VALIDATE` recommendation with reasoning.
- **Evidence-aware analysis:** Distinguishes founder-provided assumptions from verified information and identifies missing market or competitor evidence.
- **Follow-up conversations:** Supports questions about the evaluation and recalculation using updated financial assumptions.

## How It Works

1. **Founder input:** The founder describes the startup idea and provides available business and financial information.
2. **Information extraction:** The AI extracts structured fields from the conversation.
3. **Financial calculations:** Python calculates financial estimates and deterministic score components.
4. **Qualitative analysis:** ASI:One generates the qualitative score, market and competition commentary, risks, improvements, next actions, and recommendation.
5. **Report generation:** VentureLens AI combines the results into a structured evaluation.
6. **Follow-up:** The founder can ask questions or provide updated assumptions for recalculation.

## Financial Calculations

VentureLens AI uses Python for its financial calculations.

- **Revenue:** Selling price multiplied by expected sales volume.
- **Contribution per sale:** Selling price minus variable cost per sale.
- **Break-even sales volume:** Monthly fixed costs divided by contribution per sale, when contribution is positive.
- **Estimated monthly profit or loss:** Revenue minus variable costs and fixed costs.
- **Financial risk warning:** Highlights when the conservative financial scenario estimates a loss.

When the founder supplies minimum and maximum values, the agent uses them to estimate a range of possible financial outcomes.

All projections depend on the supplied assumptions and do not guarantee actual business performance.

## Technology Stack

- **Python** — financial calculations, validation, scoring, and application logic
- **uAgents** — agent framework
- **ASI:One** — AI-powered information extraction and qualitative analysis
- **OpenAI-compatible Python client** — communication with the configured AI API
- **pytest** — automated testing

## Project Structure

The main project components include:

| File or directory | Purpose |
|---|---|
| `agent.py` | Creates and runs the agent |
| `protocols.py` | Handles conversation flow, validation, financial calculations, scoring, and report generation |
| `http_client.py` | Handles AI API calls, information extraction, qualitative analysis, and follow-up responses |
| `requirements.txt` | Lists Python dependencies |
| `tests/` | Contains automated tests |

## Installation and Setup

### Prerequisites

- Python
- Git
- Access to the ASI:One API and authorised credentials
- The dependencies listed in `requirements.txt`

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/VentureLens-AI.git
cd VentureLens-AI
```

Replace `YOUR-USERNAME` with your GitHub username and update the repository URL if necessary.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

The hosted agent expects Agentverse to provide these environment variables:

- `ASI1_API_KEY`
- `ASI1_BASE_URL`

For local execution, configure these variables using your authorised API credentials and the appropriate API endpoint.

**Never commit API keys, passwords, or other private credentials to GitHub.**

### 5. Run the agent

```bash
python agent.py
```

For hosted deployment, follow the applicable Agentverse configuration and deployment instructions.

## Testing

Run the automated test suite from the project root:

```bash
python -m pytest -q
```

The tests help verify the implemented financial calculations, scoring logic, input validation, and other application functionality.

## Limitations

- A complete financial evaluation requires the startup idea and essential financial inputs, including selling price, expected monthly sales, fixed costs, and variable cost per sale.
- Market and competition analysis depends on the evidence available to the agent. Missing information does not prove that demand or competitors are absent.
- Financial projections are estimates based on founder-provided assumptions.
- The startup score is a decision-support framework, not a statistically validated prediction of startup success.
- Real customer demand, operating costs, and competitive conditions should be independently validated before making significant financial commitments.

## Future Improvements

Potential enhancements include:

- External market and competitor data integration
- Stronger evidence citations and source verification
- Improved handling of uncertain financial assumptions
- Expanded end-to-end testing
- Response-time monitoring and optimisation

## Disclaimer

VentureLens AI provides preliminary startup analysis for informational and decision-support purposes. It does not guarantee business success and should not replace independent market research or professional financial advice.

## Author

Developed for the **ASI:One Agent Challenge — From Intent to Action**.
