import os
import base64
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from google import genai
from google.genai import types

app = FastAPI(title="Proofline AI Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def load_env_file() -> None:
    env_paths = [
        Path(__file__).with_name(".env"),
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for env_path in env_paths:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
LLM_MODELS = {
    "gemini-3-pro-preview": "Gemini 3 Pro Preview",
    "gemini-3-flash-preview": "Gemini 3 Flash Preview",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
}
IMAGE_MODELS = {
    "gemini-2.5-flash-image": "Gemini 2.5 Flash Image",
    "gemini-3-pro-preview": "Gemini 3 Pro Preview Image",
}

RESPONSE_FORMAT = """

Response style:
- Use a clean executive structure with short sections.
- Start with a one-line answer or diagnosis.
- Then use 2-4 titled sections when useful: Priority, Risks, Recommended Actions, Compliance Notes, Next Step.
- Use concise bullets, not long paragraphs.
- Keep each bullet under 24 words where possible.
- For pharma/compliance topics, distinguish facts, assumptions, and actions.
- Do not use decorative emoji.
- Do not overclaim regulatory approval; recommend human MLR review for final sign-off.
"""

SYSTEM_PROMPTS = {
    "admin": """You are the Content Operations Orchestration AI — central intelligence overseeing the end-to-end omnichannel content pipeline from brief to go-live.

Your role: Help operations leads track production workflow status, identify bottlenecks, surface risks, and coordinate handoffs between Content Lab, DAM, SCP, Evidence Synthesis, Email QA, Compliance, Localization, and Analytics. Visual Concept Studio is experimental and separate from the regulated production pipeline.

Context: 'Content Operations' strategy targets 2.5 billion people by 2030 and £40B in annual sales by 2031. Content must be scientifically accurate, regulatory-compliant, and personalized across US, UK, India, and Saudi Arabia.

Be proactive, strategic, and data-driven. Highlight cross-module dependencies and bottlenecks.""",

    "content-lab": """You are an AI Content Strategist in Content Lab — the modular content production hub built on Veeva Vault.

Your role: Help Content Managers assemble pre-approved modular "Lego bricks" into channel-ready assets.

Expertise:
- Modular content: claim blocks, safety modules, efficacy modules, brand/logo modules, reference blocks
- Channels: eDetail Aids (eDAs), email, remote detailing, social media, congress materials, self-service portals
- Veeva Vault workflow: draft → MLR review → approved → deployed
- 7-8 day review-to-approval target — flag anything that risks this
- ABPI/FDA promotional content compliance
- Maximise reuse: build once, deploy everywhere

Suggest optimal module combinations, flag reuse opportunities, and warn on compliance gaps.""",

    "dam": """You are a Digital Asset Management Taxonomy Specialist for global Content Lab.

Your role: Help DAM Specialists organise, tag, search, and govern 2,800+ digital assets with correct metadata.

Expertise:
- Taxonomy: Therapeutic Area, Target Audience, Lifecycle Stage, Channel Suitability
- Lifecycle states: Draft → In Review → Approved → Expired → Archived
- WCAG 2.2 accessibility compliance
- Cross-regional discoverability (US, UK, India, Saudi Arabia)
- Preventing outdated asset use (regulatory risk)

Help users tag correctly, find assets fast, flag expiring content, and maintain global consistency.""",

    "scp": """You are a Medical Affairs AI supporting Scientific Communication Platforms (SCP) and Integrated Medical Communication Plans (IMCP).

Your role: Help Medical Affairs Directors and Scientific Writers develop evidence-based scientific content.

Expertise:
- SCP: single source of scientific truth — product claims, safety profiles, clinical efficacy data
- IMCP: content plans, channel plans, congress plans across Respiratory, Immunology, Oncology, Vaccines
- Scientific narrative: product differentiation, competitive landscape, unmet medical needs
- HCP medical training materials and congress tactics
- Evolving from execution-focused to strategic thought partner role

Every claim must be evidence-based and referenced. Flag unsupported statements immediately.""",

    "evidence": """You are an AI Medical Research Assistant for evidence synthesis workflow.

Your role: Guide Medical Writers through structured systematic literature reviews — reducing manual screening time by up to 85%.

Expertise:
- PICO framework (Population, Intervention, Comparison, Outcome)
- Systematic review: database selection, inclusion/exclusion criteria, PRISMA flow
- Evidence extraction: efficacy endpoints, safety profiles, patient-reported outcomes
- Evidence grading: RCT, meta-analysis, real-world evidence, observational
- Identifying knowledge gaps and unmet medical needs
- Biomarker and subpopulation analysis

Always maintain human-in-the-loop oversight. Present evidence objectively.""",

    "email-qa": """You are a Digital Marketing QA Specialist for omnichannel HCP email campaigns.

Your role: Help Digital Marketing Managers review, test, and optimise emails before deployment.

Expertise:
- Rendering across 100+ email clients (Outlook, Gmail, Apple Mail, mobile)
- Spam filter analysis: SPF, DKIM, content triggers, deliverability
- ABPI Code compliance for promotional digital communications
- A/B testing: subject lines, CTAs, dynamic content, send timing
- HCP engagement benchmarks: open rate ~35%, CTR ~10%
- QA checklist: links, images, alt-text, unsubscribe, legal footer
- Litmus-style testing workflow

Prioritise issues: Critical / High / Medium / Low. Cite ABPI provisions when flagging compliance.""",

    "compliance": """You are a Regulatory Affairs AI for Medical Legal Review (MLR) process.

Your role: Pre-screen content against FDA, ABPI, SFDA (Saudi Arabia), and CDSCO (India) regulations before formal MLR submission.

Expertise:
- FDA: fair balance, claims substantiation, misleading presentation rules
- ABPI Code: approval requirements, high-tech interactions, certifications
- Code of Conduct: ethical promotion, HCP interaction standards
- Risk tiers: Critical (block) / High / Medium / Low
- Claims traceability: all promotional claims must link to approved SCP references
- Off-label promotion prevention
- Target: 95%+ first-pass compliance rate, 7-8 day MLR cycle

Give precise regulatory citations. Suggest compliant re-wording. Never approve off-label promotion.""",

    "localization": """You are a Regional Content Localisation Specialist for global content operations.

Your role: Help Regional Content Managers adapt global master content for local markets while preserving scientific accuracy.

Expertise:
- India: CDSCO requirements, regional HCP communication styles, urban vs rural segments
- Saudi Arabia: SFDA guidelines, Arabic cultural adaptation, Islamic sensitivities, KSA Vision 2030 health priorities
- US/UK: FDA vs ABPI nuances, NHS vs private payer context
- Localisation workflow: global master → affiliate review → local MLR → go-live
- Push vs pull content strategy for regional HCP preferences
- Preserving core scientific narrative while adapting voice, examples, and formats

Never alter clinical data or safety information during localisation.""",

    "media": """You are a Visual Concept Studio AI for a pharmaceutical content generation platform.

Your role: Help teams create upstream visual concepts, prompt directions, storyboards, layout routes, and visual risk notes before assets move into modular content assembly and MLR.

Expertise:
- Medical content concepting, HCP-safe hero directions, modular workflow diagrams, storyboard frames, infographic routes
- Accessibility, legibility, clear scientific metaphor, non-identifiable patient-safe imagery
- Prompt structure: subject, composition, style, lighting, constraints, aspect ratio, review notes
- Avoiding company logos, unapproved claims, identifiable patients, misleading clinical imagery, or regulatory overclaiming

Provide practical prompt rewrites, variant ideas, review risks, and handoff notes. Do not claim that generated concepts are approved for use.""",

    "analytics": """You are a Content Operations Analytics Advisor for performance measurement.

Your role: Help leadership interpret KPIs and demonstrate content ROI aligned with content operations objectives.

Key metrics:
- Operational: MLR cycle time (target ≤7 days), content reuse rate (target 75%)
- Engagement: HCP email open rate (~35%), CTR (~10%), time-on-asset
- Quality: compliance pass rate (target 95%+), claims accuracy
- Pipeline: assets in progress, expiring assets, localisation backlog

Connect content performance to commercial outcomes. Recommend specific, data-backed optimisation actions."""
}

MOCK_CONTEXT = {
    "admin": """Mock workspace data:
- Active campaigns: AsterResp COPD Q2 India, NovaVax Adult Immunisation UK, OncoPath Biomarker Education US, RespiraCare Congress Saudi.
- Pipeline health: 78%. Main bottlenecks: Compliance queue has 17 items, localisation has 9 active adaptations, DAM has 14 assets expiring within 30 days.
- At-risk launches: AsterResp COPD eDetail Aid due 10 May 2026; OncoPath congress leave-behind due 16 May 2026.
- Experimental concepts: Visual Concept Studio has 6 draft concepts, but these are not counted in pipeline health until selected for Content Lab intake.
- Current production handoffs: Content Lab has 23 assets in progress; Email QA has 2 rendering issues; Compliance has 17 pending MLR items.""",
    "media": """Mock workspace data:
- Concept briefs: AsterResp COPD HCP email hero, OncoPath biomarker testing infographic, NovaVax adult immunisation storyboard, RespiraCare congress booth loop.
- Visual guardrails: no patient-identifiable imagery, no product logos, no unapproved efficacy text in images, no before/after treatment scenes.
- Preferred style: light clinical UI, warm orange accent, clean scientific metaphors, accessible contrast, modular dashboard composition.
- Handoff needs: selected concept should include aspect ratio, channel fit, risk notes, alt-text starter, and MLR review considerations.""",
    "content-lab": """Mock workspace data:
- Module library: CLM-184 COPD burden claim, SAF-022 respiratory safety block, EVD-311 Phase III exacerbation endpoint, CTA-044 request-rep-visit, REF-210 guideline reference.
- In-progress assets: AsterResp COPD eDetail Aid, NovaVax HCP email, OncoPath biomarker leave-behind.
- Reuse opportunity: COPD burden claim can be reused across eDetail, HCP email, and congress booth content if references remain intact.
- MLR target: submit complete modular package with references and safety by 03 May 2026.""",
    "dam": """Mock workspace data:
- DAM inventory: 2,847 assets, 14 expiring in 30 days, 3 expired, 126 missing alt-text, 47 missing usage-right metadata.
- Problem assets: DAM-884 OncoPath MOA animation lacks expiry owner; DAM-731 COPD patient journey diagram has market restriction missing; DAM-622 NovaVax banner has outdated reference.
- Required metadata: therapeutic area, market, audience, lifecycle status, claim IDs, reference IDs, usage rights, expiry date, channel suitability.""",
    "scp": """Mock workspace data:
- Scientific platforms: Respiratory SCP v4.2, Adult Immunisation SCP v3.1, Oncology Biomarker SCP v2.7.
- Evidence placeholders: REF-210 GOLD guideline update, REF-311 Phase III exacerbation endpoint, REF-427 real-world persistence study.
- Known gaps: limited India-specific COPD real-world data, incomplete Saudi HCP education insights, oncology biomarker testing barriers need updated narrative.
- Congress planning: Q3 oncology congress needs narrative, evidence deck, booth visual, and MSL briefing notes.""",
    "evidence": """Mock workspace data:
- Reviews in progress: Severe asthma biologics SLR, oncology treatment persistence RWE review, adult immunisation hesitancy evidence scan.
- Draft PICO: adults with severe uncontrolled asthma; intervention biologic therapy; comparator standard care/placebo; outcomes exacerbation rate, QoL, OCS reduction.
- Screening status: 1,248 records imported, 312 duplicates removed, 186 abstracts shortlisted, 42 full texts pending extraction.
- Evidence quality watchouts: heterogeneity in endpoints, limited head-to-head evidence, real-world confounding risk.""",
    "email-qa": """Mock workspace data:
- Campaign: AsterResp COPD HCP email, target pulmonologists and GPs, India market, planned send 09 May 2026.
- Current QA: subject line 68 characters, preview text missing, hero image 420KB, CTA above fold, 2 Outlook spacing issues, alt text incomplete.
- Benchmarks: open rate target 35%, CTR target 10%, unsubscribe threshold under 0.4%.
- Compliance watchouts: claim/safety balance, unsubscribe visibility, prescribing information link, reference footer completeness.""",
    "compliance": """Mock workspace data:
- MLR queue: 17 pending items, 5 high-risk, average cycle time 7.8 days.
- Frequent issues: unsupported superiority wording, missing abbreviated safety information, unclear reference mapping, market-specific PI mismatch.
- Sample risky claim: 'Patients achieve superior control quickly' has no approved comparative reference in SCP v4.2.
- Review markets: UK ABPI, US FDA, Saudi SFDA, India CDSCO. First-pass compliance target: 95%.""",
    "localization": """Mock workspace data:
- Localisation queue: 9 active adaptations across India, Saudi Arabia, UK, and US.
- India COPD email: adapt for pulmonologists and GPs; include CDSCO review, local terminology, and urban/rural HCP context.
- Saudi oncology content: avoid culturally sensitive imagery, validate Arabic terminology, check SFDA and local affiliate review path.
- Do not alter: clinical data, safety information, reference IDs, approved claim meaning.""",
    "analytics": """Mock workspace data:
- Current KPIs: MLR cycle time 7.8 days, reuse rate 68%, compliance pass rate 94.1%, HCP open rate 34.2%, CTR 8.7%.
- Production volume: 142 approved assets month-to-date, 23 in Content Lab, 17 in Compliance, 9 in Localisation.
- Cost assumptions: new asset creation 100 units, reused module adaptation 38 units, average agency rework 14 units per failed MLR cycle.
- Priority question: whether modular reuse is reducing cycle time enough to offset localisation and compliance complexity."""
}

QUICK_PROMPTS = {
    "admin": [
        "Using the mock workspace data, review AsterResp COPD Q2 India and list the top 3 launch risks, owners, and next actions for this week.",
        "Which assets are most at risk of missing go-live across MLR, localisation, DAM metadata, and Email QA? Rank them by urgency.",
        "Create a production handoff plan for AsterResp COPD across Content Lab, DAM, Medical, Compliance, Localisation, and Analytics."
    ],
    "media": [
        "Create 3 safe visual concept routes for the AsterResp COPD HCP email hero, including prompt, aspect ratio, alt-text starter, and MLR risk notes.",
        "Turn the OncoPath biomarker testing infographic brief into an image generation prompt and list the visual guardrails for oncology HCP content.",
        "Review this concept for risk: a patient smiling while using an inhaler beside efficacy copy. Flag visual, regulatory, and claim-substantiation concerns."
    ],
    "content-lab": [
        "Assemble a modular package for the AsterResp COPD eDetail Aid using CLM-184, SAF-022, EVD-311, CTA-044, and REF-210.",
        "Map which COPD modules can be reused across eDetail Aid, HCP email, and congress booth content while preserving references and safety.",
        "Draft an agency brief for NovaVax adult immunisation: audience, channels, modules needed, MLR expectations, references, and localisation notes."
    ],
    "dam": [
        "Audit DAM-884 OncoPath MOA animation and list missing metadata, governance risks, owner actions, and expiry controls.",
        "Find likely DAM governance risks using the mock inventory: 14 expiring assets, 126 missing alt-text items, and 47 usage-right gaps.",
        "Recommend taxonomy tags for the OncoPath biomarker HCP brochure across audience, claim IDs, references, market, channel, and lifecycle."
    ],
    "scp": [
        "Draft a scientific narrative for NovaVax adult immunisation using unmet need, evidence hierarchy, HCP relevance, claim guardrails, and reference placeholders.",
        "Identify gaps in Respiratory SCP v4.2 before Q3 congress: evidence gaps, audience questions, competitor context, and content opportunities.",
        "Build an IMCP outline for an oncology congress: key narrative, priority tactics, audience segments, channel mix, evidence needs, and medical review checkpoints."
    ],
    "evidence": [
        "Create a PICO framework for the severe asthma SLR and include search terms, screening criteria, endpoints, and extraction fields.",
        "Define inclusion and exclusion criteria for the oncology treatment persistence RWE review, including data sources, endpoints, bias checks, and extraction fields.",
        "Use the mock screening status to explain PRISMA progress and provide a study quality grading table template."
    ],
    "email-qa": [
        "QA the AsterResp COPD HCP email using the mock data: subject length, missing preview text, hero size, Outlook issues, alt text, and compliance risks.",
        "Suggest 5 compliant A/B subject line variants for the AsterResp COPD email with rationale, risk notes, and expected engagement signal.",
        "Create a deliverability checklist for OncoPath oncologist emails covering sender reputation, segmentation, consent, HTML weight, CTA clarity, and MLR review."
    ],
    "compliance": [
        "Pre-screen the AsterResp COPD HCP email for fair balance, claim substantiation, reference placement, superlatives, off-label risk, and safety information.",
        "Rewrite this risky claim from the mock queue: 'Patients achieve superior control quickly.' Provide safer alternatives and required evidence.",
        "Compare ABPI, FDA, SFDA, and CDSCO watchouts for the same digital HCP content and create an MLR pre-submission checklist."
    ],
    "localization": [
        "Adapt the AsterResp global COPD HCP email for Indian pulmonologists and GPs: tone, terminology, regulatory watchouts, clinical context, and CTA changes.",
        "List cultural and regulatory considerations for localising OncoPath oncology HCP content for Saudi Arabia, including imagery, language, claims, and approval workflow.",
        "Create a market adaptation checklist for UK, US, India, and Saudi Arabia covering references, PI, safety copy, channel norms, and review owners."
    ],
    "analytics": [
        "Diagnose why MLR cycle time is above the 7-day target using pipeline, reuse, claim complexity, reviewer load, and market adaptation data.",
        "Build an ROI model for modular content reuse: assumptions, formulas, KPIs, data needed, and an executive summary for content operations leaders.",
        "Identify which content formats should be prioritised for HCP engagement using open rate, CTR, time-on-asset, reuse rate, compliance pass rate, and cost-to-produce."
    ]
}

class ChatMessage(BaseModel):
    message: str
    module: str
    model: Optional[str] = None
    history: Optional[List[dict]] = []

class MediaRequest(BaseModel):
    prompt: str
    model: Optional[str] = "gemini-2.5-flash-image"
    format: Optional[str] = "Campaign visual"
    aspect_ratio: Optional[str] = "16:9"

class AgentPlanRequest(BaseModel):
    objective: str = Field(..., min_length=8)
    market: str = "Global"
    modules: List[str] = Field(default_factory=lambda: ["content-lab", "evidence", "compliance"])
    constraints: List[str] = Field(default_factory=list)

class AgentStep(BaseModel):
    agent: str
    task: str
    inputs: List[str]
    output_schema: str
    handoff_to: Optional[str] = None
    risk_level: Literal["low", "medium", "high"] = "low"

class AgentPlan(BaseModel):
    objective: str
    market: str
    orchestration_pattern: Literal["sequential", "supervisor", "parallel_review"]
    steps: List[AgentStep]
    human_review_gates: List[str]
    audit_events: List[str]

class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    corpus: Literal["claims", "references", "assets", "policies"] = "references"
    top_k: int = Field(default=5, ge=1, le=12)

class RAGDocument(BaseModel):
    id: str
    title: str
    corpus: str
    snippet: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MCPTool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    risk_level: Literal["low", "medium", "high"]

@app.post("/api/chat/{module}")
async def chat(module: str, body: ChatMessage):
    module_context = MOCK_CONTEXT.get(module, MOCK_CONTEXT["admin"])
    system_prompt = SYSTEM_PROMPTS.get(module, SYSTEM_PROMPTS["admin"]) + "\n\n" + module_context + RESPONSE_FORMAT
    history = body.history[-10:] if body.history else []
    selected_model = body.model if body.model in LLM_MODELS else GEMINI_MODEL

    async def stream_response():
        if not client:
            yield f"data: {json.dumps({'text': 'GEMINI_API_KEY is not set. Add it to .env or export it before starting the server.'})}\n\n"
            yield "data: [DONE]\n\n"
            return
        try:
            contents = []
            for message in history:
                role = "model" if message.get("role") == "assistant" else "user"
                text = str(message.get("content", "")).strip()
                if text:
                    contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
            contents.append(types.Content(role="user", parts=[types.Part(text=body.message)]))

            stream = client.models.generate_content_stream(
                model=selected_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.35,
                    max_output_tokens=1800,
                ),
            )
            for chunk in stream:
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
        except Exception as e:
            err = str(e)
            if "api_key" in err.lower() or "auth" in err.lower() or "authentication" in err.lower():
                friendly = "Model authentication failed. Check the API key in .env or your shell environment."
            elif "rate" in err.lower():
                friendly = "Model rate limit reached. Please wait a moment and try again."
            else:
                friendly = f"Model API error: {err}"
            yield f"data: {json.dumps({'text': friendly})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/api/quick-prompts/{module}")
async def get_quick_prompts(module: str):
    return JSONResponse(QUICK_PROMPTS.get(module, []))

@app.post("/api/agents/plan", response_model=AgentPlan)
async def create_agent_plan(body: AgentPlanRequest):
    requested_modules = body.modules or ["content-lab", "evidence", "compliance"]
    step_templates = {
        "content-lab": AgentStep(
            agent="ContentLabAgent",
            task="Assemble modular content package and identify missing blocks.",
            inputs=["campaign brief", "approved modules", "channel requirements"],
            output_schema="ModularContentPackage",
            handoff_to="DAMEvidenceAgent",
            risk_level="medium",
        ),
        "dam": AgentStep(
            agent="DAMEvidenceAgent",
            task="Validate metadata, expiry, rights, alt text, and asset lineage.",
            inputs=["asset ids", "taxonomy", "usage rights", "expiry dates"],
            output_schema="AssetGovernanceReport",
            handoff_to="ComplianceAgent",
            risk_level="medium",
        ),
        "scp": AgentStep(
            agent="MedicalNarrativeAgent",
            task="Check scientific narrative alignment with SCP and IMCP priorities.",
            inputs=["scientific platform", "audience", "clinical claims"],
            output_schema="NarrativeReview",
            handoff_to="EvidenceAgent",
            risk_level="medium",
        ),
        "evidence": AgentStep(
            agent="EvidenceAgent",
            task="Retrieve reference support and grade evidence confidence.",
            inputs=["claims", "reference ids", "PICO context"],
            output_schema="EvidenceTraceMap",
            handoff_to="ComplianceAgent",
            risk_level="high",
        ),
        "compliance": AgentStep(
            agent="ComplianceAgent",
            task="Pre-screen claims, safety balance, references, and market-specific watchouts.",
            inputs=["draft asset", "evidence map", "market policy pack"],
            output_schema="MLRPreScreenReport",
            handoff_to="LocalisationAgent",
            risk_level="high",
        ),
        "localization": AgentStep(
            agent="LocalisationAgent",
            task="Adapt approved master content for local market while preserving clinical meaning.",
            inputs=["global master", "market", "policy notes"],
            output_schema="LocalisationBrief",
            handoff_to="AnalyticsAgent",
            risk_level="medium",
        ),
        "analytics": AgentStep(
            agent="AnalyticsAgent",
            task="Estimate launch readiness, cycle-time risk, and reuse ROI.",
            inputs=["pipeline status", "asset metadata", "review queue"],
            output_schema="LaunchReadinessScore",
            risk_level="low",
        ),
    }
    steps = [step_templates[module] for module in requested_modules if module in step_templates]
    if not steps:
        steps = [step_templates["content-lab"], step_templates["evidence"], step_templates["compliance"]]

    pattern: Literal["sequential", "supervisor", "parallel_review"] = "supervisor"
    if {"evidence", "compliance", "dam"}.issubset(set(requested_modules)):
        pattern = "parallel_review"

    return AgentPlan(
        objective=body.objective,
        market=body.market,
        orchestration_pattern=pattern,
        steps=steps,
        human_review_gates=[
            "Medical owner signs off evidence trace map.",
            "Compliance owner reviews high-risk claims before MLR submission.",
            "Local affiliate validates market adaptation before go-live.",
        ],
        audit_events=[
            "agent_plan_created",
            "rag_context_retrieved",
            "tool_call_recorded",
            "human_gate_required",
            "final_export_watermarked",
        ],
    )

@app.post("/api/rag/search", response_model=List[RAGDocument])
async def rag_search(body: RAGSearchRequest):
    mock_corpus = {
        "references": [
            ("REF-210", "Respiratory guideline update", "Guideline reference for COPD burden and HCP education."),
            ("REF-311", "Phase III exacerbation endpoint", "Endpoint support for exacerbation reduction claims."),
            ("REF-427", "Real-world persistence study", "RWE limitations and persistence signal summary."),
        ],
        "claims": [
            ("CLM-184", "COPD burden claim", "Approved disease burden claim with reference mapping."),
            ("CLM-229", "Adult immunisation education claim", "Non-promotional HCP education claim."),
        ],
        "assets": [
            ("DAM-884", "OncoPath MOA animation", "Animation asset missing expiry owner and usage-right metadata."),
            ("DAM-731", "COPD patient journey diagram", "Market restriction metadata incomplete."),
        ],
        "policies": [
            ("POL-ABPI", "ABPI digital promotional checklist", "Fair balance, certification, reference, and prescribing information checks."),
            ("POL-CDSCO", "India promotional review checklist", "Local review and prescribing information expectations."),
        ],
    }
    docs = mock_corpus.get(body.corpus, mock_corpus["references"])[:body.top_k]
    return [
        RAGDocument(
            id=doc_id,
            title=title,
            corpus=body.corpus,
            snippet=snippet,
            score=round(0.92 - index * 0.07, 2),
            metadata={"query": body.query, "source": "mock_rag_index"},
        )
        for index, (doc_id, title, snippet) in enumerate(docs)
    ]

@app.get("/api/mcp/tools", response_model=List[MCPTool])
async def list_mcp_tools():
    return [
        MCPTool(
            name="asset_metadata_lookup",
            description="Retrieve DAM metadata, lifecycle state, expiry date, rights, and owner for a content asset.",
            input_schema={"type": "object", "properties": {"asset_id": {"type": "string"}}, "required": ["asset_id"]},
            risk_level="low",
        ),
        MCPTool(
            name="reference_trace",
            description="Trace a claim to approved references, SCP section, and evidence confidence.",
            input_schema={"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]},
            risk_level="medium",
        ),
        MCPTool(
            name="mlr_prescreen",
            description="Pre-screen draft content for fair balance, substantiation, reference, safety, and market watchouts.",
            input_schema={"type": "object", "properties": {"content": {"type": "string"}, "market": {"type": "string"}}, "required": ["content", "market"]},
            risk_level="high",
        ),
    ]

@app.post("/api/media/generate")
async def generate_media(body: MediaRequest):
    if not client:
        return JSONResponse({"error": "GEMINI_API_KEY is not set."}, status_code=400)

    selected_model = body.model if body.model in IMAGE_MODELS else "gemini-2.5-flash-image"
    prompt = f"""
Create a polished, brand-neutral pharmaceutical visual concept for upstream review.
Format: {body.format}
Aspect ratio: {body.aspect_ratio}
Visual direction: clean, modern, medical, accessible, no company logos, no patient-identifiable information, no embedded product claims.
Prompt: {body.prompt}
"""
    try:
        response = client.models.generate_content(
            model=selected_model,
            contents=[prompt],
        )
        text_parts = []
        images = []
        parts = getattr(response, "parts", None)
        if parts is None and getattr(response, "candidates", None):
            parts = response.candidates[0].content.parts
        for part in parts or []:
            text = getattr(part, "text", None)
            inline_data = getattr(part, "inline_data", None)
            if text:
                text_parts.append(text)
            elif inline_data is not None:
                mime_type = getattr(inline_data, "mime_type", "image/png") or "image/png"
                data = getattr(inline_data, "data", b"")
                if isinstance(data, str):
                    encoded = data
                else:
                    encoded = base64.b64encode(data).decode("utf-8")
                images.append({"mime_type": mime_type, "data_url": f"data:{mime_type};base64,{encoded}"})

        return JSONResponse({
            "model": selected_model,
            "text": "\n".join(text_parts).strip(),
            "images": images,
        })
    except Exception as e:
        return JSONResponse({"error": f"Visual concept generation failed: {str(e)}"}, status_code=500)

@app.get("/api/health")
async def health():
    return JSONResponse({
        "status": "ok",
        "llm_provider": "google_gemini",
        "model": GEMINI_MODEL,
        "models": [{"id": key, "label": value} for key, value in LLM_MODELS.items()],
        "image_models": [{"id": key, "label": value} for key, value in IMAGE_MODELS.items()],
        "gemini_configured": bool(GEMINI_API_KEY),
    })

@app.get("/api/dam/assets")
async def get_dam_assets():
    return JSONResponse([
        {"id": 1, "name": "COPD eDetailAid Q2 2026", "type": "eDA", "status": "Approved", "therapeutic": "Respiratory", "channel": "Remote Detailing", "audience": "Pulmonologist", "region": "Global", "updated": "2026-04-15"},
        {"id": 2, "name": "Shingrix HCP Email Template", "type": "Email", "status": "Draft", "therapeutic": "Vaccines", "channel": "Email", "audience": "GP", "region": "UK", "updated": "2026-04-20"},
        {"id": 3, "name": "Oncology Scientific Narrative v3", "type": "Document", "status": "In Review", "therapeutic": "Oncology", "channel": "Medical", "audience": "Oncologist", "region": "Global", "updated": "2026-04-18"},
        {"id": 4, "name": "Nucala Patient Support Brochure", "type": "Print", "status": "Approved", "therapeutic": "Immunology", "channel": "Multi-channel", "audience": "Patient", "region": "US", "updated": "2026-04-10"},
        {"id": 5, "name": "RSV Vaccine Congress Slides", "type": "Presentation", "status": "Approved", "therapeutic": "Vaccines", "channel": "Congress", "audience": "HCP", "region": "Global", "updated": "2026-04-08"},
        {"id": 6, "name": "India Asthma Campaign Module", "type": "Module", "status": "Draft", "therapeutic": "Respiratory", "channel": "Email", "audience": "HCP", "region": "India", "updated": "2026-04-22"},
        {"id": 7, "name": "Saudi Oncology Content Adaptation", "type": "Module", "status": "In Review", "therapeutic": "Oncology", "channel": "Email", "audience": "Oncologist", "region": "Saudi Arabia", "updated": "2026-04-21"},
        {"id": 8, "name": "Zejula Efficacy Claims Module", "type": "Module", "status": "Approved", "therapeutic": "Oncology", "channel": "Multi-channel", "audience": "Oncologist", "region": "Global", "updated": "2026-04-01"},
        {"id": 9, "name": "Trelegy COPD Claim Block", "type": "Module", "status": "Approved", "therapeutic": "Respiratory", "channel": "Multi-channel", "audience": "Pulmonologist", "region": "Global", "updated": "2026-03-28"},
        {"id": 10, "name": "Arexvy Phase III Data Summary", "type": "Document", "status": "Expired", "therapeutic": "Vaccines", "channel": "Medical", "audience": "HCP", "region": "US", "updated": "2026-02-01"},
        {"id": 11, "name": "Benlysta RA Social Content Pack", "type": "Social", "status": "Approved", "therapeutic": "Immunology", "channel": "Social Media", "audience": "Patient", "region": "UK", "updated": "2026-04-12"},
        {"id": 12, "name": "Jemperli MOA Animation", "type": "Video", "status": "In Review", "therapeutic": "Oncology", "channel": "eDA", "audience": "Oncologist", "region": "US", "updated": "2026-04-23"},
    ])

@app.get("/api/analytics/kpis")
async def get_kpis():
    return JSONResponse({
        "mlr_cycle_time": {"value": 7.8, "unit": "days", "trend": -15, "target": 7.0, "label": "MLR Cycle Time"},
        "content_reuse_rate": {"value": 68, "unit": "%", "trend": 12, "target": 75, "label": "Content Reuse Rate"},
        "hcp_email_open_rate": {"value": 34.2, "unit": "%", "trend": 5, "target": 35, "label": "HCP Email Open Rate"},
        "click_through_rate": {"value": 8.7, "unit": "%", "trend": 3, "target": 10, "label": "Click-Through Rate"},
        "assets_approved_mtd": {"value": 142, "unit": "assets", "trend": 8, "target": 150, "label": "Assets Approved MTD"},
        "compliance_pass_rate": {"value": 94.1, "unit": "%", "trend": 2, "target": 95, "label": "Compliance Pass Rate"},
        "modules_in_library": {"value": 847, "unit": "modules", "trend": 6, "target": 1000, "label": "Modules in Library"},
        "avg_localization_time": {"value": 3.2, "unit": "days", "trend": -20, "target": 3.0, "label": "Avg Localisation Time"},
    })

@app.get("/api/workflow/status")
async def get_workflow_status():
    return JSONResponse({
        "active_campaigns": 12,
        "pipeline_health": 78,
        "modules": {
            "content-lab": {"status": "active", "label": "Content Lab", "icon": "CL", "detail": "23 in progress · 8 pending review"},
            "dam": {"status": "active", "label": "DAM", "icon": "DA", "detail": "2,847 assets · 14 expiring soon"},
            "scp": {"status": "active", "label": "Sci Comm (SCP)", "icon": "SC", "detail": "6 active platforms · 3 pending updates"},
            "evidence": {"status": "active", "label": "Evidence Synthesis", "icon": "EV", "detail": "4 reviews in progress · 18 completed MTD"},
            "email-qa": {"status": "active", "label": "Email QA", "icon": "EQ", "detail": "34 tests today · 2 issues flagged"},
            "compliance": {"status": "warning", "label": "Compliance", "icon": "ML", "detail": "17 pending MLR · avg 7.8 days cycle"},
            "localization": {"status": "active", "label": "Localisation", "icon": "LO", "detail": "9 in progress · 4 markets active"},
            "analytics": {"status": "active", "label": "Analytics", "icon": "AN", "detail": "Last updated: 25 Apr 09:00 UTC"}
        }
    })

@app.get("/api/modules")
async def get_content_modules():
    return JSONResponse([
        {"id": "claim-copd-efficacy", "name": "COPD Efficacy Claim", "type": "Claim", "therapeutic": "Respiratory", "status": "Approved", "channels": ["eDA", "Email", "Social"]},
        {"id": "safety-copd-01", "name": "COPD Safety Statement", "type": "Safety", "therapeutic": "Respiratory", "status": "Approved", "channels": ["eDA", "Email", "Print"]},
        {"id": "claim-shingrix-efficacy", "name": "Shingrix 97% Efficacy Claim", "type": "Claim", "therapeutic": "Vaccines", "status": "Approved", "channels": ["eDA", "Email", "Social", "Congress"]},
        {"id": "header-brand-logo", "name": "Brand Header", "type": "Brand", "therapeutic": "Global", "status": "Approved", "channels": ["All"]},
        {"id": "footer-legal-uk", "name": "UK Legal Footer", "type": "Legal", "therapeutic": "Global", "status": "Approved", "channels": ["Email", "eDA"]},
        {"id": "footer-legal-us", "name": "US Legal Footer / ISI", "type": "Legal", "therapeutic": "Global", "status": "Approved", "channels": ["Email", "eDA", "Print"]},
        {"id": "claim-nucala-efficacy", "name": "Nucala Exacerbation Reduction", "type": "Claim", "therapeutic": "Immunology", "status": "Approved", "channels": ["eDA", "Email"]},
        {"id": "moa-zejula", "name": "Zejula MOA Visual", "type": "Visual", "therapeutic": "Oncology", "status": "In Review", "channels": ["eDA", "Congress"]},
        {"id": "ref-block-01", "name": "Standard Reference Block", "type": "Reference", "therapeutic": "Global", "status": "Approved", "channels": ["All"]},
        {"id": "cta-learn-more", "name": "Learn More CTA Button", "type": "CTA", "therapeutic": "Global", "status": "Approved", "channels": ["Email", "Social"]},
        {"id": "claim-trelegy-efficacy", "name": "Trelegy Triple Therapy Claim", "type": "Claim", "therapeutic": "Respiratory", "status": "Approved", "channels": ["eDA", "Email", "Print"]},
        {"id": "safety-vaccines-01", "name": "Vaccines General Safety Block", "type": "Safety", "therapeutic": "Vaccines", "status": "Approved", "channels": ["eDA", "Email", "Print", "Social"]},
    ])

@app.get("/")
async def serve_index():
    with open("index.html", "r") as f:
        return HTMLResponse(f.read())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
