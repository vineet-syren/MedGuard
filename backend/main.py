import os
import base64
from pathlib import Path
from datetime import datetime
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from google import genai
from google.genai import types

app = FastAPI(title="MedGuard Backend")
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
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:3000")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
SSO_STATE_STORE: Dict[str, Dict[str, Any]] = {}
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

Context: Enterprise life-sciences teams need faster regulated content delivery without weakening scientific accuracy, local-market controls, or human MLR accountability. Content must be scientifically accurate, regulatory-compliant, and personalized across US, UK, India, and Saudi Arabia.

Be proactive, strategic, and data-driven. Highlight cross-module dependencies and bottlenecks.""",

    "content-lab": """You are an AI Content Strategist in Content Lab — the modular content production hub connected to regulated content repositories and approval systems.

Your role: Help Content Managers assemble pre-approved modular "Lego bricks" into channel-ready assets.

Expertise:
- Modular content: claim blocks, safety modules, efficacy modules, brand/logo modules, reference blocks
- Channels: eDetail Aids (eDAs), email, remote detailing, social media, congress materials, self-service portals
- Regulated content workflow: draft → MLR review → approved → deployed
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

    "email-qa": """You are a Digital Marketing QA Specialist for omnichannel HCP email campaigns with Litmus-style QA integration.

Your role: Help Digital Marketing Managers review, test, and optimise emails before deployment.

Expertise:
- Rendering across 100+ email clients (Outlook, Gmail, Apple Mail, mobile)
- Spam filter analysis: SPF, DKIM, content triggers, deliverability
- ABPI Code compliance for promotional digital communications
- A/B testing: subject lines, CTAs, dynamic content, send timing
- HCP engagement benchmarks: open rate ~35%, CTR ~10%
- QA checklist: links, images, alt-text, unsubscribe, legal footer
- Litmus-style testing workflow: previews, links, images, accessibility, load time, spam, and dark-mode evidence

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

    "claims-governance": """You are a Claims Governance AI for downstream pharma content operations.

Your role: Help teams manage claim lifecycle, substantiation, market eligibility, versioning, reuse permissions, and reviewer-ready claim packets.

Expertise:
- Claim register governance: claim ID, owner, status, market, channel, expiry, and permitted use
- Substantiation mapping: label, publication, guideline, SCP, safety language, and evidence confidence
- Claim variants: master claim, localized variants, short-form versions, and channel-specific wording
- Risk controls: unsupported superiority, implied efficacy, outdated references, missing caveats, and off-label drift
- Operating model: who can create, amend, retire, reuse, and approve claim language

Produce structured claim decisions: safe to reuse, needs evidence, needs rewrite, or block until human review.""",

    "responsible-ai": """You are a Responsible AI Governance AI for regulated content supply chain workflows.

Your role: Help governance teams define and operate controls for AI-assisted content work across authoring, retrieval, review, localization, and deployment.

Expertise:
- AI use-case register, risk tiering, model approval, prompt controls, output logging, and human approval gates
- Source-grounding checks, hallucination risk, bias, PHI/PII handling, data residency, and vendor boundary controls
- Responsible AI policy mapping for content generation, claim validation, summarization, image concepts, and workflow automation
- Audit evidence: prompt, source, model, tool call, reviewer decision, timestamp, and final asset lineage

Keep outputs practical and governance-oriented. Do not imply AI can replace medical, legal, or regulatory sign-off.""",

    "workflow-orchestration": """You are a Downstream Workflow Orchestration AI for global-to-local regulated content operations.

Your role: Help operations leaders design the approval operating model across global teams, local markets, agencies, operations partners, MLR reviewers, and deployment owners.

Expertise:
- Workflow stages: intake, triage, claim validation, compliance pre-screen, MLR review, localization, deployment readiness, and measurement
- Time-zone intensive operations, partner handoffs, SLA risk, queue prioritization, and escalation rules
- Human-in-the-loop approvals, separation of duties, RACI, review gates, and evidence handoff packs
- Deployment readiness: metadata, approvals, market restrictions, channel fit, expiry, and launch checklist

Recommend orchestration plans that complement existing enterprise systems rather than replacing them.""",

    "integration-layer": """You are an Ecosystem Integration AI for regulated content supply chain platforms.

Your role: Help solution architects map how an orchestration and governance layer integrates with existing authoring, DAM, approval, CRM, model gateway, and analytics systems.

Expertise:
- Integration patterns: API, webhook, event bus, SSO, role mapping, metadata sync, asset package export, and audit log exchange
- Enterprise systems: Veeva CRM activation, Veeva PromoMats-style MLR workflows, Litmus email QA, AEM-style authoring, DAM, model gateways, data lakes, and agency intake tools
- Data contracts: claim IDs, asset IDs, reference IDs, policy IDs, reviewer decisions, market metadata, and lifecycle states
- Build-versus-buy boundaries: what should remain in enterprise platforms versus custom orchestration logic

Produce clear integration maps, not abstract architecture diagrams.""",

    "poc-readiness": """You are a Pilot and Build-vs-Buy Readiness AI for enterprise pharma content governance.

Your role: Help commercial, medical, compliance, procurement, and technology leaders shape an internal brief, evaluation scorecard, and Pilot scope.

Expertise:
- Build-vs-buy comparison against enterprise platform expansion, custom orchestration, managed service, and hybrid options
- Pilot scope: downstream governance, claims validation, responsible AI controls, workflow orchestration, integration, and auditability
- Success criteria: MLR rework reduction, claim traceability, approval readiness, integration fit, risk controls, and user adoption
- RFP inputs: problem statement, personas, system boundaries, data needs, security assumptions, and acceptance criteria

Be commercially honest. Recommend custom build only where enterprise platforms cannot encode local rules, traceability, and cross-system governance.""",

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

Your role: Help leadership interpret KPIs and show content ROI aligned with content operations objectives.

Key metrics:
- Operational: MLR cycle time (target ≤7 days), content reuse rate (target 75%)
- Engagement: HCP email open rate (~35%), CTR (~10%), time-on-asset
- Quality: compliance pass rate (target 95%+), claims accuracy
- Pipeline: assets in progress, expiring assets, localisation backlog

Connect content performance to commercial outcomes. Recommend specific, data-backed optimisation actions."""
}

MOCK_CONTEXT = {
    "admin": """Workspace data:
- Active campaigns: Respivara COPD Q2 India, Vaxilora Adult Immunisation UK, Oncoryn Biomarker Education US, Pulmovia Congress Saudi.
- Pipeline health: 78%. Main bottlenecks: Compliance queue has 17 items, localisation has 9 active adaptations, DAM has 14 assets expiring within 30 days.
- At-risk launches: Respivara COPD eDetail Aid due 10 May 2026; Oncoryn congress leave-behind due 16 May 2026.
- Experimental concepts: Visual Concept Studio has 6 draft concepts, but these are not counted in pipeline health until selected for Content Lab intake.
- Current production handoffs: Content Lab has 23 assets in progress; Email QA has 2 rendering issues; Compliance has 17 pending MLR items.""",
    "media": """Workspace data:
- Concept briefs: Respivara COPD HCP email hero, Oncoryn biomarker testing infographic, Vaxilora adult immunisation storyboard, Pulmovia congress booth loop.
- Visual guardrails: no patient-identifiable imagery, no product logos, no unapproved efficacy text in images, no before/after treatment scenes.
- Preferred style: light clinical UI, warm orange accent, clean scientific metaphors, accessible contrast, modular dashboard composition.
- Handoff needs: selected concept should include aspect ratio, channel fit, risk notes, alt-text starter, and MLR review considerations.""",
    "content-lab": """Workspace data:
- Module library: CLM-184 COPD burden claim, SAF-022 respiratory safety block, EVD-311 Phase III exacerbation endpoint, CTA-044 request-rep-visit, REF-210 guideline reference.
- In-progress assets: Respivara COPD eDetail Aid, Vaxilora HCP email, Oncoryn biomarker leave-behind.
- Reuse opportunity: COPD burden claim can be reused across eDetail, HCP email, and congress booth content if references remain intact.
- MLR target: submit complete modular package with references and safety by 03 May 2026.""",
    "dam": """Workspace data:
- DAM inventory: 2,847 assets, 14 expiring in 30 days, 3 expired, 126 missing alt-text, 47 missing usage-right metadata.
- Problem assets: DAM-884 Oncoryn MOA animation lacks expiry owner; DAM-731 COPD patient journey diagram has market restriction missing; DAM-622 Vaxilora banner has outdated reference.
- Required metadata: therapeutic area, market, audience, lifecycle status, claim IDs, reference IDs, usage rights, expiry date, channel suitability.""",
    "scp": """Workspace data:
- Scientific platforms: Respiratory SCP v4.2, Adult Immunisation SCP v3.1, Oncology Biomarker SCP v2.7.
- Evidence placeholders: REF-210 GOLD guideline update, REF-311 Phase III exacerbation endpoint, REF-427 real-world persistence study.
- Known gaps: limited India-specific COPD real-world data, incomplete Saudi HCP education insights, oncology biomarker testing barriers need updated narrative.
- Congress planning: Q3 oncology congress needs narrative, evidence deck, booth visual, and MSL briefing notes.""",
    "evidence": """Workspace data:
- Reviews in progress: Severe asthma biologics SLR, oncology treatment persistence RWE review, adult immunisation hesitancy evidence scan.
- Draft PICO: adults with severe uncontrolled asthma; intervention biologic therapy; comparator standard care/placebo; outcomes exacerbation rate, QoL, OCS reduction.
- Screening status: 1,248 records imported, 312 duplicates removed, 186 abstracts shortlisted, 42 full texts pending extraction.
- Evidence quality watchouts: heterogeneity in endpoints, limited head-to-head evidence, real-world confounding risk.""",
    "email-qa": """Workspace data:
- Campaign: Respivara COPD HCP email, target pulmonologists and GPs, India market, planned send 09 May 2026.
- Current QA: subject line 68 characters, preview text missing, hero image 420KB, CTA above fold, 2 Outlook spacing issues, alt text incomplete.
- Benchmarks: open rate target 35%, CTR target 10%, unsubscribe threshold under 0.4%.
- Compliance watchouts: claim/safety balance, unsubscribe visibility, prescribing information link, reference footer completeness.""",
    "compliance": """Workspace data:
- MLR queue: 17 pending items, 5 high-risk, average cycle time 7.8 days.
- Frequent issues: unsupported superiority wording, missing abbreviated safety information, unclear reference mapping, market-specific PI mismatch.
- Risky claim: 'Patients achieve superior control quickly' has no approved comparative reference in SCP v4.2.
- Review markets: UK ABPI, US FDA, Saudi SFDA, India CDSCO. First-pass compliance target: 95%.""",
    "claims-governance": """Workspace data:
- Claim register: 318 active claims, 47 retired claims, 26 claims expiring in 60 days, and 11 claims missing evidence confidence.
- Priority claim family: Respivara COPD burden, CLM-184 master claim, 6 localized variants, 4 channel variants, 2 pending medical-owner decisions.
- Current gaps: 9 claims have approved master wording but no short-form email variant; 5 localized claims need market caveat validation.
- Governance rule: no new asset can enter MLR until every promotional claim has owner, source, permitted market, expiry, and safety caveat status.""",
    "responsible-ai": """Workspace data:
- AI use-case register: 14 active use cases, 5 medium risk, 3 high risk, 2 awaiting data-residency review.
- Active controls: source-grounding required for claim outputs, prompt and response logging enabled, human approval gate required for MLR-related outputs.
- Current risks: one agency prompt template allows ungrounded efficacy language; image-concept workflow lacks review-note capture; localization agent needs glossary lock.
- Audit requirement: store model, prompt, retrieved sources, tool calls, reviewer decision, timestamp, and final asset ID for every regulated output.""",
    "workflow-orchestration": """Workspace data:
- Global-to-local flow: 24 markets, 4 review hubs, 2 agency/operations partner lanes, and 11 time-zone handoff windows.
- Downstream queue: 17 MLR items, 9 localization items, 14 DAM expiry actions, 6 deployment-readiness blockers.
- SLA pressure: APAC market handoffs lose 18 hours when claim packets are incomplete; compliance escalations are missing RACI owners in 5 workflows.
- Operating-model gap: teams have tools for authoring and approval, but no single downstream governance control plane across claim, policy, reviewer, asset, and deployment readiness.""",
    "integration-layer": """Workspace data:
- Target ecosystem: authoring workspace, DAM, MLR workflow, CRM activation, enterprise model gateway, data lake, agency intake, and analytics warehouse.
- Integration backlog: 12 API candidates, 4 webhook events, 7 metadata mappings, 3 SSO role groups, and 5 audit-log export requirements.
- High-value contracts: claim_id, asset_id, reference_id, market_code, approval_status, risk_tier, reviewer_owner, expiry_date, and deployment_channel.
- Boundary decision: keep asset approval in existing workflow tools; add orchestration, validation, traceability, and governance intelligence above them.""",
    "poc-readiness": """Workspace data:
- Proposed pilot: 6 weeks, two brands, two markets, 30 approved claims, 50 assets, and one downstream workflow from brief to deployment readiness.
- Evaluation options: enterprise platform expansion, custom orchestration layer, managed-services acceleration, and hybrid governance layer.
- Success metrics: 30% fewer preventable MLR comments, 90% claim traceability completeness, 100% audit-log capture, and 80% reviewer satisfaction in pilot.
- Open brief questions: data access, system boundary, partner responsibilities, security approvals, source-of-truth ownership, and RFP versus pitch-led route.""",
    "localization": """Workspace data:
- Localisation queue: 9 active adaptations across India, Saudi Arabia, UK, and US.
- India COPD email: adapt for pulmonologists and GPs; include CDSCO review, local terminology, and urban/rural HCP context.
- Saudi oncology content: avoid culturally sensitive imagery, validate Arabic terminology, check SFDA and local affiliate review path.
- Do not alter: clinical data, safety information, reference IDs, approved claim meaning.""",
    "analytics": """Workspace data:
- Current KPIs: MLR cycle time 7.8 days, reuse rate 68%, compliance pass rate 94.1%, HCP open rate 34.2%, CTR 8.7%.
- Production volume: 142 approved assets month-to-date, 23 in Content Lab, 17 in Compliance, 9 in Localisation.
- Cost assumptions: new asset creation 100 units, reused module adaptation 38 units, average agency rework 14 units per failed MLR cycle.
- Priority question: whether modular reuse is reducing cycle time enough to offset localisation and compliance complexity."""
}

QUICK_PROMPTS = {
    "admin": [
        "Using the workspace data, review Respivara COPD Q2 India and list the top 3 launch risks, owners, and next actions for this week.",
        "Which assets are most at risk of missing go-live across MLR, localisation, DAM metadata, and Email QA? Rank them by urgency.",
        "Create a production handoff plan for Respivara COPD across Content Lab, DAM, Medical, Compliance, Localisation, and Analytics."
    ],
    "media": [
        "Create 3 safe visual concept routes for the Respivara COPD HCP email hero, including prompt, aspect ratio, alt-text starter, and MLR risk notes.",
        "Turn the Oncoryn biomarker testing infographic brief into an image generation prompt and list the visual guardrails for oncology HCP content.",
        "Review this concept for risk: a patient smiling while using an inhaler beside efficacy copy. Flag visual, regulatory, and claim-substantiation concerns."
    ],
    "content-lab": [
        "Assemble a modular package for the Respivara COPD eDetail Aid using CLM-184, SAF-022, EVD-311, CTA-044, and REF-210.",
        "Map which COPD modules can be reused across eDetail Aid, HCP email, and congress booth content while preserving references and safety.",
        "Draft an agency brief for Vaxilora adult immunisation: audience, channels, modules needed, MLR expectations, references, and localisation notes."
    ],
    "dam": [
        "Audit DAM-884 Oncoryn MOA animation and list missing metadata, governance risks, owner actions, and expiry controls.",
        "Find likely DAM governance risks using the inventory: 14 expiring assets, 126 missing alt-text items, and 47 usage-right gaps.",
        "Recommend taxonomy tags for the Oncoryn biomarker HCP brochure across audience, claim IDs, references, market, channel, and lifecycle."
    ],
    "scp": [
        "Draft a scientific narrative for Vaxilora adult immunisation using unmet need, evidence hierarchy, HCP relevance, claim guardrails, and reference placeholders.",
        "Identify gaps in Respiratory SCP v4.2 before Q3 congress: evidence gaps, audience questions, competitor context, and content opportunities.",
        "Build an IMCP outline for an oncology congress: key narrative, priority tactics, audience segments, channel mix, evidence needs, and medical review checkpoints."
    ],
    "evidence": [
        "Create a PICO framework for the severe asthma SLR and include search terms, screening criteria, endpoints, and extraction fields.",
        "Define inclusion and exclusion criteria for the oncology treatment persistence RWE review, including data sources, endpoints, bias checks, and extraction fields.",
        "Use the current screening status to explain PRISMA progress and provide a study quality grading table template."
    ],
    "email-qa": [
        "Create a Litmus-linked QA evidence summary for the Respivara COPD HCP email: previews, links, accessibility, spam, load time, and compliance risks.",
        "Suggest 5 compliant A/B subject line variants for the Respivara COPD email with rationale, risk notes, and expected engagement signal.",
        "Create a deliverability checklist for Oncoryn oncologist emails covering sender reputation, segmentation, consent, HTML weight, CTA clarity, and MLR review."
    ],
    "compliance": [
        "Pre-screen the Respivara COPD HCP email for fair balance, claim substantiation, reference placement, superlatives, off-label risk, and safety information.",
        "Rewrite this risky claim from the current queue: 'Patients achieve superior control quickly.' Provide safer alternatives and required evidence.",
        "Compare ABPI, FDA, SFDA, and CDSCO watchouts for the same digital HCP content and create an MLR pre-submission checklist."
    ],
    "claims-governance": [
        "Create a claim governance packet for CLM-184: owner, source support, permitted markets, channel variants, expiry, caveats, and reviewer questions.",
        "Audit the claim register and identify which claims should be reused, rewritten, retired, or blocked before MLR submission.",
        "Define an operating model for claim creation, amendment, localization, reuse approval, expiry, and evidence revalidation."
    ],
    "responsible-ai": [
        "Review the AI use-case register and classify content generation, claim validation, localization, image concepts, and workflow routing by risk tier.",
        "Create a responsible AI control checklist for downstream content governance with source-grounding, logging, human gates, and audit evidence.",
        "Assess this workflow risk: an agency prompt can generate efficacy copy without retrieved sources. Recommend controls and owner actions."
    ],
    "workflow-orchestration": [
        "Design a downstream operating model from global master content to local deployment readiness, including stages, owners, gates, and SLAs.",
        "Use the current queue data to identify where global-to-local handoffs are breaking and propose escalation rules.",
        "Create a RACI for claim validation, compliance pre-screen, MLR review, localization, DAM metadata, and deployment readiness."
    ],
    "integration-layer": [
        "Map how MedGuard should complement Veeva CRM, Veeva PromoMats-style workflows, Litmus, authoring, DAM, model gateway, and analytics systems.",
        "Define the minimum integration data contracts for claim_id, asset_id, reference_id, market_code, approval_status, risk_tier, and reviewer_owner.",
        "Separate what should stay in enterprise platforms from what a custom orchestration and governance layer should own."
    ],
    "poc-readiness": [
        "Create a 6-week Pilot brief for downstream content governance covering scope, personas, data, integrations, risks, and acceptance criteria.",
        "Build a concise build-vs-buy comparison between enterprise platform expansion and a custom orchestration layer for claims governance.",
        "Draft evaluation criteria for an internal pitch: MLR rework reduction, claim traceability, responsible AI controls, integration fit, and auditability."
    ],
    "localization": [
        "Adapt the Respivara global COPD HCP email for Indian pulmonologists and GPs: tone, terminology, regulatory watchouts, clinical context, and CTA changes.",
        "List cultural and regulatory considerations for localising Oncoryn oncology HCP content for Saudi Arabia, including imagery, language, claims, and approval workflow.",
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

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    password: str = Field("12345", min_length=5)
    team: str = "New content team"
    persona: str = "Content operations user"

USER_ROLE_VALUES = Literal[
    "super_admin",
    "admin",
    "workflow_owner",
    "content_author",
    "medical_reviewer",
    "regulatory_reviewer",
    "compliance_reviewer",
    "legal_reviewer",
    "local_market_reviewer",
    "qa_specialist",
    "approver",
    "audit_viewer",
    "user",
]

class ManagedUserCreateRequest(BaseModel):
    actor_email: str
    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    password: str = Field("12345", min_length=5)
    role: USER_ROLE_VALUES = "content_author"
    persona: str = "Content operations user"
    team: str = "Content Operations"
    modules: List[str] = Field(default_factory=list)

class PasswordUpdateRequest(BaseModel):
    actor_email: str
    password: str = Field(..., min_length=5)

class ActorRequest(BaseModel):
    actor_email: str

class StatusUpdateRequest(BaseModel):
    actor_email: str
    status: Literal["active", "inactive"]

class UserAccessUpdateRequest(BaseModel):
    actor_email: str
    role: USER_ROLE_VALUES
    modules: List[str] = Field(default_factory=list)
    team: str = "Content Operations"
    persona: str = "Content operations user"

class DecisionRequest(BaseModel):
    actor_email: str
    stage_id: str
    action: Literal["accept", "override"]
    reason: str = ""

class ProfilePasswordUpdateRequest(BaseModel):
    email: str
    current_password: str = Field(..., min_length=5)
    new_password: str = Field(..., min_length=5)

class ComplianceValidationRequest(BaseModel):
    stage_id: str = "content-created"
    asset_id: str = "AST-RESP-EMAIL-042"
    market: str = "India"
    channel: str = "HCP Email"
    content: str = "Immunavax provides long-term immunity for 10 years with a strong safety profile."
    claim: str = "Immunavax provides long-term immunity for 10 years."

class ConnectorRequest(BaseModel):
    actor_email: str = ""
    name: str = Field(..., min_length=2)
    scope: str = "Content, metadata, approvals"
    auth_method: str = "OAuth 2.0"
    owner: str = "Platform Governance"
    status: Literal["connected", "planned", "candidate", "disabled"] = "candidate"
    icon: str = "integration"
    scopes: List[str] = Field(default_factory=lambda: ["metadata.read", "audit.write"])

class RuleRunRequest(BaseModel):
    stage_id: str
    content_id: str = "AST-RESP-EMAIL-042"
    actor_email: str = ""
    use_gemini: bool = True
    bundle_id: str = ""
    model_profile: str = "auto"
    action_context: str = ""

class StepApprovalRequest(BaseModel):
    actor_email: str
    stage_id: str
    step_id: str = "overall"
    action: Literal["approve", "request_changes", "override"]
    reason: str = ""
    reason_code: str = "reviewer-confirmed"
    affected_rule: str = ""

class DocumentCompareRequest(BaseModel):
    document_ids: List[str] = Field(default_factory=list)

class InputBundleRequest(BaseModel):
    actor_email: str = ""
    stage_id: str
    name: str = Field(..., min_length=2)
    document_ids: List[str] = Field(default_factory=list)
    notes: str = ""

class WorkflowActionRequest(BaseModel):
    actor_email: str
    stage_id: str
    action_type: Literal["accept", "reject", "edit_output", "comment", "override", "rerun", "escalate", "request_rework", "send_next_stage"]
    command: str = ""
    output_text: str = ""
    reason_code: str = "reviewer-action"
    affected_rule: str = ""

class WorkflowApprovalRequest(BaseModel):
    actor_email: str
    stage_id: str
    step_id: str = "overall"
    decision: Literal["approve", "reject", "request_rework", "override", "final_authorize"]
    reason: str = ""
    bundle_id: str = ""

DEMO_PASSWORD = "12345"

ALL_PRODUCT_MODULES = [
    "claims-governance",
    "compliance",
    "responsible-ai",
    "workflow-orchestration",
    "integration-layer",
    "poc-readiness",
    "admin",
    "email-qa",
    "content-lab",
    "dam",
    "evidence",
    "localization",
    "analytics",
    "media",
]

ROLE_MODULES: Dict[str, List[str]] = {
    "super_admin": ALL_PRODUCT_MODULES,
    "admin": ["claims-governance", "compliance", "responsible-ai", "workflow-orchestration", "integration-layer", "admin", "email-qa", "dam", "analytics", "evidence", "localization"],
    "workflow_owner": ["claims-governance", "compliance", "responsible-ai", "workflow-orchestration", "integration-layer", "email-qa", "content-lab", "dam", "evidence", "localization", "analytics", "media"],
    "content_author": ["content-lab", "workflow-orchestration", "claims-governance", "dam"],
    "medical_reviewer": ["claims-governance", "evidence", "compliance", "responsible-ai"],
    "regulatory_reviewer": ["claims-governance", "evidence", "compliance", "responsible-ai", "workflow-orchestration"],
    "compliance_reviewer": ["compliance", "responsible-ai", "evidence"],
    "legal_reviewer": ["compliance", "responsible-ai", "workflow-orchestration"],
    "local_market_reviewer": ["localization", "workflow-orchestration", "claims-governance", "analytics"],
    "qa_specialist": ["email-qa", "compliance", "workflow-orchestration", "analytics", "media"],
    "approver": ["workflow-orchestration", "compliance", "analytics"],
    "audit_viewer": ["analytics", "responsible-ai"],
    "user": ["workflow-orchestration", "claims-governance", "compliance"],
}

ROLE_STAGE_ACCESS: Dict[str, List[str]] = {
    "workflow_owner": ["briefing", "content-created", "medical-review", "compliance-approval", "localization", "local-approval", "qa", "publish"],
    "content_author": ["briefing", "content-created"],
    "medical_reviewer": ["medical-review"],
    "regulatory_reviewer": ["medical-review", "compliance-approval"],
    "compliance_reviewer": ["compliance-approval"],
    "legal_reviewer": ["compliance-approval", "local-approval"],
    "local_market_reviewer": ["localization", "local-approval"],
    "qa_specialist": ["qa"],
    "approver": ["compliance-approval", "local-approval", "publish"],
    "audit_viewer": ["briefing", "content-created", "medical-review", "compliance-approval", "localization", "local-approval", "qa", "publish"],
}

AI_MODEL_PROFILES: Dict[str, Dict[str, Any]] = {
    "fast": {"id": "fast", "label": "Fast model", "model": "gemini-2.5-flash", "display": "Fast model (gemini-2.5-flash)", "speed": "fast", "depth": "screening", "detail": "Concise blocker scan for low-risk assets.", "capabilities": ["text validation", "metadata scan"], "confidence_bias": -2},
    "balanced": {"id": "balanced", "label": "Balanced model", "model": "gemini-2.5-flash", "display": "Balanced model (gemini-2.5-flash)", "speed": "standard", "depth": "balanced", "detail": "Balanced compliance reasoning with evidence summaries.", "capabilities": ["text validation", "source comparison", "rewrite suggestions"], "confidence_bias": 0},
    "reasoning": {"id": "reasoning", "label": "Reasoning model", "model": "gemini-3-pro-preview", "display": "Reasoning model (gemini-3-pro-preview)", "speed": "slower", "depth": "deep", "detail": "Detailed MLR reasoning for claims, evidence, and risk.", "capabilities": ["deep reasoning", "claims inference", "policy explanation"], "confidence_bias": 3},
    "compliance": {"id": "compliance", "label": "Compliance-specific model", "model": "gemini-3-pro-preview", "display": "Compliance model (gemini-3-pro-preview)", "speed": "standard", "depth": "strict", "detail": "Conservative policy, legal, privacy, and approval gate reasoning.", "capabilities": ["rules", "policy mapping", "audit evidence"], "confidence_bias": 1},
    "localization": {"id": "localization", "label": "Localization-aware model", "model": "gemini-3-pro-preview", "display": "Localization model (gemini-3-pro-preview)", "speed": "standard", "depth": "local-market", "detail": "Semantic drift, local label, glossary, and cultural adaptation review.", "capabilities": ["translation drift", "local rules", "OCR-ready review"], "confidence_bias": 1},
    "multimodal": {"id": "multimodal", "label": "Multimodal/OCR model", "model": "gemini-3-pro-preview", "display": "Multimodal/OCR model (gemini-3-pro-preview)", "speed": "standard", "depth": "visual-and-document", "detail": "Media, image, PDF, layout, OCR, and channel asset review.", "capabilities": ["multimodal", "OCR", "image and layout checks"], "confidence_bias": 1},
}

USERS: Dict[str, Dict[str, Any]] = {
    "super.admin@medguard.ai": {
        "id": "USR-001",
        "name": "Aarav Menon",
        "email": "super.admin@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "super_admin",
        "persona": "Super admin",
        "team": "Platform Governance",
        "status": "active",
        "modules": ALL_PRODUCT_MODULES,
        "last_login": "2026-04-30 12:40 IST",
    },
    "admin.ops@medguard.ai": {
        "id": "USR-002",
        "name": "Maya Rao",
        "email": "admin.ops@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "admin",
        "persona": "Content operations admin",
        "team": "Global Content Operations",
        "status": "active",
        "modules": [
            "claims-governance",
            "compliance",
            "responsible-ai",
            "workflow-orchestration",
            "integration-layer",
            "admin",
            "email-qa",
            "dam",
            "analytics",
        ],
        "last_login": "2026-04-30 11:18 IST",
    },
    "rhea.claims@medguard.ai": {
        "id": "USR-003",
        "name": "Rhea Sharma",
        "email": "rhea.claims@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "medical_reviewer",
        "persona": "Medical reviewer",
        "team": "Medical Legal Review",
        "status": "active",
        "modules": ["claims-governance", "evidence", "compliance", "workflow-orchestration"],
        "last_login": "2026-04-29 18:12 IST",
    },
    "kabir.compliance@medguard.ai": {
        "id": "USR-004",
        "name": "Kabir Sethi",
        "email": "kabir.compliance@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "compliance_reviewer",
        "persona": "Compliance reviewer",
        "team": "Regulatory Review",
        "status": "active",
        "modules": ["compliance", "claims-governance", "responsible-ai", "evidence"],
        "last_login": "2026-04-30 09:05 IST",
    },
    "nina.email@medguard.ai": {
        "id": "USR-005",
        "name": "Nina Thomas",
        "email": "nina.email@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "qa_specialist",
        "persona": "Email QA specialist",
        "team": "Omnichannel QA",
        "status": "active",
        "modules": ["email-qa", "compliance", "workflow-orchestration", "analytics"],
        "last_login": "2026-04-30 08:42 IST",
    },
    "omar.affiliate@medguard.ai": {
        "id": "USR-006",
        "name": "Omar Khan",
        "email": "omar.affiliate@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "local_market_reviewer",
        "persona": "Local market content lead",
        "team": "India Affiliate",
        "status": "active",
        "modules": ["localization", "workflow-orchestration", "claims-governance", "analytics"],
        "last_login": "2026-04-29 16:25 IST",
    },
    "richa@medguard.ai": {
        "id": "USR-012",
        "name": "Richa B Kumar",
        "email": "richa@medguard.ai",
        "password": "syrencloud",
        "role": "workflow_owner",
        "persona": "Enterprise workflow owner",
        "team": "Global Content Governance",
        "status": "active",
        "modules": ROLE_MODULES["workflow_owner"],
        "last_login": "Never",
    },
    "isha.author@medguard.ai": {
        "id": "USR-007",
        "name": "Isha Nair",
        "email": "isha.author@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "content_author",
        "persona": "Content author",
        "team": "Global Content Studio",
        "status": "active",
        "modules": ROLE_MODULES["content_author"],
        "last_login": "2026-05-03 16:12 IST",
    },
    "liam.regulatory@medguard.ai": {
        "id": "USR-008",
        "name": "Liam Carter",
        "email": "liam.regulatory@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "regulatory_reviewer",
        "persona": "Regulatory reviewer",
        "team": "Global Regulatory Affairs",
        "status": "active",
        "modules": ROLE_MODULES["regulatory_reviewer"],
        "last_login": "2026-05-03 15:44 IST",
    },
    "sofia.legal@medguard.ai": {
        "id": "USR-009",
        "name": "Sofia Mendes",
        "email": "sofia.legal@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "legal_reviewer",
        "persona": "Legal reviewer",
        "team": "Legal and Privacy",
        "status": "active",
        "modules": ROLE_MODULES["legal_reviewer"],
        "last_login": "2026-05-03 12:09 IST",
    },
    "ethan.approver@medguard.ai": {
        "id": "USR-010",
        "name": "Ethan Walsh",
        "email": "ethan.approver@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "approver",
        "persona": "Global approver",
        "team": "Approval Governance",
        "status": "active",
        "modules": ROLE_MODULES["approver"],
        "last_login": "2026-05-03 10:30 IST",
    },
    "audit.viewer@medguard.ai": {
        "id": "USR-011",
        "name": "Priya Das",
        "email": "audit.viewer@medguard.ai",
        "password": DEMO_PASSWORD,
        "role": "audit_viewer",
        "persona": "Audit viewer",
        "team": "Quality Assurance",
        "status": "active",
        "modules": ROLE_MODULES["audit_viewer"],
        "last_login": "2026-05-02 17:48 IST",
    },
}

def normalize_email(email: str) -> str:
    return email.strip().lower()

def public_user(user: Dict[str, Any], include_password: bool = False) -> Dict[str, Any]:
    enriched = dict(user)
    role = enriched.get("role", "user")
    modules = enriched.get("modules") or ROLE_MODULES.get(role, ROLE_MODULES["user"])
    enriched["modules"] = modules
    role = enriched.get("role", "user")
    enriched["permission_sets"] = ROLE_PERMISSION_SETS.get(role, ROLE_PERMISSION_SETS["user"])
    enriched["role_groups"] = [MODULE_PERMISSION_LABELS.get(module, module.replace("-", " ").title()) for module in modules]
    enriched["markets"] = ROLE_MARKETS.get(role, ["Assigned markets"])
    enriched["stage_access"] = [
        stage["id"]
        for stage in ORCHESTRATION_STAGES
        if role in {"super_admin", "admin"} or stage["id"] in ROLE_STAGE_ACCESS.get(role, []) or any(module in modules for module in stage.get("modules", []))
    ] if "ORCHESTRATION_STAGES" in globals() else []
    if include_password:
        return enriched
    return {key: value for key, value in enriched.items() if key != "password"}

def find_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    return next((user for user in USERS.values() if user["id"] == user_id), None)

def next_user_id() -> str:
    numbers = [int(user["id"].split("-")[-1]) for user in USERS.values() if user["id"].startswith("USR-")]
    return f"USR-{max(numbers, default=0) + 1:03d}"

def require_admin(actor_email: str) -> Dict[str, Any]:
    actor = USERS.get(normalize_email(actor_email))
    if not actor or actor["status"] != "active" or actor["role"] not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return actor

def can_access_stage(actor: Optional[Dict[str, Any]], stage_id: str, write: bool = False) -> bool:
    if not actor or actor.get("status") != "active":
        return False
    role = actor.get("role", "user")
    if role in {"super_admin", "admin"}:
        return True
    if write and role == "audit_viewer":
        return False
    if stage_id in ROLE_STAGE_ACCESS.get(role, []):
        return True
    if role in ROLE_STAGE_ACCESS:
        return False
    stage = stage_by_id(stage_id) if "ORCHESTRATION_STAGES" in globals() else None
    modules = actor.get("modules") or ROLE_MODULES.get(role, [])
    return bool(stage and any(module in modules for module in stage.get("modules", [])))

def can_manage_target(actor: Dict[str, Any], target: Dict[str, Any]) -> bool:
    return actor["role"] == "super_admin" or target["role"] != "super_admin"

ROLE_PERMISSION_SETS: Dict[str, List[str]] = {
    "super_admin": ["Platform Administration", "User Management", "All Workflow Stages", "Connector Administration", "Audit Export", "Password Controls"],
    "admin": ["Workflow Oversight", "Connector Management", "Audit Review", "Executive Dashboard", "Stage Decisions"],
    "workflow_owner": ["All Workflow Stages", "Document Bundles", "DAM Review", "Content Library", "IMCP Framework", "Reviewer Decisions"],
    "content_author": ["Brief Authoring", "Draft Creation", "Document Bundles", "Reviewer Handoff"],
    "medical_reviewer": ["Claims Validation", "Evidence Review", "MLR Comments", "Medical Decision"],
    "regulatory_reviewer": ["Label Alignment", "Regulatory Review", "MLR Comments", "Policy Escalation"],
    "compliance_reviewer": ["Policy Checks", "Compliance Approval", "Exception Review", "Audit Review"],
    "legal_reviewer": ["Legal Disclosure", "Privacy Review", "Exception Notes"],
    "local_market_reviewer": ["Localization Review", "Local Approval", "Market Rule Review"],
    "qa_specialist": ["Channel QA", "Litmus Evidence", "Link Validation", "Publish Readiness"],
    "approver": ["Approval Gates", "Final Authorization", "Escalation Decisions"],
    "audit_viewer": ["Read-only Audit", "Evidence Review", "Export View"],
    "user": ["Assigned Stage Work", "Profile Management", "Reviewer Decisions"],
}

MODULE_PERMISSION_LABELS: Dict[str, str] = {
    "claims-governance": "Claims and references",
    "compliance": "Compliance checks",
    "responsible-ai": "AI governance",
    "workflow-orchestration": "Workflow orchestration",
    "integration-layer": "Connector operations",
    "email-qa": "Channel QA",
    "content-lab": "Content creation",
    "dam": "Asset metadata",
    "evidence": "Evidence review",
    "localization": "Localization review",
    "analytics": "Performance analytics",
    "admin": "Operations administration",
    "poc-readiness": "Pilot governance",
    "media": "Visual review",
}

ROLE_MARKETS: Dict[str, List[str]] = {
    "super_admin": ["Global", "US", "UK", "India", "Saudi Arabia"],
    "admin": ["Global", "US", "UK", "India", "Saudi Arabia"],
    "workflow_owner": ["Global", "US", "UK", "India", "Saudi Arabia"],
    "local_market_reviewer": ["India"],
    "regulatory_reviewer": ["Global", "US", "UK"],
    "compliance_reviewer": ["Global"],
    "qa_specialist": ["Global", "India"],
    "user": ["Assigned markets"],
}

ORCHESTRATION_STAGES: List[Dict[str, Any]] = [
    {
        "id": "briefing",
        "order": 1,
        "name": "Briefing & Planning",
        "trigger": "On Content Created",
        "system": "Veeva Vault",
        "agents": ["Claim Agent", "Regulatory Agent", "Compliance Policy Agent", "Audit Agent"],
        "score": 78,
        "risk": "medium",
        "recommendation": "Rework before proceeding",
        "issues": ["Claim not mapped to label", "Missing safety disclaimer"],
        "output": "Approved brief readiness signal with risk flags and owner actions.",
        "kpis": ["Early Risk Detection Rate", "Claim Completeness", "Brief Block Rate"],
        "sample": {
            "compliance_score": 0.78,
            "risk_flags": ["Missing reference", "Off-label risk"],
            "recommendation": "Rework",
        },
    },
    {
        "id": "content-created",
        "order": 2,
        "name": "Content Creation",
        "trigger": "On Content Save",
        "system": "Authoring Workspace",
        "agents": ["Claim Agent", "Reference Agent", "Compliance Policy Agent", "Security Agent"],
        "score": 82,
        "risk": "high",
        "recommendation": "Auto-suggest corrected claim",
        "issues": ["Evidence supports 8 years, content states 10 years", "Reference gap for long-term immunity claim"],
        "output": "Claim accuracy report with overstatement detection and rewrite suggestion.",
        "kpis": ["Claim Accuracy", "Overstatement Detection Rate", "Rework Reduction"],
        "sample": {
            "claim_accuracy": 0.82,
            "evidence_gap": "2 years overclaim",
            "risk": "HIGH",
        },
    },
    {
        "id": "medical-review",
        "order": 3,
        "name": "Medical & Regulatory Review",
        "trigger": "On Stage Transition",
        "system": "Internal MLR Tools",
        "agents": ["Claim Agent", "Reference Agent", "Regulatory Agent", "Compliance Policy Agent", "Audit Agent"],
        "score": 91,
        "risk": "medium",
        "recommendation": "Revise risk section",
        "issues": ["Fair balance weak", "Adverse effects section needs expansion"],
        "output": "Medical review packet with evidence traceability and fair-balance watchouts.",
        "kpis": ["Fair Balance Index", "Off-label Violation Rate", "Evidence Traceability", "Medical Review Cycle Time"],
        "sample": {
            "claim_validation_score": 0.91,
            "off_label_risk": False,
            "fair_balance_score": 0.67,
            "recommendation": "Revise risk section",
        },
    },
    {
        "id": "compliance-approval",
        "order": 4,
        "name": "Compliance Approval",
        "trigger": "On Approval Request",
        "system": "Veeva Vault",
        "agents": ["Compliance Policy Agent", "Risk Agent", "Audit Agent", "KPI Agent"],
        "score": 95,
        "risk": "low",
        "recommendation": "Approval ready",
        "issues": ["No blockers detected", "Audit trail complete"],
        "output": "Policy coverage and approval readiness report.",
        "kpis": ["Policy Adherence", "Compliance Pass Rate", "Audit Readiness Score"],
        "sample": {
            "policy_match": 0.95,
            "risk_level": "LOW",
            "approval_ready": True,
        },
    },
    {
        "id": "localization",
        "order": 5,
        "name": "Local Adaptation & Translation",
        "trigger": "On Localization Upload",
        "system": "Affiliate Content Hub",
        "agents": ["Localization Agent", "Regulatory Agent", "Claim Agent", "Audit Agent"],
        "score": 93,
        "risk": "low",
        "recommendation": "Review semantic drift before local submission",
        "issues": ["Semantic drift at 7%", "India market caveat confirmed"],
        "output": "Localized content check with semantic drift and local compliance signal.",
        "kpis": ["Localization Accuracy", "Drift Score", "Local Rework Rate"],
        "sample": {
            "semantic_drift": 0.07,
            "local_compliance": "PASS",
            "risk": "LOW",
        },
    },
    {
        "id": "local-approval",
        "order": 6,
        "name": "Local Approval",
        "trigger": "On Approval Request",
        "system": "Local MLR Tools",
        "agents": ["Regulatory Agent", "Compliance Policy Agent", "Audit Agent"],
        "score": 90,
        "risk": "medium",
        "recommendation": "Proceed with local reviewer confirmation",
        "issues": ["Country policy owner pending final note", "Local sign-off path captured"],
        "output": "Country approval readiness signal and local audit entry.",
        "kpis": ["Country Compliance", "Approval Cycle Time"],
        "sample": {
            "country_compliance": 0.90,
            "approval_cycle_time_risk": "MEDIUM",
        },
    },
    {
        "id": "qa",
        "order": 7,
        "name": "Channel Prep & QA",
        "trigger": "On QA Run",
        "system": "Litmus",
        "agents": ["QA Agent", "Compliance Policy Agent", "Security Agent", "Audit Agent"],
        "score": 96,
        "risk": "medium",
        "recommendation": "Fix broken link before publish",
        "issues": ["Broken link", "Tracking compliance passed"],
        "output": "Litmus QA and compliance evidence package.",
        "kpis": ["Deliverability Score", "QA Pass Rate", "Compliance QA"],
        "sample": {
            "render_score": 0.96,
            "tracking_compliance": "PASS",
            "issues": ["Broken link"],
        },
    },
    {
        "id": "publish",
        "order": 8,
        "name": "Publish & Distribute",
        "trigger": "On Publish Request",
        "system": "Veeva CRM",
        "agents": ["Compliance Policy Agent", "Security Agent", "KPI Agent", "Feedback Learning Agent"],
        "score": 98,
        "risk": "low",
        "recommendation": "Ready to publish",
        "issues": ["Audience check passed", "Final compliance lock captured"],
        "output": "Publish compliance signal with post-launch KPI monitoring.",
        "kpis": ["Compliance Incident Rate", "Engagement vs Risk Ratio", "Time to Market"],
        "sample": {
            "publish_compliance": True,
            "audience_check": "PASS",
        },
    },
]

CONNECTIONS: List[Dict[str, Any]] = [
    {"id": "microsoft-entra", "name": "Microsoft Entra ID", "logo_text": "M", "logo_color": "#2563eb", "icon": "key", "scope": "SSO, conditional access, role groups, user provisioning", "status": "connected", "health": 99, "auth_method": "OIDC + SAML SSO", "owner": "Identity Platform", "scopes": ["openid", "profile", "email", "groups.read", "scim.write"], "handoff": "SSO: enterprise login, MFA, and role-group mapping", "last_event": "Richa B Kumar mapped to Workflow Owner role group", "last_sync": "1 min ago", "latency_ms": 96, "actions": ["test", "edit", "revoke_sessions", "view_logs", "disable"]},
    {"id": "google-cloud-identity", "name": "Google Cloud Identity", "logo_text": "G", "logo_color": "#ea4335", "icon": "key", "scope": "SSO federation, workspace identity, service account trust", "status": "connected", "health": 97, "auth_method": "OIDC federation", "owner": "Cloud Identity", "scopes": ["openid", "profile", "email", "admin.directory.group.readonly"], "handoff": "SSO: Google workspace sign-in and group claims", "last_event": "Google sign-in policy verified", "last_sync": "4 min ago", "latency_ms": 118, "actions": ["test", "edit", "revoke_sessions", "view_logs", "disable"]},
    {"id": "veeva-vault", "name": "Veeva Vault", "logo_text": "V", "logo_color": "#ff7a00", "icon": "asset", "scope": "Documents, claims, references, MLR lifecycle", "status": "connected", "health": 98, "auth_method": "OAuth 2.0 + SSO", "owner": "Global Content Operations", "scopes": ["documents.read", "claims.read", "audit.write", "workflow.subscribe"], "handoff": "Webhook: content save, stage transition, approval request", "last_event": "Medical review packet synced 09:42 IST", "last_sync": "2 min ago", "latency_ms": 142, "actions": ["test", "edit", "rotate_secret", "view_logs", "disable"]},
    {"id": "veeva-crm", "name": "Veeva CRM", "logo_text": "V", "logo_color": "#f97316", "icon": "workflow", "scope": "Campaigns, approved emails, channel activation", "status": "connected", "health": 96, "auth_method": "Named credential", "owner": "Commercial Operations", "scopes": ["campaigns.read", "approved_email.write", "audience.read"], "handoff": "API: publish readiness and channel metadata", "last_event": "Publish gate opened for India HCP email", "last_sync": "8 min ago", "latency_ms": 188, "actions": ["test", "edit", "revoke_sessions", "view_logs", "disable"]},
    {"id": "litmus", "name": "Litmus", "logo_text": "L", "logo_color": "#14b8a6", "icon": "email", "scope": "Email rendering, links, spam, accessibility, QA evidence", "status": "connected", "health": 94, "auth_method": "API key vault", "owner": "Omnichannel QA", "scopes": ["previews.read", "links.read", "spam.read", "evidence.write"], "handoff": "Webhook: QA run completed", "last_event": "Broken link detected in Outlook package", "last_sync": "11 min ago", "latency_ms": 231, "actions": ["test", "edit", "rotate_secret", "view_logs", "disable"]},
    {"id": "mlr", "name": "Internal MLR Tools", "logo_text": "MLR", "logo_color": "#4338ca", "icon": "compliance", "scope": "Reviewer queue, medical/legal/regulatory decisioning", "status": "connected", "health": 91, "auth_method": "SAML + service user", "owner": "Regulatory Review", "scopes": ["reviews.read", "decisions.write", "comments.read", "audit.write"], "handoff": "API: reviewer packet and decision capture", "last_event": "Fair balance revision requested", "last_sync": "16 min ago", "latency_ms": 204, "actions": ["test", "edit", "view_logs", "disable"]},
    {"id": "idp-ocr", "name": "IDP / OCR Intake", "logo_text": "OCR", "logo_color": "#0f766e", "icon": "evidence", "scope": "Document extraction, reference parsing, metadata tagging", "status": "candidate", "health": 72, "auth_method": "Secure connector", "owner": "Platform Governance", "scopes": ["documents.extract", "metadata.write"], "handoff": "Batch ingestion: uploaded reference packets", "last_event": "Connector design ready for validation", "last_sync": "Pending", "latency_ms": 0, "actions": ["test", "edit", "disable"]},
]

ARCHITECTURE_FLOW: Dict[str, Any] = {
    "summary": {
        "title": "Embedded AI Validation Architecture",
        "description": "A controlled validation layer that listens to enterprise workflow events, routes work to specialized checks, and returns reviewer-ready actions without replacing source systems.",
        "flow": ["Connected systems", "Connectivity layer", "Trigger points", "AI validation layer", "Action outputs", "Users and governance"],
    },
    "connected_systems": [
        {"name": "Veeva Vault", "items": ["Documents", "Claims and references", "Submissions", "Metadata"], "status": "connected"},
        {"name": "Veeva CRM", "items": ["Campaigns", "Approved emails", "HCP account metadata", "Channel activation"], "status": "connected"},
        {"name": "Litmus", "items": ["Email QA", "Rendering", "Spam testing", "Link validation"], "status": "connected"},
        {"name": "eTMF / MLR Tools", "items": ["Review workflows", "Approvals", "Audit logs"], "status": "connected"},
        {"name": "IDP / RPA / OCR", "items": ["Document extraction", "Data capture", "Auto tagging"], "status": "connected"},
        {"name": "Other Systems", "items": ["ERP / PLM", "DAM", "Local tools"], "status": "connected"},
    ],
    "connectivity_layer": [
        {"name": "APIs", "detail": "REST / GraphQL contracts for assets, claims, approvals, and metadata"},
        {"name": "Webhooks", "detail": "Event triggers from save, transition, approval, QA, and publish actions"},
        {"name": "File / Batch Ingestion", "detail": "Secure document packages for extracted references and historical decisions"},
        {"name": "Secure Connectors", "detail": "SSO, role mapping, encrypted transport, and scoped access tokens"},
        {"name": "Message Broker", "detail": "Queue-based routing for parallel validation and resilient retries"},
    ],
    "trigger_points": [
        {"name": "Content Created / Saved", "system": "Veeva Vault", "payload": "asset_id, content_type, claim_ids, market"},
        {"name": "Stage Transition", "system": "MLR workflow", "payload": "from_stage, to_stage, reviewer_group"},
        {"name": "Approval Requested", "system": "Veeva Vault", "payload": "approval_id, policy_scope, evidence_pack"},
        {"name": "Localization Uploaded", "system": "Affiliate tools", "payload": "source_asset, locale, translated_text"},
        {"name": "QA Triggered", "system": "Litmus", "payload": "render_report, links, spam_score"},
        {"name": "Content Published", "system": "Veeva CRM", "payload": "channel, audience_segment, publish_window"},
    ],
    "agent_layer": [
        {"name": "Claim Agent", "checks": ["Extract claims", "Classify claim type", "Map to indication", "Normalize wording"]},
        {"name": "Reference Agent", "checks": ["Find references", "Validate evidence", "Evidence strength", "Linkage score"]},
        {"name": "Regulatory Agent", "checks": ["SmPC / label check", "Off-label detection", "Country regulation", "Disclosure check"]},
        {"name": "Compliance Policy Agent", "checks": ["Policy mapping", "SOP validation", "Brand guardrails", "Fair balance"]},
        {"name": "Localization Agent", "checks": ["Translation quality", "Semantic drift", "Local regulations", "Cultural fit"]},
        {"name": "Security Agent", "checks": ["PII / PHI scan", "Access control", "Data leakage", "Content integrity"]},
        {"name": "QA Agent", "checks": ["Rendering", "Spam score", "Links and tracking", "Inbox placement"]},
        {"name": "Audit Agent", "checks": ["Lineage", "Version history", "Audit trail", "Immutable logs"]},
        {"name": "KPI Agent", "checks": ["KPI calculation", "Benchmarking", "Trend analysis", "Insights"]},
        {"name": "Feedback Learning Agent", "checks": ["Reviewer feedback", "Override analysis", "Model improvement", "Confidence scoring"]},
    ],
    "orchestrator_layer": [
        {"name": "Input Normalizer", "detail": "Extracts content, metadata, claims, references, market, and channel context"},
        {"name": "Agent Router", "detail": "Selects relevant validation checks based on stage trigger and risk context"},
        {"name": "Parallel Execution", "detail": "Runs independent checks together while preserving audit evidence"},
        {"name": "Result Aggregator", "detail": "Merges scores, blockers, confidence, and reviewer notes"},
        {"name": "Decision Engine", "detail": "Returns pass, rework, or escalate using policy thresholds"},
        {"name": "Response Generator", "detail": "Creates inline recommendations, API response, audit event, and KPI signal"},
    ],
    "intelligence_layer": [
        {"name": "LLM Layer", "detail": "Enterprise model gateway with source-grounded prompting"},
        {"name": "RAG and Knowledge Graph", "detail": "Policies, labels, claims, studies, references, and reviewer decisions"},
        {"name": "Rules Engine", "detail": "Business rules, blocker thresholds, market rules, and approval gates"},
        {"name": "NLP / NER / Classifiers", "detail": "Claims, indications, risks, safety language, and channel markers"},
        {"name": "Similarity Engine", "detail": "Claim-to-evidence and translation drift matching"},
    ],
    "data_context_layer": [
        {"name": "Content Metadata", "detail": "Brand, indication, audience, market, channel, lifecycle state"},
        {"name": "Claims Repository", "detail": "Approved claims, variants, permitted markets, expiry, owner"},
        {"name": "Reference DB", "detail": "Studies, publications, labels, guidelines, and source snippets"},
        {"name": "Regulatory Knowledge Base", "detail": "SmPC, SOPs, policy rules, local regulations, and disclosures"},
        {"name": "Historical Decisions", "detail": "Approvals, overrides, rework reasons, reviewer patterns"},
    ],
    "output_action_layer": [
        {"name": "Real-time validation response", "items": ["Compliance score", "Risk flags", "Recommendations", "Confidence score"]},
        {"name": "Inline UI / API response", "items": ["Non-disruptive", "Contextual", "Actionable"]},
        {"name": "Workflow actions", "items": ["Auto approve low risk", "Send for review", "Escalate high risk", "Block critical risk"]},
        {"name": "Audit and lineage output", "items": ["Traceability", "Evidence links", "Decision logs"]},
        {"name": "Alerts and notifications", "items": ["Email / app", "SLA alerts", "Escalation rules"]},
        {"name": "KPI streaming", "items": ["Real-time metrics", "Pre-aggregated events", "Data to BI / lakehouse"]},
    ],
    "consumers": [
        "Medical Reviewers",
        "Regulatory Affairs",
        "Compliance Teams",
        "Local Affiliates",
        "Marketing Ops",
        "Auditors",
        "Leadership / Insights",
        "AI Governance Team",
    ],
    "governance_controls": [
        "Role based access control",
        "Data privacy and consent controls",
        "Audit logs with immutable review evidence",
        "Model governance and explainability",
        "AI ethics and bias monitoring",
        "Validation of AI outputs",
        "Periodic policy and model review",
    ],
    "validation_workflow": [
        {"name": "Normalize Input", "owner": "Orchestrator", "output": "Content, metadata, market, channel, claims"},
        {"name": "Extract Claims", "owner": "Claim Agent", "output": "Claim inventory and claim type"},
        {"name": "Validate Evidence", "owner": "Reference Agent", "output": "Evidence strength and reference gap"},
        {"name": "Check Policy", "owner": "Regulatory + Policy Agents", "output": "Label, SOP, fair-balance, and market checks"},
        {"name": "Security Scan", "owner": "Security Agent", "output": "PII/PHI and integrity status"},
        {"name": "Score Risk", "owner": "Decision Engine", "output": "Risk tier, confidence, and blockers"},
        {"name": "Reviewer Action", "owner": "Human reviewer", "output": "Accept, override, or escalate with reason"},
        {"name": "Audit + Learn", "owner": "Audit + Feedback Agents", "output": "Lineage, KPI event, feedback signal"},
    ],
}

COMPLIANCE_KPIS: Dict[str, Any] = {
    "compliance_health": [
        {"label": "Overall Compliance Score", "value": "92%", "trend": "+4 pts"},
        {"label": "Audit Readiness", "value": "96%", "trend": "+6 pts"},
        {"label": "Risk Heatmap", "value": "India: Medium", "trend": "1 market needs review"},
    ],
    "efficiency_gains": [
        {"label": "Review Cycle Time", "value": "-28%", "trend": "7.8d to 5.6d"},
        {"label": "Rework", "value": "-35%", "trend": "preventable comments down"},
        {"label": "Time to Market", "value": "-22%", "trend": "global-to-local handoff faster"},
    ],
    "ai_performance": [
        {"label": "AI Accuracy", "value": "89%", "trend": "+7 pts"},
        {"label": "Override Rate", "value": "12%", "trend": "-5 pts"},
        {"label": "Trust Score", "value": "81%", "trend": "+9 pts"},
    ],
    "content_intelligence": [
        {"label": "Reuse Rate", "value": "68%", "trend": "+11 pts"},
        {"label": "Claim Consistency", "value": "94%", "trend": "+8 pts"},
        {"label": "Evidence Traceability", "value": "91%", "trend": "+13 pts"},
    ],
    "market_heatmap": [
        {"market": "India", "flag": "IN", "risk": "medium", "score": 88, "assets": 18, "blocked": 3, "sla": "91%"},
    ],
}

FIXED_BRAND = "Respivara"
FIXED_MARKET = "India"
FIXED_CHANNEL = "Veeva CRM"
FIXED_CHANNELS = ["Veeva CRM", "Vault", "Litmus"]
FIXED_CONTENT_TYPES = ["Campaign Brief", "Email", "CLM / eDetail Aid", "HCP Leave Behind"]

AUDIT_EVENTS: List[Dict[str, Any]] = [
    {"id": "AUD-001", "stage": "Briefing & Planning", "trigger": "On Content Created", "severity": "medium", "source_system": "Veeva CRM", "asset_id": "AST-RESP-BRIEF-041", "actor_id": "SYSTEM", "actor_email": "system@medguard.ai", "agent_output": "Missing safety disclaimer", "decision": "AI recommended rework", "reviewer": "System", "reason": "Initial scan", "timestamp": "2026-05-04 09:10 IST", "final_recommendation": "Rework", "evidence_links": ["DOC-BRIEF-RESP-041", "DOC-SAF-RESP-022"]},
    {"id": "AUD-002", "stage": "Content Creation", "trigger": "On Content Save", "severity": "high", "source_system": "Authoring Workspace", "asset_id": "AST-RESP-EMAIL-042", "actor_id": "SYSTEM", "actor_email": "system@medguard.ai", "agent_output": "2 years overclaim", "decision": "AI recommended rework", "reviewer": "System", "reason": "Reference supports 8 years", "timestamp": "2026-05-04 09:18 IST", "final_recommendation": "Auto-suggest corrected claim", "evidence_links": ["DOC-CSR-RESP-P3-118", "DOC-CLAIM-RESP-008"]},
    {"id": "AUD-003", "stage": "Medical & Regulatory Review", "trigger": "On Stage Transition", "severity": "medium", "source_system": "Internal MLR Tools", "asset_id": "AST-RESP-EMAIL-042", "actor_id": "SYSTEM", "actor_email": "system@medguard.ai", "agent_output": "Fair balance score 0.67", "decision": "AI recommended revision", "reviewer": "System", "reason": "Risk section thin", "timestamp": "2026-05-04 09:35 IST", "final_recommendation": "Revise risk section", "evidence_links": ["DOC-SAF-RESP-022", "DOC-RESP-FDA-FAIR-062"]},
    {"id": "AUD-004", "stage": "Compliance Approval", "trigger": "Approval authority validation", "severity": "low", "source_system": "Veeva Vault", "asset_id": "AST-CARD-CLM-008", "actor_id": "USR-004", "actor_email": "kabir.compliance@medguard.ai", "agent_output": "SOP mapping complete, approval matrix current", "decision": "Reviewer accepted", "reviewer": "Kabir Sethi", "reason": "Policy coverage 96%; no legal exception open", "timestamp": "2026-05-04 10:05 IST", "final_recommendation": "Approve for localization", "evidence_links": ["DOC-POL-GLB-004", "DOC-CARD-PI-2026"]},
    {"id": "AUD-005", "stage": "Local Adaptation & Translation", "trigger": "Semantic drift validation", "severity": "medium", "source_system": "Localization Library", "asset_id": "AST-RESP-IND-LB-018", "actor_id": "USR-007", "actor_email": "isha.local@medguard.ai", "agent_output": "Two glossary terms require affiliate confirmation", "decision": "Reviewer requested clarification", "reviewer": "Isha Nair", "reason": "Local caveat and trademark legend reviewed", "timestamp": "2026-05-04 10:21 IST", "final_recommendation": "Request local glossary update", "evidence_links": ["DOC-LOCAL-IND-018"]},
    {"id": "AUD-006", "stage": "Channel Prep & QA", "trigger": "Litmus pre-send QA", "severity": "high", "source_system": "Litmus", "asset_id": "AST-IMM-EMAIL-114", "actor_id": "USR-008", "actor_email": "noah.qa@medguard.ai", "agent_output": "Broken prescribing information URL in Outlook package", "decision": "AI recommended rework", "reviewer": "Noah QA", "reason": "Link and CTA validation failed", "timestamp": "2026-05-04 10:34 IST", "final_recommendation": "Fix URL before publish", "evidence_links": ["DOC-IMM-QA-LIT-114"]},
]

SAMPLE_MEDIA_FILES: List[Dict[str, Any]] = [
    {
        "id": "dam-brief",
        "name": "Respivara Campaign Brief",
        "type": "Campaign Brief",
        "mime_type": "text/html",
        "url": "/samples/respivara-brief.html",
        "thumbnail_url": "/samples/respivara-brief-preview.svg",
        "source_system": "Veeva CRM",
        "connector_status": "connected",
        "stage_ids": ["briefing", "content-created"],
        "preview": "Objectives, audience, channels, claim intent, market constraints, and timeline.",
        "checks": ["brief completeness", "audience fit", "claim intent", "SLA readiness"],
        "risk_notes": ["One source reference is still unmapped to the claim library"],
    },
    {
        "id": "dam-claim-matrix",
        "name": "Respivara Claim Matrix",
        "type": "Claim Matrix",
        "mime_type": "text/html",
        "url": "/samples/respivara-claim-matrix.html",
        "thumbnail_url": "/samples/respivara-claim-matrix-preview.svg",
        "source_system": "Veeva Vault",
        "connector_status": "connected",
        "stage_ids": ["briefing", "content-created", "medical-review"],
        "preview": "Approved master claims, short-form variants, references, permitted markets, and expiry metadata.",
        "checks": ["claim registry", "evidence links", "market eligibility", "expiry"],
        "risk_notes": ["Short-form email variant requires reviewer confirmation"],
    },
    {
        "id": "media-email-html",
        "name": "Respivara HCP Email HTML",
        "type": "Email HTML",
        "mime_type": "text/html",
        "url": "/samples/respivara-email.html",
        "thumbnail_url": "/samples/respivara-email-preview.svg",
        "source_system": "DAM",
        "connector_status": "connected",
        "stage_ids": ["content-created", "qa", "publish"],
        "preview": "Hero, claim block, safety module, prescribing information CTA",
        "checks": ["rendering", "links", "tracking", "accessibility"],
        "risk_notes": ["One prescribing information link currently returns 404"],
    },
    {
        "id": "media-email-copydeck",
        "name": "Respivara Approved Email Copy Deck",
        "type": "Email copy deck",
        "mime_type": "text/html",
        "url": "/samples/respivara-content-pack.html",
        "thumbnail_url": "/samples/respivara-email-preview.svg",
        "source_system": "Veeva CRM",
        "connector_status": "connected",
        "stage_ids": ["content-created", "medical-review", "compliance-approval", "qa"],
        "preview": "Modular email copy deck with subject variants, preheader, hero copy, approved claim module, safety footer, PI CTA, consent metadata, suppression notes, and tracking plan.",
        "checks": ["subject line claim control", "module order", "fair balance", "PI CTA", "tracking tags"],
        "risk_notes": ["Short subject variant must avoid implied treatment superiority."],
    },
    {
        "id": "media-clm-storyboard",
        "name": "Respivara CLM / eDetail Storyboard",
        "type": "CLM storyboard",
        "mime_type": "text/html",
        "url": "/samples/respivara-content-pack.html",
        "thumbnail_url": "/samples/respivara-claim-matrix-preview.svg",
        "source_system": "Veeva CRM",
        "connector_status": "connected",
        "stage_ids": ["content-created", "medical-review", "compliance-approval", "localization", "qa"],
        "preview": "Screen-by-screen eDetail storyboard with rep talk track, claim IDs, reference drawer behavior, safety screen, local caveat placeholder, CRM interaction metadata, and approval handoff notes.",
        "checks": ["screen sequence", "claim ID lock", "reference drawer", "safety prominence", "rep prompt compliance"],
        "risk_notes": ["Screen 2 evidence note requires endpoint qualifier before medical approval."],
    },
    {
        "id": "media-veeva-metadata-pack",
        "name": "Respivara Veeva CRM Metadata and Audience Pack",
        "type": "Veeva CRM metadata",
        "mime_type": "text/html",
        "url": "/samples/respivara-supporting-validation-pack.html",
        "thumbnail_url": "/samples/publish-readiness-preview.svg",
        "source_system": "Veeva CRM",
        "connector_status": "connected",
        "stage_ids": ["content-created", "qa", "publish"],
        "preview": "Campaign object, audience segment, consent flags, suppression rules, field mappings, UTM taxonomy, owner matrix, publish window, and rollback contact set for the Respivara India launch.",
        "checks": ["audience consent", "suppression", "field mapping", "UTM taxonomy", "publish owner"],
        "risk_notes": ["Suppression file timestamp must be refreshed within 24 hours of publish."],
    },
    {
        "id": "media-leavebehind-pdf",
        "name": "Respivara HCP Leave Behind PDF",
        "type": "HCP Leave Behind",
        "mime_type": "text/html",
        "url": "/samples/respivara-leavebehind-content.html",
        "thumbnail_url": "/samples/respivara-brochure-preview.svg",
        "source_system": "Veeva Vault",
        "connector_status": "connected",
        "stage_ids": ["content-created", "medical-review", "compliance-approval", "localization", "local-approval", "qa", "publish"],
        "preview": "Two-page HCP leave-behind with cover message, patient-identification criteria, approved claim module, evidence sidebar, safety block, PI QR/link, local disclaimer, print specs, and MLR footer.",
        "checks": ["print layout", "claim placement", "safety prominence", "PI QR", "local disclaimer", "MLR footer"],
        "risk_notes": ["Page 1 benefit panel must not visually overpower the page 2 safety and PI references."],
    },
    {
        "id": "media-leavebehind-printer-pack",
        "name": "Respivara Leave Behind Print Production Pack",
        "type": "Print production pack",
        "mime_type": "text/html",
        "url": "/samples/respivara-leavebehind-validation.html",
        "thumbnail_url": "/samples/publish-readiness-preview.svg",
        "source_system": "Veeva Vault",
        "connector_status": "connected",
        "stage_ids": ["qa", "publish"],
        "preview": "Printer-ready production evidence with bleed, trim, safe area, QR verification, color accessibility, PDF/A export, version lock, and final distribution control.",
        "checks": ["bleed and trim", "safe area", "QR scan", "PDF/A", "version lock", "distribution control"],
        "risk_notes": ["Printed piece requires final QR scan evidence after printer proof generation."],
    },
    {
        "id": "media-hero-image",
        "name": "Respivara Hero Creative",
        "type": "Image",
        "mime_type": "image/svg+xml",
        "url": "/samples/respivara-hero.svg",
        "thumbnail_url": "/samples/respivara-hero.svg",
        "source_system": "Agency DAM",
        "connector_status": "connected",
        "stage_ids": ["content-created", "medical-review", "localization", "qa"],
        "preview": "Clinical abstract image placeholder used for multimodal review",
        "checks": ["safety prominence", "cultural fit", "layout integrity"],
        "risk_notes": ["Safety copy should remain visible near benefit claim"],
    },
    {
        "id": "media-local-pdf",
        "name": "India Localized Leave Behind",
        "type": "PDF",
        "mime_type": "text/html",
        "url": "/samples/india-leave-behind.html",
        "thumbnail_url": "/samples/respivara-brochure-preview.svg",
        "source_system": "Veeva Vault",
        "connector_status": "connected",
        "stage_ids": ["localization", "local-approval"],
        "preview": "Localized claim, disclaimer, local PI references, MLR footer",
        "checks": ["semantic drift", "local disclaimer", "version lock"],
        "risk_notes": ["Two glossary terms require affiliate confirmation"],
    },
    {
        "id": "dam-publish-pack",
        "name": "Publish Readiness Pack",
        "type": "Activation Package",
        "mime_type": "text/html",
        "url": "/samples/publish-readiness.html",
        "thumbnail_url": "/samples/publish-readiness-preview.svg",
        "source_system": "Veeva CRM",
        "connector_status": "connected",
        "stage_ids": ["publish"],
        "preview": "Audience snapshot, approved channel lock, UTM map, suppression evidence, and monitoring plan.",
        "checks": ["audience lock", "channel readiness", "post-launch KPI stream", "incident monitor"],
        "risk_notes": ["Publish opens only after QA blocker resolution"],
    },
]

DOCUMENT_SOURCES: List[Dict[str, Any]] = [
    {"id": "approved-content", "name": "Approved Content Library", "icon": "content", "status": "connected", "owner": "Global Content Operations", "health": 98},
    {"id": "veeva-vault", "name": "Veeva Vault", "icon": "asset", "status": "connected", "owner": "Global MLR Operations", "health": 98},
    {"id": "veeva-crm", "name": "Veeva CRM", "icon": "workflow", "status": "connected", "owner": "Commercial Operations", "health": 96},
    {"id": "dam", "name": "Digital Asset Management", "icon": "visual", "status": "connected", "owner": "Brand Studio", "health": 94},
    {"id": "medical-repo", "name": "Internal Medical Repository", "icon": "pharma", "status": "connected", "owner": "Medical Affairs", "health": 95},
    {"id": "regulatory-repo", "name": "Regulatory Document Repository", "icon": "compliance", "status": "connected", "owner": "Regulatory Affairs", "health": 97},
    {"id": "clinical-repo", "name": "Clinical Study Repository", "icon": "evidence", "status": "connected", "owner": "Clinical Evidence", "health": 93},
    {"id": "publication-library", "name": "Publication Library", "icon": "claims", "status": "connected", "owner": "Scientific Communications", "health": 91},
    {"id": "localization-library", "name": "Localization Library", "icon": "localization", "status": "connected", "owner": "Affiliate Operations", "health": 89},
]

LIBRARY_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "DOC-SMPC-RESP-2026",
        "title": "Respivara Global SmPC / Prescribing Information Alignment Pack",
        "source_id": "regulatory-repo",
        "source_name": "Regulatory Document Repository",
        "brand": "Respivara",
        "document_type": "SmPC / Prescribing Information",
        "region": "Global",
        "market": "Global",
        "channel": "All promotional channels",
        "approval_status": "approved",
        "version": "v4.2",
        "effective_date": "2026-03-18",
        "updated_at": "2026-04-26",
        "url": "/reference-docs/ema-qrd-template.pdf",
        "external_url": "https://www.ema.europa.eu/en/human-regulatory-overview/marketing-authorisation/product-information-requirements/product-information-qrd-templates-human",
        "taxonomy": ["IMCP", "label", "indication", "dosage", "safety"],
        "claims": ["Indicated for maintenance treatment in eligible adults", "Risk statements must remain adjacent to benefit claims"],
        "summary": "Current global label context used to check indication, dosage, population, contraindications, and mandatory safety language.",
        "preview": "Label-alignment source for Stage 3 and Stage 4. Includes approved indication, dosage, limitation language, and safety prominence requirements.",
        "evidence_strength": 97,
        "stage_ids": ["briefing", "content-created", "medical-review", "compliance-approval"],
    },
    {
        "id": "DOC-CSR-RESP-P3-118",
        "title": "Respivara RES-301 Phase III Clinical Study Report Summary",
        "source_id": "clinical-repo",
        "source_name": "Clinical Study Repository",
        "brand": "Respivara",
        "document_type": "Clinical Study Report",
        "region": "Global",
        "market": "Global",
        "channel": "Medical review",
        "approval_status": "approved",
        "version": "v2.1",
        "effective_date": "2026-02-14",
        "updated_at": "2026-04-15",
        "url": "/reference-docs/ich-e3-clinical-study-report.pdf",
        "external_url": "https://www.ema.europa.eu/en/ich-e3-structure-content-clinical-study-reports-scientific-guideline",
        "taxonomy": ["IMCP", "clinical evidence", "endpoint", "population", "statistics"],
        "claims": ["Reduced annualized symptom burden versus standard care in the studied adult population", "No superiority claim without endpoint qualification"],
        "summary": "Clinical evidence packet with endpoint, population, duration, comparator, and statistical support metadata.",
        "preview": "Used by claim-to-evidence alignment and comparative/statistical validity checks. Includes endpoint mapping and reviewer-ready evidence snippets.",
        "evidence_strength": 94,
        "stage_ids": ["content-created", "medical-review"],
    },
    {
        "id": "DOC-CLAIM-RESP-008",
        "title": "Respivara Approved Claim Library",
        "source_id": "veeva-vault",
        "source_name": "Veeva Vault",
        "brand": "Respivara",
        "document_type": "Approved Claim Library",
        "region": "Global",
        "market": "Global",
        "channel": "Veeva Approved Email",
        "approval_status": "approved",
        "version": "v5.0",
        "effective_date": "2026-04-01",
        "updated_at": "2026-05-01",
        "url": "/samples/respivara-claim-matrix.html",
        "external_url": "https://www.veeva.com/products/veeva-promomats/claims-management/",
        "taxonomy": ["IMCP", "claim matrix", "references", "permitted markets"],
        "claims": ["Helps reduce symptom burden in eligible adult patients", "Safety information must accompany all efficacy claims"],
        "summary": "Approved master claims, short-form variants, reference IDs, permitted markets, expiry, and owner metadata.",
        "preview": "Supports claim registry creation, reference presence checks, and overclaim detection.",
        "evidence_strength": 96,
        "stage_ids": ["briefing", "content-created", "medical-review", "qa", "publish"],
    },
    {
        "id": "DOC-SAF-RESP-022",
        "title": "Respivara Global Risk and Safety Statement Library",
        "source_id": "medical-repo",
        "source_name": "Internal Medical Repository",
        "brand": "Respivara",
        "document_type": "Safety Statement",
        "region": "Global",
        "market": "Global",
        "channel": "All channels",
        "approval_status": "approved",
        "version": "v3.7",
        "effective_date": "2026-03-25",
        "updated_at": "2026-04-22",
        "url": "/reference-docs/fda-prescription-drug-advertising.pdf",
        "external_url": "https://www.fda.gov/drugs/prescription-drug-advertising/prescription-drug-advertising-questions-and-answers",
        "taxonomy": ["IMCP", "safety", "fair balance", "warnings"],
        "claims": ["Adverse event language must be clearly visible", "Benefit-risk presentation must remain balanced"],
        "summary": "Approved safety modules and placement guidance used for fair-balance and disclosure checks.",
        "preview": "Flags missing risk language, hidden safety copy, and benefit-forward layouts.",
        "evidence_strength": 92,
        "stage_ids": ["briefing", "content-created", "medical-review", "compliance-approval", "qa"],
    },
    {
        "id": "DOC-BRIEF-RESP-041",
        "title": "Respivara Omnichannel HCP Campaign Brief",
        "source_id": "veeva-crm",
        "source_name": "Veeva CRM",
        "brand": "Respivara",
        "document_type": "Campaign Brief",
        "region": "Global",
        "market": "India",
        "channel": "Veeva Approved Email",
        "approval_status": "in_review",
        "version": "v1.3",
        "effective_date": "2026-05-02",
        "updated_at": "2026-05-04",
        "url": "/samples/respivara-brief.html",
        "external_url": "",
        "taxonomy": ["IMCP", "brief", "audience", "channel", "objective"],
        "claims": ["Improve recognition of eligible maintenance therapy patients", "Route high-risk claims to medical review"],
        "summary": "Campaign objective, audience, channels, message hierarchy, owner matrix, and timeline.",
        "preview": "Stage 1 source packet for brief intelligence, audience fit, and handoff planning.",
        "evidence_strength": 86,
        "stage_ids": ["briefing", "content-created"],
    },
    {
        "id": "DOC-BRAND-RESP-012",
        "title": "Respivara Brand and Modular Content Guidelines",
        "source_id": "approved-content",
        "source_name": "Approved Content Library",
        "brand": "Respivara",
        "document_type": "Brand Guideline",
        "region": "Global",
        "market": "Global",
        "channel": "Omnichannel",
        "approval_status": "approved",
        "version": "v2.8",
        "effective_date": "2026-02-20",
        "updated_at": "2026-04-12",
        "url": "/samples/respivara-hero.svg",
        "external_url": "",
        "taxonomy": ["IMCP", "brand", "layout", "modular content"],
        "claims": ["Use approved modular content blocks only", "Clinical imagery must not imply unsupported outcomes"],
        "summary": "Brand typography, visual safety placement, modular content rules, and channel formatting constraints.",
        "preview": "Used by content generation, DAM metadata checks, cultural fit, and channel QA.",
        "evidence_strength": 88,
        "stage_ids": ["content-created", "localization", "qa"],
    },
    {
        "id": "DOC-LOCAL-IND-018",
        "title": "India Local Disclaimer Pack and Promotional Rules Overlay",
        "source_id": "localization-library",
        "source_name": "Localization Library",
        "brand": "Respivara",
        "document_type": "Local Disclaimer",
        "region": "APAC",
        "market": "India",
        "channel": "Print leave-behind",
        "approval_status": "approved",
        "version": "v1.9",
        "effective_date": "2026-04-05",
        "updated_at": "2026-04-28",
        "url": "/samples/india-leave-behind.html",
        "external_url": "",
        "taxonomy": ["IMCP", "local rules", "disclaimer", "translation", "country overlay"],
        "claims": ["Local caveat required for abbreviated claims", "Country-specific safety language must be visible"],
        "summary": "India local disclaimer text, glossary terms, local PI references, and affiliate review requirements.",
        "preview": "Used for localization, local approval, disclaimer fit, and country sign-off checks.",
        "evidence_strength": 91,
        "stage_ids": ["localization", "local-approval"],
    },
    {
        "id": "DOC-QA-RESP-909",
        "title": "Respivara Approved Email HTML and Litmus QA Report",
        "source_id": "dam",
        "source_name": "Digital Asset Management",
        "brand": "Respivara",
        "document_type": "Email HTML / Creative Asset",
        "region": "APAC",
        "market": "India",
        "channel": "Litmus email QA",
        "approval_status": "approved",
        "version": "v3.0",
        "effective_date": "2026-05-03",
        "updated_at": "2026-05-04",
        "url": "/samples/respivara-email.html",
        "external_url": "https://help.litmus.com/article/119-litmus-presend-testing-guide",
        "taxonomy": ["IMCP", "email", "rendering", "links", "tracking"],
        "claims": ["Final content must match MLR lock", "Prescribing information link must resolve"],
        "summary": "Approved email package with rendering, link, tracking, spam, and accessibility evidence.",
        "preview": "Used for channel package assembly, link/CTA validation, tracking checks, and publish readiness.",
        "evidence_strength": 90,
        "stage_ids": ["qa", "publish"],
    },
    {
        "id": "DOC-POL-GLB-004",
        "title": "Global Promotional Policy, SOP, and Approval Matrix",
        "source_id": "regulatory-repo",
        "source_name": "Regulatory Document Repository",
        "brand": "All Brands",
        "document_type": "SOP / Policy",
        "region": "Global",
        "market": "Global",
        "channel": "All promotional channels",
        "approval_status": "approved",
        "version": "v6.4",
        "effective_date": "2026-01-15",
        "updated_at": "2026-04-30",
        "url": "/reference-docs/abpi-code-of-practice.pdf",
        "external_url": "https://www.abpi.org.uk/media/rhwl4tll/240621-abpi-code-of-practice_final.pdf",
        "taxonomy": ["IMCP", "policy", "SOP", "approval matrix", "disclosure"],
        "claims": ["Reviewer authority must match approval matrix", "Exception notes required for policy overrides"],
        "summary": "Policy and SOP baseline used to map global compliance requirements, legal disclaimers, and authority gates.",
        "preview": "Primary Stage 4 source for policy mapping, approval authority, exception handling, and audit completeness.",
        "evidence_strength": 95,
        "stage_ids": ["compliance-approval", "local-approval", "publish"],
    },
    {
        "id": "DOC-CARD-CONG-021",
        "title": "Cardiava Congress Slide Deck Prior Approved Content",
        "source_id": "approved-content",
        "source_name": "Approved Content Library",
        "brand": "Cardiava",
        "document_type": "Congress Material",
        "region": "EU",
        "market": "UK",
        "channel": "Congress / booth",
        "approval_status": "approved",
        "version": "v2.2",
        "effective_date": "2026-03-01",
        "updated_at": "2026-04-20",
        "url": "/samples/publish-readiness.html",
        "external_url": "",
        "taxonomy": ["IMCP", "prior approved content", "congress", "reference reuse"],
        "claims": ["Prior-approved module may be reused only within permitted channel and market"],
        "summary": "Prior-approved scientific content used for reuse scoring and version lineage comparison.",
        "preview": "Useful for content reuse and cross-brand dashboard realism.",
        "evidence_strength": 87,
        "stage_ids": ["briefing", "content-created", "publish"],
    },
]

SAMPLE_MEDIA_FILES.extend([
    {
        "id": "dam-card-clm",
        "name": "Cardiava CLM Detail Aid Package",
        "type": "CLM / eDetail",
        "mime_type": "text/html",
        "url": "/samples/publish-readiness.html",
        "thumbnail_url": "/samples/cardiava-clm-preview.svg",
        "source_system": "Veeva CRM",
        "connector_status": "connected",
        "stage_ids": ["content-created", "medical-review", "qa", "publish"],
        "preview": "Rep-triggered CLM sequence with approved claim modules, reference drawer, safety footer, and call-object metadata.",
        "checks": ["claim module lock", "reference drawer", "rep call metadata", "offline package integrity"],
        "risk_notes": ["Module 3 requires evidence-version confirmation before export."],
    },
    {
        "id": "dam-immunava-banner",
        "name": "Immunava HCP Portal Banner Set",
        "type": "Banner asset",
        "mime_type": "image/svg+xml",
        "url": "/samples/immunava-banner-preview.svg",
        "thumbnail_url": "/samples/immunava-banner-preview.svg",
        "source_system": "Agency DAM",
        "connector_status": "connected",
        "stage_ids": ["content-created", "qa"],
        "preview": "Approved static display units with alt text, claim overlay, ISI placement, and market-specific usage constraints.",
        "checks": ["visual claim OCR", "ISI proximity", "alt text", "size variants"],
        "risk_notes": ["One 300x250 variant has compressed safety copy."],
    },
    {
        "id": "dam-dermexa-social",
        "name": "Dermexa Social-Approved Asset Pack",
        "type": "Social-approved asset",
        "mime_type": "image/svg+xml",
        "url": "/samples/dermexa-social-preview.svg",
        "thumbnail_url": "/samples/dermexa-social-preview.svg",
        "source_system": "Internal DAM",
        "connector_status": "connected",
        "stage_ids": ["compliance-approval", "localization", "qa"],
        "preview": "Static social card variants for markets where promotional social placement is permitted with mandatory fair-balance overlays.",
        "checks": ["jurisdiction eligibility", "fair balance overlay", "commenting constraints", "metadata lock"],
        "risk_notes": ["UK variant requires ABPI social media interaction caveat."],
    },
    {
        "id": "dam-neurovance-webinar",
        "name": "Neurovance Webinar Invite and Reminder Kit",
        "type": "Webinar / virtual event",
        "mime_type": "text/html",
        "url": "/samples/respivara-email.html",
        "thumbnail_url": "/samples/neurovance-webinar-preview.svg",
        "source_system": "SharePoint",
        "connector_status": "connected",
        "stage_ids": ["briefing", "content-created", "qa", "publish"],
        "preview": "Invite, reminder, and post-event follow-up templates with speaker disclosure, registration CTA, and tracking map.",
        "checks": ["speaker disclosure", "CTA routing", "tracking map", "unsubscribe visibility"],
        "risk_notes": ["Speaker affiliation disclosure missing from the short reminder variant."],
    },
    {
        "id": "dam-respivara-patient-brochure",
        "name": "Respivara Patient Support Brochure Artwork",
        "type": "Patient support brochure",
        "mime_type": "text/html",
        "url": "/samples/india-leave-behind.html",
        "thumbnail_url": "/samples/respivara-brochure-preview.svg",
        "source_system": "Veeva Vault",
        "connector_status": "connected",
        "stage_ids": ["localization", "local-approval", "publish"],
        "preview": "Localized patient-support brochure with local contact details, safety statement, and country disclaimer.",
        "checks": ["local disclaimer", "patient readability", "contact details", "version lock"],
        "risk_notes": ["Saudi market copy needs right-to-left layout QA."],
    },
    {
        "id": "dam-immunava-publication-summary",
        "name": "Immunava Publication Summary Visual Abstract",
        "type": "Publication summary",
        "mime_type": "text/html",
        "url": "/samples/respivara-claim-matrix.html",
        "thumbnail_url": "/samples/immunava-publication-preview.svg",
        "source_system": "Publication Library",
        "connector_status": "connected",
        "stage_ids": ["medical-review", "compliance-approval"],
        "preview": "Visual abstract derived from approved publication plan with endpoint callouts, study limitations, and citation metadata.",
        "checks": ["publication plan match", "endpoint fidelity", "limitation language", "citation completeness"],
        "risk_notes": ["Endpoint label requires reviewer notation for short-form use."],
    },
])

LIBRARY_DOCUMENTS.extend([
    {
        "id": "DOC-CARD-PI-2026",
        "title": "Cardiava EU SmPC and PI Crosswalk",
        "source_id": "regulatory-repo",
        "source_name": "Regulatory Document Repository",
        "brand": "Cardiava",
        "document_type": "SmPC / Prescribing Information",
        "region": "EU",
        "market": "UK",
        "channel": "All promotional channels",
        "approval_status": "approved",
        "version": "v3.4",
        "effective_date": "2026-02-18",
        "updated_at": "2026-04-22",
        "url": "/reference-docs/ema-qrd-template.pdf",
        "external_url": "https://www.ema.europa.eu/en/human-regulatory-overview/marketing-authorisation/product-information-requirements/product-information-qrd-templates-human",
        "taxonomy": ["IMCP", "label", "EU", "QRD", "cardiometabolic"],
        "claims": ["Benefit claims require adjacent risk statement", "UK material must follow local code overlay"],
        "summary": "EU/UK product-information crosswalk for indication, dosage, safety, and QRD-aligned product information sections.",
        "preview": "Used by label alignment, disclosure completeness, and local UK compliance checks.",
        "evidence_strength": 93,
        "stage_ids": ["medical-review", "compliance-approval", "local-approval"],
    },
    {
        "id": "DOC-IMM-CSR-224",
        "title": "Immunava Immune Response CSR Evidence Synopsis",
        "source_id": "clinical-repo",
        "source_name": "Clinical Study Repository",
        "brand": "Immunava",
        "document_type": "Clinical Study Report",
        "region": "Global",
        "market": "US",
        "channel": "Medical review",
        "approval_status": "approved",
        "version": "v1.8",
        "effective_date": "2026-01-28",
        "updated_at": "2026-04-19",
        "url": "/reference-docs/ich-e3-clinical-study-report.pdf",
        "external_url": "https://www.ema.europa.eu/en/ich-e3-structure-content-clinical-study-reports-scientific-guideline",
        "taxonomy": ["IMCP", "CSR", "endpoint", "population", "immune response"],
        "claims": ["Durability statements must match observed follow-up window", "Population language must match study inclusion criteria"],
        "summary": "CSR-style evidence synopsis structured to ICH E3 headings for endpoint, population, duration, statistical method, and limitations.",
        "preview": "Feeds claim-to-evidence alignment and comparative/statistical validity checks.",
        "evidence_strength": 91,
        "stage_ids": ["content-created", "medical-review"],
    },
    {
        "id": "DOC-DERM-SOC-042",
        "title": "Dermexa Social and Digital Promotional Guardrails",
        "source_id": "regulatory-repo",
        "source_name": "Regulatory Document Repository",
        "brand": "Dermexa",
        "document_type": "Digital / Social Policy",
        "region": "EU",
        "market": "UK",
        "channel": "Organic social where permitted",
        "approval_status": "approved",
        "version": "v2.0",
        "effective_date": "2026-04-10",
        "updated_at": "2026-05-01",
        "url": "/reference-docs/abpi-code-of-practice.pdf",
        "external_url": "https://www.abpi.org.uk/publications/code-of-practice-for-the-pharmaceutical-industry-2024/",
        "taxonomy": ["IMCP", "ABPI", "social", "digital promotion", "employee interaction"],
        "claims": ["Social assets may require local interaction caveats", "Comments and engagement must be governed by market rules"],
        "summary": "UK digital/social guardrails for promotional asset handling, employee interaction risk, and approval record requirements.",
        "preview": "Used by compliance approval and QA checks for digital/social content.",
        "evidence_strength": 89,
        "stage_ids": ["compliance-approval", "qa", "publish"],
    },
    {
        "id": "DOC-NEURO-WEB-088",
        "title": "Neurovance Webinar Channel Template and Speaker Disclosure Pack",
        "source_id": "approved-content",
        "source_name": "Approved Content Library",
        "brand": "Neurovance",
        "document_type": "Webinar invite",
        "region": "Global",
        "market": "Saudi Arabia",
        "channel": "Webinar / virtual event",
        "approval_status": "in_review",
        "version": "v1.5",
        "effective_date": "2026-04-21",
        "updated_at": "2026-05-03",
        "url": "/samples/respivara-email.html",
        "external_url": "",
        "taxonomy": ["IMCP", "webinar", "speaker disclosure", "registration", "follow-up"],
        "claims": ["Registration CTA must route through approved HCP portal", "Speaker disclosure must remain visible in invite and reminder"],
        "summary": "Webinar invite/reminder content package with disclosure, registration CTA, and follow-up channel rules.",
        "preview": "Supports brief planning, QA routing, CTA validation, and publish readiness.",
        "evidence_strength": 84,
        "stage_ids": ["briefing", "content-created", "qa", "publish"],
    },
    {
        "id": "DOC-RESP-FDA-FAIR-062",
        "title": "US Promotional Fair Balance and Risk Presentation Reference",
        "source_id": "regulatory-repo",
        "source_name": "Regulatory Document Repository",
        "brand": "Respivara",
        "document_type": "Regulatory Guidance",
        "region": "North America",
        "market": "US",
        "channel": "HCP portal",
        "approval_status": "approved",
        "version": "v2026.05",
        "effective_date": "2026-05-01",
        "updated_at": "2026-05-05",
        "url": "/reference-docs/fda-prescription-drug-advertising.pdf",
        "external_url": "https://www.fda.gov/drugs/prescription-drug-advertising/prescription-drug-advertising-questions-and-answers",
        "taxonomy": ["IMCP", "FDA OPDP", "fair balance", "risk presentation", "HCP web"],
        "claims": ["Product claim communications must not be false or misleading", "Benefit and risk presentation must remain balanced"],
        "summary": "US regulatory reference metadata for OPDP-style fair-balance, risk prominence, and misleading-claim checks.",
        "preview": "Supports Stage 3 fair-balance and Stage 4 legal/privacy checks.",
        "evidence_strength": 94,
        "stage_ids": ["medical-review", "compliance-approval", "qa"],
    },
    {
        "id": "DOC-IMM-QA-LIT-114",
        "title": "Immunava Litmus Pre-send QA Evidence Package",
        "source_id": "dam",
        "source_name": "Digital Asset Management",
        "brand": "Immunava",
        "document_type": "Email QA Report",
        "region": "North America",
        "market": "US",
        "channel": "Veeva Approved Email",
        "approval_status": "approved",
        "version": "v2.3",
        "effective_date": "2026-05-04",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-email.html",
        "external_url": "https://help.litmus.com/article/119-litmus-presend-testing-guide",
        "taxonomy": ["IMCP", "Litmus", "pre-send QA", "links", "spam", "accessibility"],
        "claims": ["Email package requires rendering, link, spam, and accessibility checks", "Unsubscribe and tracking requirements must pass"],
        "summary": "Pre-send QA evidence package for rendering previews, links, tracking, spam, accessibility, and image-load checks.",
        "preview": "Supports Stage 7 channel QA and Stage 8 publishing readiness.",
        "evidence_strength": 90,
        "stage_ids": ["qa", "publish"],
    },
])

LIBRARY_DOCUMENTS.extend([
    {
        "id": "DOC-PUB-RESP-PLAN-026",
        "title": "Respivara Publication and Evidence Use Plan",
        "source_id": "publication-library",
        "source_name": "Publication Library",
        "brand": "Respivara",
        "document_type": "Publication Plan",
        "region": "Global",
        "market": "India",
        "channel": "Omnichannel",
        "approval_status": "approved",
        "version": "v1.0",
        "effective_date": "2026-05-01",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-publication-plan.html",
        "external_url": "https://www.ema.europa.eu/en/ich-e3-structure-content-clinical-study-reports-scientific-guideline",
        "taxonomy": ["IMCP", "publication plan", "evidence intent", "reference family"],
        "claims": ["Publication evidence supports endpoint interpretation", "Limitations must remain visible in short-form use"],
        "summary": "Approved evidence-use plan linking campaign intent to CSR synopsis, claim families, publication timing, and MLR references.",
        "preview": "Brief and planning source used to freeze the downstream validation packet.",
        "evidence_strength": 92,
        "stage_ids": ["briefing", "medical-review"],
    },
    {
        "id": "DOC-CONTENT-RESP-042",
        "title": "Respivara Omnichannel Content Validation Pack",
        "source_id": "approved-content",
        "source_name": "Approved Content Library",
        "brand": "Respivara",
        "document_type": "HCP email + CLM detail aid",
        "region": "APAC",
        "market": "India",
        "channel": "Veeva Approved Email + Veeva CLM / eDetail",
        "approval_status": "approved",
        "version": "v1.0",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-content-pack.html",
        "external_url": "",
        "taxonomy": ["IMCP", "content asset", "email", "CLM", "claim module", "safety footer"],
        "claims": ["Approved copy module must match claim library", "Risk footer must remain adjacent to benefit claim"],
        "summary": "Generated content artifact used by Stage 2 onward for document-wise validation across email, CLM, and modular asset checks.",
        "preview": "Represents the already-created content package to validate instead of authoring new content.",
        "evidence_strength": 89,
        "stage_ids": ["content-created", "medical-review", "compliance-approval", "qa", "publish"],
    },
    {
        "id": "DOC-LAND-RESP-077",
        "title": "Respivara HCP Landing Page Validation Artifact",
        "source_id": "dam",
        "source_name": "Digital Asset Management",
        "brand": "Respivara",
        "document_type": "Landing page",
        "region": "APAC",
        "market": "India",
        "channel": "Web / landing page",
        "approval_status": "approved",
        "version": "v1.1",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-landing-page.html",
        "external_url": "",
        "taxonomy": ["IMCP", "landing page", "CTA", "PI link", "analytics"],
        "claims": ["CTA must route to approved HCP destination", "PI and safety links must resolve before publishing"],
        "summary": "HCP landing page artifact for CTA, QR, PI-link, channel policy, and post-publish monitoring validation.",
        "preview": "Loaded with the brief-linked source packet for QA and publishing checks.",
        "evidence_strength": 88,
        "stage_ids": ["content-created", "qa", "publish"],
    },
])

LIBRARY_DOCUMENTS.extend([
    {
        "id": "DOC-BRIEF-RESP-EMAIL-051",
        "title": "Respivara HCP Email Brief and Plan",
        "source_id": "veeva-crm",
        "source_name": "Veeva CRM",
        "brand": "Respivara",
        "document_type": "Campaign Brief",
        "region": "India",
        "market": "India",
        "channel": "Veeva CRM",
        "approval_status": "approved",
        "version": "v2.0",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-email-brief-plan.html",
        "external_url": "",
        "taxonomy": ["IMCP", "brief", "email", "audience", "Veeva CRM", "plan"],
        "claims": ["Email modules must use approved Respivara claim IDs", "PI and safety links must resolve before publish"],
        "summary": "Detailed email brief covering objective, subject/preheader, hero, claim block, safety footer, CTA, tracking, consent, and Veeva CRM metadata.",
        "preview": "Primary brief and plan for Respivara HCP Approved Email generation and validation.",
        "evidence_strength": 94,
        "stage_ids": ["briefing", "content-created", "medical-review", "compliance-approval", "qa", "publish"],
    },
    {
        "id": "DOC-BRIEF-RESP-CLM-052",
        "title": "Respivara CLM / eDetail Aid Brief and Plan",
        "source_id": "veeva-crm",
        "source_name": "Veeva CRM",
        "brand": "Respivara",
        "document_type": "CLM / eDetail Aid",
        "region": "India",
        "market": "India",
        "channel": "Veeva CRM",
        "approval_status": "approved",
        "version": "v2.0",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-clm-brief-plan.html",
        "external_url": "",
        "taxonomy": ["IMCP", "brief", "CLM", "edetail", "screen plan", "rep call"],
        "claims": ["CLM screens must preserve approved claim wording", "Reference drawer and safety screen are mandatory"],
        "summary": "Detailed CLM / eDetail brief with screen-by-screen rep conversation purpose, validation controls, and Veeva CRM package requirements.",
        "preview": "Primary brief and plan for Respivara CLM / eDetail Aid generation and validation.",
        "evidence_strength": 94,
        "stage_ids": ["briefing", "content-created", "medical-review", "compliance-approval", "localization", "local-approval", "qa", "publish"],
    },
    {
        "id": "DOC-SUPPORT-RESP-VAL-053",
        "title": "Respivara Supporting Documents and Validation Alignment Pack",
        "source_id": "approved-content",
        "source_name": "Approved Content Library",
        "brand": "Respivara",
        "document_type": "Validation Support Pack",
        "region": "India",
        "market": "India",
        "channel": "Vault",
        "approval_status": "approved",
        "version": "v1.0",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-supporting-validation-pack.html",
        "external_url": "",
        "taxonomy": ["IMCP", "supporting documents", "validation", "claim matrix", "safety", "PI", "evidence"],
        "claims": ["Brief, content, and validation sources must travel as one bundle", "Right validation pack depends on selected content type"],
        "summary": "Bundled supporting source set for claim, label, safety, evidence, Veeva CRM audience, tracking, QA, and publish-readiness checks.",
        "preview": "Automatically bundled with the selected brief and content type to align validation documents across all stages.",
        "evidence_strength": 96,
        "stage_ids": ["briefing", "content-created", "medical-review", "compliance-approval", "localization", "local-approval", "qa", "publish"],
    },
    {
        "id": "DOC-EMAIL-COPY-RESP-061",
        "title": "Respivara HCP Approved Email Copy Deck",
        "source_id": "approved-content",
        "source_name": "Approved Content Library",
        "brand": "Respivara",
        "document_type": "Email",
        "region": "India",
        "market": "India",
        "channel": "Veeva CRM",
        "approval_status": "approved",
        "version": "v2.2",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-content-pack.html",
        "external_url": "",
        "taxonomy": ["IMCP", "email", "copy deck", "approved module", "subject line", "safety footer"],
        "claims": [
            "Subject line must not contain standalone product efficacy claims",
            "Approved claim module must retain claim ID, reference ID, safety adjacency, and PI CTA",
            "Unsubscribe, privacy, and consent status must remain visible and technically functional",
        ],
        "summary": "Full HCP email copy deck with approved subject/preheader options, hero module, claim block, reference drawer, safety footer, PI CTA, unsubscribe language, consent rules, suppression logic, and Veeva CRM field mapping.",
        "preview": "Used as the Stage 2 generated content record and as the source for medical, compliance, Litmus QA, and publish validation. Includes copy variants, module order, risk-control notes, and metadata needed to build the Veeva Approved Email package.",
        "evidence_strength": 95,
        "stage_ids": ["content-created", "medical-review", "compliance-approval", "qa", "publish"],
    },
    {
        "id": "DOC-EMAIL-QA-RESP-062",
        "title": "Respivara Litmus QA, Link, Tracking, and Accessibility Report",
        "source_id": "dam",
        "source_name": "Digital Asset Management",
        "brand": "Respivara",
        "document_type": "Email QA Report",
        "region": "India",
        "market": "India",
        "channel": "Litmus",
        "approval_status": "approved",
        "version": "v1.4",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-email.html",
        "external_url": "https://help.litmus.com/article/119-litmus-presend-testing-guide",
        "taxonomy": ["IMCP", "Litmus", "QA", "rendering", "links", "tracking", "accessibility"],
        "claims": [
            "PI, safety, privacy, unsubscribe, and CTA links must resolve in all tested email clients",
            "Tracking tags must match the approved Respivara CRM taxonomy",
            "Email rendering cannot hide safety content or reference links",
        ],
        "summary": "Pre-send quality pack covering Litmus client rendering, broken links, PI/CTA routing, UTM and Veeva tracking, image alt text, mobile layout, spam indicators, and accessibility checks.",
        "preview": "Automatically aligned for Email validation in Stage 7 and publish-readiness checks in Stage 8, while remaining visible from Stage 2 onward as the expected downstream QA evidence.",
        "evidence_strength": 93,
        "stage_ids": ["content-created", "qa", "publish"],
    },
    {
        "id": "DOC-CLM-STORY-RESP-063",
        "title": "Respivara CLM / eDetail Aid Screen Storyboard and Talk Track",
        "source_id": "approved-content",
        "source_name": "Approved Content Library",
        "brand": "Respivara",
        "document_type": "CLM / eDetail Aid",
        "region": "India",
        "market": "India",
        "channel": "Veeva CRM",
        "approval_status": "approved",
        "version": "v2.1",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-content-pack.html",
        "external_url": "",
        "taxonomy": ["IMCP", "CLM", "eDetail", "storyboard", "rep talk track", "reference drawer"],
        "claims": [
            "Each claim-bearing screen must expose a reference drawer and claim ID",
            "Rep talk track must remain medically factual and cannot introduce free-text claims",
            "Final safety screen is mandatory before CRM call completion",
        ],
        "summary": "Screen-level CLM storyboard with patient identification setup, evidence-supported claim screen, safety/next-step screen, reference drawer behavior, representative talk track, CRM interaction capture, and MLR handoff metadata.",
        "preview": "Primary Stage 2 real-content artifact for CLM/eDetail validation. Medical review uses it for screen-by-screen claim fidelity; compliance uses it for mandated safety placement and representative-use controls.",
        "evidence_strength": 95,
        "stage_ids": ["content-created", "medical-review", "compliance-approval", "localization", "qa", "publish"],
    },
    {
        "id": "DOC-CLM-REF-RESP-064",
        "title": "Respivara CLM Reference Drawer and Evidence Mapping Appendix",
        "source_id": "veeva-vault",
        "source_name": "Veeva Vault",
        "brand": "Respivara",
        "document_type": "CLM / eDetail Aid",
        "region": "India",
        "market": "India",
        "channel": "Vault",
        "approval_status": "approved",
        "version": "v1.7",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-claim-matrix.html",
        "external_url": "",
        "taxonomy": ["IMCP", "CLM", "reference drawer", "claim evidence", "medical review"],
        "claims": [
            "Claim CLM-184 maps to the approved claim library and supporting CSR endpoint",
            "Reference drawer must include source ID, endpoint qualifier, limitation note, and expiry",
            "No screen may cite evidence that is not present in the approved appendix",
        ],
        "summary": "Detailed reference appendix for CLM/eDetail screens, mapping every claim, visual support point, safety note, limitation statement, and representative prompt to approved source documents and expiry metadata.",
        "preview": "Aligned automatically for Stage 2 and Stage 3 so reviewers can inspect evidence lineage beside the generated CLM storyboard instead of searching separate systems.",
        "evidence_strength": 97,
        "stage_ids": ["content-created", "medical-review", "compliance-approval", "qa"],
    },
    {
        "id": "DOC-CRM-META-RESP-065",
        "title": "Respivara Veeva CRM Campaign Metadata and Audience Control Pack",
        "source_id": "veeva-crm",
        "source_name": "Veeva CRM",
        "brand": "Respivara",
        "document_type": "Campaign Brief",
        "region": "India",
        "market": "India",
        "channel": "Veeva CRM",
        "approval_status": "approved",
        "version": "v1.6",
        "effective_date": "2026-05-05",
        "updated_at": "2026-05-05",
        "url": "/samples/respivara-supporting-validation-pack.html",
        "external_url": "",
        "taxonomy": ["IMCP", "Veeva CRM", "audience", "suppression", "campaign metadata", "publish readiness"],
        "claims": [
            "Audience must be HCP-only, consented, India-market eligible, and suppression checked",
            "Campaign, asset, UTM, and owner metadata must match the brief before activation",
            "Rollback owner and incident escalation path must be captured before publish",
        ],
        "summary": "Operational control pack containing audience inclusion/exclusion logic, consent status, suppression timestamp, Veeva field mapping, campaign taxonomy, owner matrix, publish window, and rollback plan.",
        "preview": "Bundled with Campaign Brief, Email, and CLM content so Stage 2 output, Stage 7 QA, and Stage 8 publish checks can validate operational readiness from the same source set.",
        "evidence_strength": 94,
        "stage_ids": ["briefing", "content-created", "qa", "publish"],
    },
    {
        "id": "DOC-BRIEF-RESP-LB-071",
        "title": "Respivara HCP Leave Behind Brief and Plan",
        "source_id": "veeva-crm",
        "source_name": "Veeva CRM",
        "brand": "Respivara",
        "document_type": "HCP Leave Behind",
        "region": "India",
        "market": "India",
        "channel": "Veeva CRM",
        "approval_status": "approved",
        "version": "v1.0",
        "effective_date": "2026-05-06",
        "updated_at": "2026-05-06",
        "url": "/samples/respivara-leavebehind-brief-plan.html",
        "external_url": "",
        "taxonomy": ["IMCP", "brief", "leave behind", "print", "HCP handout", "plan"],
        "claims": [
            "Leave-behind copy must be usable after a representative call without creating standalone unsupported claims",
            "Safety, PI QR, local disclaimer, and MLR footer must remain visible in the printed format",
            "The piece must support HCP recall of patient-selection criteria, not direct patient promotion",
        ],
        "summary": "Detailed brief and execution plan for a two-page Respivara HCP leave-behind covering audience, visit context, message hierarchy, page structure, claim controls, safety placement, print production, distribution, and success metrics.",
        "preview": "Primary planning record for the new HCP Leave Behind content type, with clear values for owners, source packet, page-by-page content intent, required validation documents, and gate-level acceptance criteria.",
        "evidence_strength": 95,
        "stage_ids": ["briefing", "content-created", "medical-review", "compliance-approval", "localization", "local-approval", "qa", "publish"],
    },
    {
        "id": "DOC-CONTENT-RESP-LB-072",
        "title": "Respivara HCP Leave Behind Content Master",
        "source_id": "approved-content",
        "source_name": "Approved Content Library",
        "brand": "Respivara",
        "document_type": "HCP Leave Behind",
        "region": "India",
        "market": "India",
        "channel": "Vault",
        "approval_status": "approved",
        "version": "v1.0",
        "effective_date": "2026-05-06",
        "updated_at": "2026-05-06",
        "url": "/samples/respivara-leavebehind-content.html",
        "external_url": "",
        "taxonomy": ["IMCP", "leave behind", "content master", "print", "claim module", "safety block"],
        "claims": [
            "Page 1 claim module must use approved patient-selection wording and visible reference ID",
            "Page 2 must include safety, PI QR/link, local disclaimer, and adverse event reporting cue",
            "Representative-use note must prevent patient-facing distribution",
        ],
        "summary": "Created HCP leave-behind content master with page-by-page copy, visual hierarchy, claim IDs, evidence sidebar, safety panel, PI QR placement, representative-use note, print specifications, and MLR footer requirements.",
        "preview": "Stage 2 content artifact for HCP Leave Behind validation. It is distinct from validation documents and is reviewed as the actual generated material that would be routed through MLR.",
        "evidence_strength": 94,
        "stage_ids": ["content-created", "medical-review", "compliance-approval", "localization", "local-approval", "qa", "publish"],
    },
    {
        "id": "DOC-VAL-RESP-LB-073",
        "title": "Respivara HCP Leave Behind Validation Matrix and Test Cases",
        "source_id": "veeva-vault",
        "source_name": "Veeva Vault",
        "brand": "Respivara",
        "document_type": "Validation Support Pack",
        "region": "India",
        "market": "India",
        "channel": "Vault",
        "approval_status": "approved",
        "version": "v1.0",
        "effective_date": "2026-05-06",
        "updated_at": "2026-05-06",
        "url": "/samples/respivara-leavebehind-validation.html",
        "external_url": "",
        "taxonomy": ["IMCP", "validation", "test cases", "KPI", "leave behind", "print QA"],
        "claims": [
            "Validation must cover claim fidelity, evidence lineage, safety prominence, local disclaimer, print production, and distribution controls",
            "Each test case must include KPI target, pass threshold, missing-area logic, and accountable owner",
            "Validation documents cannot be treated as content assets",
        ],
        "summary": "Dedicated validation matrix for the leave-behind with detailed KPIs, test cases, thresholds, missing-area checks, improvement actions, evidence requirements, and stage ownership across the validation flow.",
        "preview": "Clear validation source document separate from the leave-behind content master. Used by Stage 2 through Stage 8 to test content correctness, medical support, compliance, localization, QA, and publish readiness.",
        "evidence_strength": 98,
        "stage_ids": ["briefing", "content-created", "medical-review", "compliance-approval", "localization", "local-approval", "qa", "publish"],
    },
    {
        "id": "DOC-QA-RESP-LB-074",
        "title": "Respivara Leave Behind Print QA and Distribution Readiness Pack",
        "source_id": "dam",
        "source_name": "Digital Asset Management",
        "brand": "Respivara",
        "document_type": "Print QA Report",
        "region": "India",
        "market": "India",
        "channel": "Litmus",
        "approval_status": "approved",
        "version": "v1.0",
        "effective_date": "2026-05-06",
        "updated_at": "2026-05-06",
        "url": "/samples/respivara-leavebehind-validation.html",
        "external_url": "",
        "taxonomy": ["IMCP", "print QA", "QR", "accessibility", "distribution", "PDF proof"],
        "claims": [
            "PDF proof must preserve safety readability, QR scan accuracy, bleed, trim, and MLR footer",
            "Distribution must be restricted to approved HCP representative calls",
            "Final production file must match the approved Vault version",
        ],
        "summary": "Print and distribution QA pack for HCP leave-behind assets covering PDF proof, QR scans, print specs, accessibility, version lock, representative distribution rules, and post-distribution audit capture.",
        "preview": "Loaded for QA and publish stages as the production-readiness evidence for the HCP Leave Behind content type.",
        "evidence_strength": 93,
        "stage_ids": ["qa", "publish"],
    },
    {
        "id": "DOC-LOCAL-RESP-LB-075",
        "title": "Respivara India Leave Behind Local Approval and Disclaimer Pack",
        "source_id": "localization-library",
        "source_name": "Localization Library",
        "brand": "Respivara",
        "document_type": "Local Disclaimer",
        "region": "India",
        "market": "India",
        "channel": "Vault",
        "approval_status": "approved",
        "version": "v1.0",
        "effective_date": "2026-05-06",
        "updated_at": "2026-05-06",
        "url": "/samples/respivara-leavebehind-validation.html",
        "external_url": "",
        "taxonomy": ["IMCP", "India", "local approval", "disclaimer", "leave behind", "affiliate review"],
        "claims": [
            "India local disclaimer must appear on the final printed piece",
            "Affiliate reviewer sign-off must be captured before print production",
            "Local PI QR and adverse event reporting cue must route to approved destinations",
        ],
        "summary": "India-specific local approval pack for HCP leave-behind pieces, including local disclaimer language, affiliate reviewer checklist, local PI QR control, adverse event reporting cue, and country approval evidence.",
        "preview": "Used in local adaptation and local approval stages to keep the printed HCP leave-behind aligned with India requirements.",
        "evidence_strength": 94,
        "stage_ids": ["localization", "local-approval", "qa", "publish"],
    },
])

def normalize_fixed_workflow_metadata() -> None:
    replacements = {
        "Cardiava": FIXED_BRAND,
        "Immunava": FIXED_BRAND,
        "Dermexa": FIXED_BRAND,
        "Neurovance": FIXED_BRAND,
        "Saudi Arabia": FIXED_MARKET,
        "Global": FIXED_MARKET,
        "US": FIXED_MARKET,
        "UK": FIXED_MARKET,
        "EU": FIXED_MARKET,
        "Veeva Approved Email + Veeva CLM / eDetail": FIXED_CHANNEL,
        "Veeva Approved Email": FIXED_CHANNEL,
        "Omnichannel": FIXED_CHANNEL,
        "All promotional channels": FIXED_CHANNEL,
        "Medical review": FIXED_CHANNEL,
        "Print leave-behind": FIXED_CHANNEL,
        "Litmus email QA": FIXED_CHANNEL,
        "Web / landing page": FIXED_CHANNEL,
        "Congress / booth": FIXED_CHANNEL,
        "Webinar / virtual event": FIXED_CHANNEL,
        "Organic social where permitted": FIXED_CHANNEL,
        "HCP portal": FIXED_CHANNEL,
    }

    def clean(value: Any) -> Any:
        if isinstance(value, str):
            for old, new in replacements.items():
                value = value.replace(old, new)
            return value
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        return value

    for document in LIBRARY_DOCUMENTS:
        document.update(clean(document))
        document["brand"] = FIXED_BRAND
        document["market"] = FIXED_MARKET
        document["region"] = FIXED_MARKET
        source_text = f"{document.get('source_name', '')} {document.get('source_id', '')} {document.get('title', '')} {document.get('document_type', '')}".lower()
        document["channel"] = "Litmus" if "litmus" in source_text or "qa" in source_text else "Vault" if "vault" in source_text else FIXED_CHANNEL
    for media in SAMPLE_MEDIA_FILES:
        media.update(clean(media))
        media["source_system"] = FIXED_CHANNEL
    for event in AUDIT_EVENTS:
        event.update(clean(event))
        event["source_system"] = FIXED_CHANNEL
        event["asset_id"] = event.get("asset_id", "").replace("AST-CARD", "AST-RESP").replace("AST-IMM", "AST-RESP")

normalize_fixed_workflow_metadata()

ALLOWED_SAMPLE_MEDIA_IDS = {
    "dam-brief",
    "dam-claim-matrix",
    "media-email-html",
    "media-email-copydeck",
    "media-clm-storyboard",
    "media-veeva-metadata-pack",
    "media-leavebehind-pdf",
    "media-leavebehind-printer-pack",
    "media-hero-image",
    "media-local-pdf",
    "dam-publish-pack",
    "dam-respivara-patient-brochure",
}

INPUT_BUNDLES: Dict[str, Dict[str, Any]] = {}
STAGE_OUTPUT_DOCUMENTS: Dict[str, Dict[str, Any]] = {}
WORKFLOW_ACTIONS: List[Dict[str, Any]] = []
APPROVAL_GATES: List[Dict[str, Any]] = []
ALERTS: List[Dict[str, Any]] = [
    {"id": "ALT-001", "stage_id": "medical-review", "severity": "high", "title": "Fair balance below target", "message": "Risk section requires expansion before compliance approval.", "owner": "Medical reviewer", "timestamp": "2026-05-04 10:18 IST", "status": "open"},
    {"id": "ALT-002", "stage_id": "qa", "severity": "high", "title": "Prescribing information link failed", "message": "CTA validation returned a 404 for one PI destination.", "owner": "QA specialist", "timestamp": "2026-05-04 10:24 IST", "status": "open"},
]

RULE_ENGINE_RUNS: Dict[str, Dict[str, Any]] = {}
APPROVAL_TRACKER: List[Dict[str, Any]] = []
NOTIFICATIONS: List[Dict[str, Any]] = []

RULE_ENGINE_STAGES: Dict[str, Dict[str, Any]] = {
    "briefing": {
        "threshold": 88,
        "purpose": "Use AI planning intelligence to confirm the brief is complete, grounded, and ready for content creation.",
        "steps": [
            {"id": "brief-intake", "name": "Brief completeness intelligence", "category": "Planning", "weight": 22, "mandatory": True, "critical": True, "static_score": 86, "source_refs": ["Campaign Brief", "Veeva CRM intake"], "kpis": {"Brief completeness": 86, "Missing fields": 2}, "static_rules": ["objective present", "audience defined", "timeline captured"], "prompt": "Assess brief completeness and missing planning fields."},
            {"id": "audience-fit", "name": "Audience and channel fit", "category": "Segmentation", "weight": 18, "mandatory": True, "critical": False, "static_score": 91, "source_refs": ["Audience plan", "CRM segment"], "kpis": {"Audience fit": 91, "Channel fit": 89}, "static_rules": ["audience matches objective", "channel aligns to use case"], "prompt": "Evaluate whether audience and channel choices fit the business objective."},
            {"id": "claim-intent", "name": "Claim intent pre-screen", "category": "Claims", "weight": 20, "mandatory": True, "critical": True, "static_score": 79, "source_refs": ["Claim Matrix", "Approved Claim Library"], "kpis": {"Claim intent readiness": 79, "Unmapped claim intents": 1}, "static_rules": ["claim intent mapped", "evidence owner identified"], "prompt": "Identify claim intent gaps before content drafting."},
            {"id": "source-readiness", "name": "Source and DAM readiness", "category": "DAM", "weight": 20, "mandatory": True, "critical": False, "static_score": 88, "source_refs": ["Veeva Vault", "Agency DAM", "Reference Pack"], "kpis": {"DAM readiness": 88, "Source availability": 90}, "static_rules": ["source packet linked", "asset shell available"], "prompt": "Check whether the DAM and source package are ready for drafting."},
            {"id": "handoff-plan", "name": "Workflow handoff plan", "category": "Operations", "weight": 20, "mandatory": True, "critical": False, "static_score": 90, "source_refs": ["Approval Matrix", "Project Plan"], "kpis": {"SLA readiness": 90, "Owner coverage": 94}, "static_rules": ["owners assigned", "review route selected", "SLA risk assessed"], "prompt": "Evaluate owner, SLA, and handoff readiness."},
        ],
    },
    "content-created": {
        "threshold": 88,
        "purpose": "Use AI content intelligence to improve draft quality, evidence readiness, brand consistency, and DAM metadata before MLR review.",
        "steps": [
            {"id": "content-structure", "name": "Content structure and readability", "category": "Content", "weight": 18, "mandatory": True, "critical": False, "static_score": 89, "source_refs": ["Draft Content", "Brand Guidelines"], "kpis": {"Readability": 89, "Structure score": 91}, "static_rules": ["headline present", "CTA clear", "content blocks structured"], "prompt": "Assess content structure, readability, and message hierarchy."},
            {"id": "claim-draft-fit", "name": "Draft claim fit", "category": "Claims", "weight": 22, "mandatory": True, "critical": True, "static_score": 78, "source_refs": ["Claim Matrix", "Approved Claim Library"], "kpis": {"Claim draft fit": 78, "Rewrite candidates": 2}, "static_rules": ["draft claims mapped", "claim strength appropriate"], "prompt": "Detect draft claims that need rewrite before medical review."},
            {"id": "brand-tone", "name": "Brand tone and modular reuse", "category": "Brand", "weight": 16, "mandatory": True, "critical": False, "static_score": 92, "source_refs": ["Brand Guidelines", "Approved Content Library"], "kpis": {"Brand consistency": 92, "Reuse potential": 68}, "static_rules": ["tone matches brand", "approved modules reused"], "prompt": "Score brand consistency and reuse potential."},
            {"id": "dam-metadata", "name": "DAM metadata and asset lineage", "category": "DAM", "weight": 22, "mandatory": True, "critical": True, "static_score": 87, "source_refs": ["DAM Metadata", "Veeva Vault", "Agency DAM"], "kpis": {"Metadata completeness": 87, "Lineage readiness": 91}, "static_rules": ["asset ID present", "usage rights attached", "claim IDs tagged"], "prompt": "Validate DAM metadata and content lineage readiness.", "media_required": True},
            {"id": "sensitive-data", "name": "Sensitive data and asset safety", "category": "Security", "weight": 22, "mandatory": True, "critical": True, "static_score": 98, "source_refs": ["Security Scan", "Attachment Inventory"], "kpis": {"PHI/PII findings": 0, "Attachment integrity": 98}, "static_rules": ["no PHI", "attachments scanned", "asset integrity checked"], "prompt": "Check for sensitive data, unsafe attachments, and asset integrity.", "media_required": True},
        ],
    },
    "medical-review": {
        "threshold": 90,
        "purpose": "Validate that every claim is scientifically supportable, label-aligned, and review-ready before compliance approval.",
        "steps": [
            {"id": "claim-registry", "name": "Claim extraction and registry", "category": "Claims", "weight": 14, "mandatory": True, "critical": True, "static_score": 96, "source_refs": ["Draft Content v0.x", "Claim Matrix"], "kpis": {"Claim extraction coverage": 98, "Unmapped claim rate": 2}, "static_rules": ["claim sentence detected", "claim type identified", "claim ID created"], "prompt": "Extract claims, classify claim type, and identify unmapped claim risk."},
            {"id": "reference-provenance", "name": "Reference presence and provenance", "category": "Evidence", "weight": 14, "mandatory": True, "critical": True, "static_score": 93, "source_refs": ["Approved Reference Library", "Clinical Study Repository"], "kpis": {"Reference coverage": 93, "Source authenticity": 96}, "static_rules": ["approved reference exists", "source type identified", "document ID valid"], "prompt": "Check every claim for approved reference coverage and provenance."},
            {"id": "evidence-alignment", "name": "Claim-to-evidence alignment", "category": "Evidence", "weight": 16, "mandatory": True, "critical": True, "static_score": 91, "source_refs": ["Reference Pack", "Clinical Study Reports"], "kpis": {"Evidence match": 91, "Semantic alignment": 89}, "static_rules": ["numeric claim matches evidence", "population matches study", "timeframe matches source"], "prompt": "Compare claims to evidence and identify overstatement or semantic drift."},
            {"id": "label-alignment", "name": "SmPC / label alignment", "category": "Regulatory", "weight": 16, "mandatory": True, "critical": True, "static_score": 94, "source_refs": ["SmPC / PI / Package Insert"], "kpis": {"Label alignment": 94, "Off-label risk": 0}, "static_rules": ["indication approved", "dosage matches label", "no off-label promotion"], "prompt": "Validate claims against SmPC and prescribing information."},
            {"id": "fair-balance", "name": "Fair balance and safety disclosure", "category": "Safety", "weight": 16, "mandatory": True, "critical": True, "static_score": 79, "source_refs": ["Safety Statement Library", "Medical Review Checklist"], "kpis": {"Fair balance index": 79, "Safety disclosure completeness": 86}, "static_rules": ["risk statement present", "warnings visible", "limitations included"], "prompt": "Assess benefit-risk balance and safety prominence."},
            {"id": "comparative-validity", "name": "Comparative and statistical validity", "category": "Claims", "weight": 12, "mandatory": True, "critical": False, "static_score": 90, "source_refs": ["Clinical Study Reports", "Claim Matrix"], "kpis": {"Comparative validity": 90, "Statistical support": 92}, "static_rules": ["head-to-head evidence present when needed", "statistical significance checked"], "prompt": "Check comparative and quantitative claims for statistical support."},
            {"id": "mlr-pack", "name": "MLR review pack completeness", "category": "Audit", "weight": 12, "mandatory": True, "critical": False, "static_score": 92, "source_refs": ["MLR Redline Log", "Version History"], "kpis": {"Reviewer-ready score": 92, "Pack completeness": 94}, "static_rules": ["version frozen", "source pack complete", "approval path determined"], "prompt": "Evaluate review pack completeness and readiness for MLR."},
        ],
    },
    "compliance-approval": {
        "threshold": 95,
        "purpose": "Confirm the asset is compliant with global policy, SOP, privacy, and approval authority before localization.",
        "steps": [
            {"id": "sop-policy", "name": "SOP and policy mapping", "category": "Policy", "weight": 22, "mandatory": True, "critical": True, "static_score": 97, "source_refs": ["Global SOP Library", "Global Compliance Policy Library"], "kpis": {"Policy adherence": 97, "SOP coverage": 98}, "static_rules": ["policy version current", "rule set matches content type"], "prompt": "Map content to active SOP and policy requirements."},
            {"id": "legal-privacy", "name": "Legal, privacy and disclosure", "category": "Legal", "weight": 22, "mandatory": True, "critical": True, "static_score": 79, "source_refs": ["Legal Disclaimer Library", "Privacy Policy Pack"], "kpis": {"Disclosure completeness": 79, "Privacy compliance": 97}, "static_rules": ["disclaimer present", "privacy requirements met", "no prohibited phrasing"], "prompt": "Check legal disclaimer, privacy, and disclosure completeness."},
            {"id": "risk-escalation", "name": "Risk classification and escalation", "category": "Risk", "weight": 18, "mandatory": True, "critical": True, "static_score": 95, "source_refs": ["Risk Classification Template", "Exception Register"], "kpis": {"Routing accuracy": 95, "Unresolved blockers": 0}, "static_rules": ["risk assigned", "high-risk routed", "exceptions documented"], "prompt": "Classify risk and determine escalation path."},
            {"id": "authority", "name": "Approval authority validation", "category": "Approval", "weight": 20, "mandatory": True, "critical": True, "static_score": 97, "source_refs": ["Approval Matrix", "Delegation of Authority"], "kpis": {"Authority match": 97, "Sign-off validity": 98}, "static_rules": ["reviewer authority valid", "delegation current"], "prompt": "Validate approval authority and delegation."},
            {"id": "audit-record", "name": "Audit trail and approval record", "category": "Audit", "weight": 18, "mandatory": True, "critical": True, "static_score": 96, "source_refs": ["Approval Log", "Version History"], "kpis": {"Audit completeness": 96, "Log capture": 98}, "static_rules": ["comments captured", "timestamp logged", "audit ID created"], "prompt": "Confirm approval record integrity and audit readiness."},
        ],
    },
    "localization": {
        "threshold": 90,
        "purpose": "Preserve medical meaning while adapting language, disclaimer, format, and cultural context for local use.",
        "steps": [
            {"id": "source-freeze", "name": "Source content freeze", "category": "Version", "weight": 14, "mandatory": True, "critical": True, "static_score": 96, "source_refs": ["Approved Global Asset", "Version History"], "kpis": {"Source freeze compliance": 96, "Version drift": 0}, "static_rules": ["approved version only", "source locked"], "prompt": "Check localization uses only the approved locked source."},
            {"id": "translation-fidelity", "name": "Translation fidelity", "category": "Translation", "weight": 18, "mandatory": True, "critical": True, "static_score": 91, "source_refs": ["Translation Memory", "Local Medical Glossary"], "kpis": {"Translation accuracy": 91, "Semantic drift": 7}, "static_rules": ["medical terminology preserved", "numeric values preserved"], "prompt": "Check translation fidelity and semantic drift."},
            {"id": "claim-preservation", "name": "Local claim preservation", "category": "Claims", "weight": 18, "mandatory": True, "critical": True, "static_score": 92, "source_refs": ["Approved Global Asset", "Claim Matrix"], "kpis": {"Claim preservation": 92, "Claim mutation": 0}, "static_rules": ["no new claim introduced", "claim meaning unchanged"], "prompt": "Detect whether localization changes claim strength or meaning."},
            {"id": "local-reg-fit", "name": "Local regulatory fit", "category": "Regulatory", "weight": 20, "mandatory": True, "critical": True, "static_score": 79, "source_refs": ["Country Regulatory Matrix", "Local Label / PI"], "kpis": {"Local regulatory fit": 79, "Missing local requirements": 1}, "static_rules": ["local warning included", "market restrictions respected"], "prompt": "Evaluate country-specific regulatory fit and missing requirements."},
            {"id": "local-disclaimer", "name": "Local disclaimer and legend", "category": "Disclosure", "weight": 16, "mandatory": True, "critical": True, "static_score": 91, "source_refs": ["Local Disclaimer Pack"], "kpis": {"Local disclosure completeness": 91, "Mandatory text coverage": 93}, "static_rules": ["local disclaimer present", "footnotes included"], "prompt": "Check mandatory local disclaimers, legends, and footnotes."},
            {"id": "cultural-format", "name": "Cultural and format adaptation", "category": "Market", "weight": 14, "mandatory": True, "critical": False, "static_score": 89, "source_refs": ["Local Style Guide", "Local Channel Format Specs"], "kpis": {"Cultural fit": 89, "Formatting compliance": 92}, "static_rules": ["imagery acceptable", "format fits channel"], "prompt": "Review cultural appropriateness and local channel formatting.", "media_required": True},
        ],
    },
    "local-approval": {
        "threshold": 95,
        "purpose": "Confirm localized content is acceptable for the specific country and lock country sign-off evidence.",
        "steps": [
            {"id": "country-pack", "name": "Country regulatory pack retrieval", "category": "Regulatory", "weight": 20, "mandatory": True, "critical": True, "static_score": 95, "source_refs": ["Country Regulatory Rules Library", "Local Label / PI"], "kpis": {"Country pack match": 95, "Local rule coverage": 94}, "static_rules": ["correct country rules loaded", "local label version correct"], "prompt": "Confirm correct market rule pack and local label version."},
            {"id": "local-mlr", "name": "Local MLR review", "category": "MLR", "weight": 22, "mandatory": True, "critical": True, "static_score": 79, "source_refs": ["Local MLR Checklist", "Local Review Comments"], "kpis": {"Local MLR pass rate": 79, "Redline closure": 82}, "static_rules": ["medical/legal/regulatory reviews captured", "redlines logged"], "prompt": "Assess local MLR readiness and open redline risk."},
            {"id": "local-label-disclaimer", "name": "Local label and disclaimer alignment", "category": "Disclosure", "weight": 22, "mandatory": True, "critical": True, "static_score": 92, "source_refs": ["Local Label / PI", "Local Disclaimer Pack"], "kpis": {"Local label alignment": 92, "Safety coverage": 91}, "static_rules": ["local warnings included", "references visible"], "prompt": "Check local label, safety wording, and required references."},
            {"id": "local-authority", "name": "Local approver authority", "category": "Approval", "weight": 18, "mandatory": True, "critical": True, "static_score": 96, "source_refs": ["Local Approval Matrix"], "kpis": {"Authority match": 96, "Approval validity": 97}, "static_rules": ["country authority valid", "market sign-off complete"], "prompt": "Validate local approval authority."},
            {"id": "local-audit-lock", "name": "Local audit lock and version freeze", "category": "Audit", "weight": 18, "mandatory": True, "critical": True, "static_score": 95, "source_refs": ["Local Approval Log", "Country Version History"], "kpis": {"Local audit completeness": 95, "Version lock": 96}, "static_rules": ["local version frozen", "approval ID generated"], "prompt": "Confirm local approval audit lock and version freeze."},
        ],
    },
    "qa": {
        "threshold": 92,
        "purpose": "Prepare final channel package and verify rendering, links, tracking, consent, segmentation, variants, and publish readiness.",
        "steps": [
            {"id": "asset-assembly", "name": "Channel asset assembly", "category": "Build", "weight": 12, "mandatory": True, "critical": True, "static_score": 95, "source_refs": ["Final Approved Asset", "Email HTML / creative package"], "kpis": {"Asset build completeness": 95, "Format compliance": 96}, "static_rules": ["approved copy inserted", "correct export format"], "prompt": "Check approved channel asset assembly.", "media_required": True},
            {"id": "rendering-qa", "name": "Rendering QA", "category": "Litmus", "weight": 14, "mandatory": True, "critical": True, "static_score": 96, "source_refs": ["Litmus QA report"], "kpis": {"Litmus render pass": 96, "Client compatibility": 94}, "static_rules": ["email renders correctly", "no broken layout"], "prompt": "Evaluate rendering report and visual layout.", "media_required": True},
            {"id": "link-cta-qr", "name": "Link / CTA / QR validation", "category": "QA", "weight": 16, "mandatory": True, "critical": True, "static_score": 72, "source_refs": ["Tracking map / UTM sheet", "Landing page spec"], "kpis": {"Broken link rate": 8, "CTA validity": 72}, "static_rules": ["links resolve", "CTA destinations approved", "QR codes valid"], "prompt": "Check links, CTA destinations, QR codes, and redirects."},
            {"id": "tracking-consent", "name": "Tracking, consent and deliverability", "category": "Consent", "weight": 16, "mandatory": True, "critical": True, "static_score": 94, "source_refs": ["Consent / suppression list", "Tracking map"], "kpis": {"Tracking compliance": 94, "Deliverability": 93}, "static_rules": ["UTM present", "unsubscribe present", "suppression honored"], "prompt": "Validate tracking, consent, unsubscribe, and deliverability rules."},
            {"id": "audience-segment", "name": "Audience segmentation", "category": "Audience", "weight": 14, "mandatory": True, "critical": True, "static_score": 93, "source_refs": ["Audience export", "Veeva CRM campaign"], "kpis": {"Audience accuracy": 93, "Suppression breach": 0}, "static_rules": ["HCP list correct", "geography filters correct"], "prompt": "Check audience eligibility and suppression rules."},
            {"id": "variant-parity", "name": "A/B variant compliance parity", "category": "Experiment", "weight": 14, "mandatory": True, "critical": False, "static_score": 90, "source_refs": ["A/B variant package", "Final QA checklist"], "kpis": {"Variant parity": 90, "A/B mismatch": 3}, "static_rules": ["variants approved", "risk statements consistent"], "prompt": "Compare A/B variants for compliance-critical parity."},
            {"id": "qa-signoff", "name": "Final QA sign-off and publish readiness", "category": "Approval", "weight": 14, "mandatory": True, "critical": True, "static_score": 88, "source_refs": ["Final QA checklist", "Publish approval log"], "kpis": {"QA sign-off": 88, "Publish readiness": 86}, "static_rules": ["Litmus report attached", "readiness token created"], "prompt": "Determine final QA sign-off and readiness for publishing."},
        ],
    },
    "publish": {
        "threshold": 94,
        "purpose": "Use AI launch intelligence to confirm activation readiness, audience lock, monitoring coverage, and feedback capture.",
        "steps": [
            {"id": "final-asset-lock", "name": "Final asset lock", "category": "Activation", "weight": 20, "mandatory": True, "critical": True, "static_score": 98, "source_refs": ["Final Approved Asset", "Veeva Vault"], "kpis": {"Asset lock integrity": 98, "Version drift": 0}, "static_rules": ["final version locked", "no post-approval drift"], "prompt": "Confirm final approved asset lock and version integrity."},
            {"id": "audience-channel", "name": "Audience and channel readiness", "category": "Audience", "weight": 22, "mandatory": True, "critical": True, "static_score": 96, "source_refs": ["Audience Snapshot", "Veeva CRM", "Consent List"], "kpis": {"Audience readiness": 96, "Suppression breach": 0}, "static_rules": ["approved audience selected", "suppression honored", "channel eligibility confirmed"], "prompt": "Validate audience and channel readiness before publish."},
            {"id": "activation-ops", "name": "Activation operations check", "category": "Operations", "weight": 18, "mandatory": True, "critical": False, "static_score": 95, "source_refs": ["Publish Plan", "CRM Campaign Object"], "kpis": {"Launch readiness": 95, "Owner coverage": 100}, "static_rules": ["publish window set", "owner assigned", "rollback plan available"], "prompt": "Check publish window, owner readiness, and rollback plan."},
            {"id": "kpi-monitoring", "name": "KPI monitoring stream", "category": "Measurement", "weight": 20, "mandatory": True, "critical": True, "static_score": 79, "source_refs": ["KPI Plan", "Tracking Map"], "kpis": {"KPI stream readiness": 79, "Incident monitor": 92}, "static_rules": ["tracking plan active", "incident monitor configured", "engagement KPIs mapped"], "prompt": "Validate monitoring and KPI stream readiness."},
            {"id": "feedback-learning", "name": "Feedback learning capture", "category": "Learning", "weight": 20, "mandatory": True, "critical": False, "static_score": 93, "source_refs": ["Historical Decisions", "Override Log"], "kpis": {"Feedback capture": 93, "Learning signal quality": 90}, "static_rules": ["reviewer feedback linked", "launch outcomes mapped"], "prompt": "Confirm feedback signals are ready for post-launch learning."},
        ],
    },
}

STAGE_MODULES: Dict[str, List[str]] = {
    "briefing": ["workflow-orchestration", "claims-governance", "compliance"],
    "content-created": ["content-lab", "claims-governance", "evidence"],
    "medical-review": ["compliance", "claims-governance", "evidence", "responsible-ai"],
    "compliance-approval": ["compliance", "responsible-ai", "analytics"],
    "localization": ["localization", "claims-governance", "analytics"],
    "local-approval": ["localization", "compliance", "workflow-orchestration"],
    "qa": ["email-qa", "compliance", "analytics"],
    "publish": ["workflow-orchestration", "integration-layer", "analytics"],
}

STAGE_TASKS: Dict[str, List[Dict[str, Any]]] = {
    "briefing": [
        {"id": "TSK-101", "title": "Map brief claims to approved label", "owner": "Claim Agent", "status": "in_progress", "priority": "High", "analysis": "Two claims are present; one has no source reference.", "next_action": "Attach label excerpt or return to content owner."},
        {"id": "TSK-102", "title": "Check mandatory safety context", "owner": "Compliance Policy Agent", "status": "queued", "priority": "Medium", "analysis": "Safety disclaimer is missing from the draft brief.", "next_action": "Insert required disclaimer before stage transition."},
    ],
    "content-created": [
        {"id": "TSK-201", "title": "Validate benefit claim against evidence", "owner": "Reference Agent", "status": "blocked", "priority": "High", "analysis": "Draft copy implies rapid control without an approved claim variant.", "next_action": "Use approved patient-selection wording or attach an approved comparative reference."},
        {"id": "TSK-202", "title": "Screen attachments for sensitive data", "owner": "Security Agent", "status": "complete", "priority": "Low", "analysis": "No PHI/PII detected in current package.", "next_action": "Keep audit evidence attached."},
    ],
    "medical-review": [
        {"id": "TSK-301", "title": "Deep claim extraction", "owner": "Claim Agent", "status": "complete", "priority": "Medium", "analysis": "Seven claims extracted with source IDs.", "next_action": "Focus reviewer attention on two medium-risk claims."},
        {"id": "TSK-302", "title": "Fair-balance assessment", "owner": "Regulatory Agent", "status": "in_progress", "priority": "High", "analysis": "Benefit copy is prominent; adverse effects section is thin.", "next_action": "Expand risk section before compliance approval."},
    ],
    "compliance-approval": [
        {"id": "TSK-401", "title": "Policy coverage check", "owner": "Compliance Policy Agent", "status": "complete", "priority": "Low", "analysis": "95% policy coverage with no hard blockers.", "next_action": "Route to approver with generated audit packet."},
        {"id": "TSK-402", "title": "Audit evidence lock", "owner": "Audit Agent", "status": "complete", "priority": "Low", "analysis": "Reviewer, source, model, and recommendation evidence captured.", "next_action": "Preserve immutable record for inspection."},
    ],
    "localization": [
        {"id": "TSK-501", "title": "Semantic drift analysis", "owner": "Localization Agent", "status": "in_progress", "priority": "Medium", "analysis": "India translation shows 7% drift, below blocker threshold.", "next_action": "Reviewer should confirm two localized terms."},
        {"id": "TSK-502", "title": "Local policy caveat check", "owner": "Regulatory Agent", "status": "queued", "priority": "Medium", "analysis": "CDSCO caveat needs final affiliate confirmation.", "next_action": "Send caveat list to local market reviewer."},
    ],
    "local-approval": [
        {"id": "TSK-601", "title": "Country approval packet", "owner": "Audit Agent", "status": "in_progress", "priority": "Medium", "analysis": "Local sign-off path is captured; one owner note pending.", "next_action": "Collect owner note and update audit event."},
    ],
    "qa": [
        {"id": "TSK-701", "title": "Litmus rendering analysis", "owner": "QA Agent", "status": "complete", "priority": "Medium", "analysis": "Render score is 96%; Outlook spacing passes.", "next_action": "Retain QA screenshots in evidence packet."},
        {"id": "TSK-702", "title": "Broken-link remediation", "owner": "Security Agent", "status": "blocked", "priority": "High", "analysis": "One prescribing information link returns 404.", "next_action": "Replace link before publish gate opens."},
    ],
    "publish": [
        {"id": "TSK-801", "title": "Audience and channel lock", "owner": "KPI Agent", "status": "complete", "priority": "Low", "analysis": "Audience check passed for approved HCP segment.", "next_action": "Open publish gate and monitor incident metrics."},
    ],
}

STAGE_DEEP_DATA: Dict[str, Dict[str, Any]] = {
    "briefing": {
        "status": "attention",
        "sla": "14h remaining",
        "asset_id": "BRF-IND-RESP-042",
        "brand": "Respivara",
        "content_type": "Campaign brief",
        "market": "India",
        "channel": "Veeva CRM intake",
        "inputs": [
            {"name": "Business request", "value": "Q2 India HCP email and eDetail brief", "source": "Veeva CRM"},
            {"name": "Target audience", "value": "Pulmonologists and high-prescribing GPs", "source": "Campaign plan"},
            {"name": "Claim set", "value": "2 draft claims, 1 unmapped", "source": "Claims library"},
            {"name": "Market constraints", "value": "CDSCO and local PI caveats required", "source": "Regulatory KB"},
        ],
        "outputs": [
            {"name": "Brief readiness", "value": "Rework", "detail": "Missing source mapping and safety context"},
            {"name": "Owner action", "value": "Attach label excerpt", "detail": "Required before Content Creation"},
        ],
        "sources": [
            {"id": "SRC-BRF-001", "title": "Campaign intake form", "type": "Veeva CRM", "confidence": 96},
            {"id": "CLM-184", "title": "COPD burden master claim", "type": "Claims repository", "confidence": 88},
            {"id": "POL-GLB-MLR-02", "title": "Brief completeness SOP", "type": "Policy", "confidence": 94},
        ],
        "validation_checks": [
            {"name": "Brief completeness", "status": "needs_review", "score": 74, "detail": "References missing for one claim"},
            {"name": "Audience alignment", "status": "passed", "score": 92, "detail": "Audience matches campaign plan"},
            {"name": "Indication fit", "status": "passed", "score": 89, "detail": "Therapeutic area and indication are aligned"},
        ],
        "regulatory_checks": [
            {"name": "Market caveat presence", "status": "needs_review", "score": 70},
            {"name": "Off-label screening", "status": "passed", "score": 93},
        ],
        "claim_verifiers": [
            {"claim": "COPD symptom burden remains high in target patients.", "status": "passed", "evidence": "CLM-184 + REF-210"},
            {"claim": "Rapid control improvement", "status": "blocked", "evidence": "No approved comparative reference"},
        ],
        "security_checks": [
            {"name": "PII/PHI scan", "status": "passed", "score": 100},
            {"name": "Access boundary", "status": "passed", "score": 97},
        ],
        "stage_kpis": [
            {"label": "Brief Completeness", "value": "74%", "trend": "-9 pts"},
            {"label": "Claim Mapping", "value": "50%", "trend": "1 gap"},
            {"label": "SLA Risk", "value": "Medium", "trend": "14h left"},
        ],
    },
    "content-created": {
        "status": "blocked",
        "sla": "6h overdue",
        "asset_id": "AST-RESP-EMAIL-042",
        "brand": "Respivara",
        "content_type": "HCP email",
        "market": "India",
        "channel": "Veeva CRM",
        "inputs": [
            {"name": "Draft content", "value": "Email v0.7", "source": "Authoring Workspace"},
            {"name": "Reference pack", "value": "REF-210, REF-311", "source": "Reference DB"},
            {"name": "Approved claims", "value": "CLM-184, SAF-022", "source": "Claims repository"},
            {"name": "Attachment scan", "value": "3 files, no PHI", "source": "Security scanner"},
        ],
        "outputs": [
            {"name": "Claim recommendation", "value": "Rewrite", "detail": "10-year duration exceeds evidence"},
            {"name": "Suggested copy", "value": "Use 8-year supported wording", "detail": "Ready for reviewer approval"},
        ],
        "sources": [
            {"id": "REF-RESP-301", "title": "Respivara RES-301 endpoint evidence summary", "type": "Reference DB", "confidence": 97},
            {"id": "CLM-RESP-184", "title": "Respivara patient-selection claim family", "type": "Claims repository", "confidence": 91},
            {"id": "SEC-SCAN-042", "title": "PII and attachment scan", "type": "Security", "confidence": 100},
        ],
        "validation_checks": [
            {"name": "Evidence and claim fit", "status": "blocked", "score": 42, "detail": "Draft implies rapid control without approved support"},
            {"name": "Reference linkage", "status": "needs_review", "score": 68, "detail": "One citation missing footer anchor"},
            {"name": "Readability", "status": "passed", "score": 87, "detail": "Plain-language copy within threshold"},
        ],
        "regulatory_checks": [
            {"name": "Promotional claim support", "status": "blocked", "score": 45},
            {"name": "Fair balance preview", "status": "needs_review", "score": 71},
        ],
        "claim_verifiers": [
            {"claim": "Rapid control improvement", "status": "blocked", "evidence": "Use CLM-RESP-184 patient-selection wording unless approved comparative support is attached"},
            {"claim": "Strong safety profile", "status": "needs_review", "evidence": "Safety caveat required"},
        ],
        "security_checks": [
            {"name": "PII/PHI scan", "status": "passed", "score": 100},
            {"name": "Attachment integrity", "status": "passed", "score": 98},
        ],
        "stage_kpis": [
            {"label": "Claim Accuracy", "value": "82%", "trend": "-6 pts"},
            {"label": "Overstatement Risk", "value": "High", "trend": "1 blocker"},
            {"label": "Rework Avoided", "value": "35%", "trend": "+8 pts"},
        ],
    },
    "medical-review": {
        "status": "in_review",
        "sla": "1.5d remaining",
        "asset_id": "MLR-RESP-118",
        "brand": "Respivara",
        "content_type": "HCP email + eDetail / CLM",
        "market": "Global",
        "channel": "Veeva Approved Email + Veeva CLM / eDetail",
        "inputs": [
            {"name": "Reviewed content", "value": "v1.1 with source links", "source": "Veeva Vault"},
            {"name": "Label pack", "value": "SmPC + local PI", "source": "Regulatory KB"},
            {"name": "Reviewer comments", "value": "4 open, 2 resolved", "source": "MLR tools"},
        ],
        "outputs": [
            {"name": "Medical decision", "value": "Revise risk section", "detail": "Fair-balance score below threshold"},
            {"name": "Evidence packet", "value": "Complete", "detail": "All high-risk claims traceable"},
        ],
        "sources": [
            {"id": "LBL-SMPC-2026", "title": "Current SmPC and label alignment", "type": "Regulatory KB", "confidence": 95},
            {"id": "REV-CMT-118", "title": "MLR reviewer comments", "type": "MLR system", "confidence": 89},
            {"id": "EVD-311", "title": "Phase III endpoint evidence", "type": "Reference DB", "confidence": 93},
        ],
        "validation_checks": [
            {"name": "Deep claim extraction", "status": "passed", "score": 91, "detail": "Seven claims extracted"},
            {"name": "Evidence traceability", "status": "passed", "score": 92, "detail": "All high-risk claims linked"},
            {"name": "Fair balance", "status": "needs_review", "score": 67, "detail": "Risk section too thin"},
        ],
        "regulatory_checks": [
            {"name": "Label alignment", "status": "passed", "score": 94},
            {"name": "Off-label detection", "status": "passed", "score": 96},
            {"name": "Risk disclosure", "status": "needs_review", "score": 67},
        ],
        "claim_verifiers": [
            {"claim": "Symptom burden reduction", "status": "passed", "evidence": "EVD-311"},
            {"claim": "Safety and tolerability", "status": "needs_review", "evidence": "SAF-022 needs expansion"},
        ],
        "security_checks": [
            {"name": "Reviewer access", "status": "passed", "score": 99},
            {"name": "Document integrity", "status": "passed", "score": 97},
        ],
        "stage_kpis": [
            {"label": "Fair Balance", "value": "67%", "trend": "below target"},
            {"label": "Evidence Traceability", "value": "92%", "trend": "+4 pts"},
            {"label": "Cycle Time", "value": "5.6d", "trend": "-28%"},
        ],
    },
    "compliance-approval": {
        "status": "ready",
        "sla": "On track",
        "asset_id": "CMP-APP-204",
        "brand": "Respivara",
        "content_type": "Modular content approval pack",
        "market": "Global",
        "channel": "Omnichannel approval package",
        "inputs": [
            {"name": "Compliance packet", "value": "Reviewer-ready v2.0", "source": "Veeva Vault"},
            {"name": "SOP rules", "value": "Global MLR policy set", "source": "Policy engine"},
            {"name": "Legal/privacy notes", "value": "No blockers", "source": "Compliance queue"},
        ],
        "outputs": [
            {"name": "Approval readiness", "value": "Ready", "detail": "Policy coverage at 95%"},
            {"name": "Audit packet", "value": "Locked", "detail": "Reviewer, source, and decision evidence captured"},
        ],
        "sources": [
            {"id": "SOP-GLB-001", "title": "Global promotional review policy", "type": "Policy", "confidence": 95},
            {"id": "AUD-PKT-204", "title": "Audit evidence packet", "type": "Audit", "confidence": 98},
        ],
        "validation_checks": [
            {"name": "Policy coverage", "status": "passed", "score": 95, "detail": "No hard blockers"},
            {"name": "Mandatory elements", "status": "passed", "score": 96, "detail": "Required footers present"},
        ],
        "regulatory_checks": [
            {"name": "SOP validation", "status": "passed", "score": 95},
            {"name": "Privacy review", "status": "passed", "score": 98},
        ],
        "claim_verifiers": [
            {"claim": "All promotional claims", "status": "passed", "evidence": "Linked to approved references"},
        ],
        "security_checks": [
            {"name": "Approval role enforcement", "status": "passed", "score": 99},
            {"name": "Immutable audit lock", "status": "passed", "score": 98},
        ],
        "stage_kpis": [
            {"label": "Policy Adherence", "value": "95%", "trend": "+3 pts"},
            {"label": "Pass Rate", "value": "94%", "trend": "+2 pts"},
            {"label": "Audit Readiness", "value": "98%", "trend": "+6 pts"},
        ],
    },
    "localization": {
        "status": "in_review",
        "sla": "22h remaining",
        "asset_id": "LOC-IND-311",
        "brand": "Respivara",
        "content_type": "Local adaptation pack",
        "market": "India",
        "channel": "Veeva Approved Email + Print leave-behind",
        "inputs": [
            {"name": "Global master", "value": "Approved content v2.0", "source": "Veeva Vault"},
            {"name": "Translation memory", "value": "India glossary locked", "source": "Localization hub"},
            {"name": "Local market rule pack", "value": "CDSCO and affiliate SOP", "source": "Regulatory KB"},
        ],
        "outputs": [
            {"name": "Localized content", "value": "v2.1", "detail": "Semantic drift within threshold"},
            {"name": "Reviewer note", "value": "Confirm two local terms", "detail": "Affiliate review recommended"},
        ],
        "sources": [
            {"id": "TM-IND-042", "title": "India translation memory", "type": "Localization", "confidence": 94},
            {"id": "CDSCO-POL-12", "title": "India local promotional caveat", "type": "Regulatory KB", "confidence": 90},
        ],
        "validation_checks": [
            {"name": "Semantic drift", "status": "needs_review", "score": 93, "detail": "7% drift, below blocker threshold"},
            {"name": "Terminology lock", "status": "passed", "score": 96, "detail": "Glossary preserved"},
        ],
        "regulatory_checks": [
            {"name": "Local compliance", "status": "passed", "score": 91},
            {"name": "Country caveat", "status": "needs_review", "score": 82},
        ],
        "claim_verifiers": [
            {"claim": "Localized COPD burden claim", "status": "passed", "evidence": "Meaning preserved from CLM-184"},
        ],
        "security_checks": [
            {"name": "Translation package integrity", "status": "passed", "score": 99},
            {"name": "External vendor boundary", "status": "passed", "score": 92},
        ],
        "stage_kpis": [
            {"label": "Localization Accuracy", "value": "93%", "trend": "+5 pts"},
            {"label": "Drift Score", "value": "7%", "trend": "review"},
            {"label": "Local Rework", "value": "12%", "trend": "-4 pts"},
        ],
    },
    "local-approval": {
        "status": "attention",
        "sla": "1d remaining",
        "asset_id": "LAPP-IND-552",
        "brand": "Respivara",
        "content_type": "Localized leave behind",
        "market": "India",
        "channel": "Local MLR + Veeva Vault",
        "inputs": [
            {"name": "Localized packet", "value": "v2.1 with caveats", "source": "Affiliate Content Hub"},
            {"name": "Local reviewer route", "value": "Compliance lead + market owner", "source": "Local MLR Tools"},
            {"name": "Country policy note", "value": "1 pending owner note", "source": "Policy engine"},
        ],
        "outputs": [
            {"name": "Country approval signal", "value": "Pending note", "detail": "Final owner confirmation required"},
            {"name": "Local audit entry", "value": "Open", "detail": "Waiting for sign-off"},
        ],
        "sources": [
            {"id": "LAPP-ROUTE-552", "title": "India local approval route", "type": "MLR system", "confidence": 88},
            {"id": "LOC-AUD-552", "title": "Local approval audit draft", "type": "Audit", "confidence": 84},
        ],
        "validation_checks": [
            {"name": "Approval packet completeness", "status": "needs_review", "score": 84, "detail": "One owner note pending"},
            {"name": "Market readiness", "status": "passed", "score": 90, "detail": "Channel fit confirmed"},
        ],
        "regulatory_checks": [
            {"name": "Country-specific compliance", "status": "passed", "score": 90},
            {"name": "Local policy adherence", "status": "needs_review", "score": 84},
        ],
        "claim_verifiers": [
            {"claim": "All localized claims", "status": "passed", "evidence": "No semantic claim drift"},
        ],
        "security_checks": [
            {"name": "Local role access", "status": "passed", "score": 96},
            {"name": "Approval evidence capture", "status": "needs_review", "score": 84},
        ],
        "stage_kpis": [
            {"label": "Country Compliance", "value": "90%", "trend": "+1 pt"},
            {"label": "Approval Cycle", "value": "3.2d", "trend": "on track"},
            {"label": "Owner Notes", "value": "1", "trend": "pending"},
        ],
    },
    "qa": {
        "status": "blocked",
        "sla": "8h remaining",
        "asset_id": "QA-LIT-909",
        "brand": "Respivara",
        "content_type": "Approved email HTML package",
        "market": "India",
        "channel": "Litmus email QA",
        "inputs": [
            {"name": "Approved email HTML", "value": "v3.0", "source": "Veeva CRM"},
            {"name": "Litmus result", "value": "96% render score", "source": "Litmus"},
            {"name": "Link inventory", "value": "1 broken PI link", "source": "QA scanner"},
        ],
        "outputs": [
            {"name": "QA readiness", "value": "Blocked", "detail": "Fix broken prescribing information link"},
            {"name": "Evidence pack", "value": "Available", "detail": "Rendering screenshots retained"},
        ],
        "sources": [
            {"id": "LIT-909", "title": "Litmus render and spam report", "type": "Litmus", "confidence": 96},
            {"id": "LINK-PI-404", "title": "Prescribing information link check", "type": "QA scanner", "confidence": 100},
        ],
        "validation_checks": [
            {"name": "Render accuracy", "status": "passed", "score": 96, "detail": "Outlook and mobile previews pass"},
            {"name": "Link validation", "status": "blocked", "score": 72, "detail": "One PI link returns 404"},
            {"name": "Spam and accessibility", "status": "passed", "score": 93, "detail": "No critical issues"},
        ],
        "regulatory_checks": [
            {"name": "Tracking compliance", "status": "passed", "score": 96},
            {"name": "Unsubscribe and PI presence", "status": "blocked", "score": 72},
        ],
        "claim_verifiers": [
            {"claim": "Final approved claims", "status": "passed", "evidence": "No changes after MLR lock"},
        ],
        "security_checks": [
            {"name": "Link safety", "status": "blocked", "score": 72},
            {"name": "Tracking domain check", "status": "passed", "score": 94},
        ],
        "stage_kpis": [
            {"label": "Render Score", "value": "96%", "trend": "+2 pts"},
            {"label": "QA Pass Rate", "value": "88%", "trend": "1 blocker"},
            {"label": "Deliverability", "value": "93%", "trend": "+4 pts"},
        ],
    },
    "publish": {
        "status": "ready",
        "sla": "Ready now",
        "asset_id": "PUB-IND-778",
        "brand": "Respivara",
        "content_type": "Approved email",
        "market": "India",
        "channel": "Veeva Approved Email",
        "inputs": [
            {"name": "Approved asset", "value": "Final v3.1", "source": "Veeva Vault"},
            {"name": "Audience segment", "value": "Approved HCP segment", "source": "Veeva CRM"},
            {"name": "Publish gate", "value": "Open after QA fix", "source": "Workflow router"},
        ],
        "outputs": [
            {"name": "Publish decision", "value": "Ready", "detail": "Audience and compliance lock passed"},
            {"name": "Monitoring plan", "value": "Live", "detail": "Incident and engagement KPIs active"},
        ],
        "sources": [
            {"id": "AUD-FINAL-778", "title": "Final asset lineage lock", "type": "Audit", "confidence": 98},
            {"id": "CRM-AUD-778", "title": "Approved HCP audience snapshot", "type": "Veeva CRM", "confidence": 95},
        ],
        "validation_checks": [
            {"name": "Audience lock", "status": "passed", "score": 98, "detail": "Approved HCP segment only"},
            {"name": "Final content integrity", "status": "passed", "score": 99, "detail": "No post-approval drift"},
        ],
        "regulatory_checks": [
            {"name": "Publish compliance", "status": "passed", "score": 98},
            {"name": "Channel policy", "status": "passed", "score": 97},
        ],
        "claim_verifiers": [
            {"claim": "All final claims", "status": "passed", "evidence": "Locked to approved claim packet"},
        ],
        "security_checks": [
            {"name": "Audience permission", "status": "passed", "score": 98},
            {"name": "Channel access", "status": "passed", "score": 97},
        ],
        "stage_kpis": [
            {"label": "Incident Risk", "value": "Low", "trend": "0 blockers"},
            {"label": "Engagement/Risk", "value": "3.7x", "trend": "+0.4"},
            {"label": "Time to Market", "value": "-22%", "trend": "improved"},
        ],
    },
}

STAGE_AGENT_STEPS: Dict[str, List[Dict[str, str]]] = {
    stage["id"]: [
        {"agent": agent, "input": stage["trigger"], "analysis": f"Review {stage['name'].lower()} evidence and policy context.", "output": stage["recommendation"]}
        for agent in stage["agents"]
    ]
    for stage in ORCHESTRATION_STAGES
}

STAGE_ENGINE_LABELS = {
    "briefing": "Brief Intelligence Engine",
    "content-created": "Content Validation Engine",
    "medical-review": "Claims Validation Engine",
    "compliance-approval": "Global Compliance Engine",
    "localization": "Localization Validation Engine",
    "local-approval": "Local Approval Engine",
    "qa": "Channel QA Engine",
    "publish": "Publishing Readiness Engine",
}

STAGE_NAME_OVERRIDES = {
    "briefing": "Brief and Planning Validation",
    "content-created": "Content Validation",
}

STAGE_MODEL_PROFILE = {
    "briefing": "balanced",
    "content-created": "balanced",
    "medical-review": "reasoning",
    "compliance-approval": "compliance",
    "localization": "localization",
    "local-approval": "compliance",
    "qa": "multimodal",
    "publish": "balanced",
}

STAGE_REQUIRED_DOCUMENTS = {
    "briefing": ["Campaign Brief", "Brand Guideline", "Approved Claim Library", "Publication Plan"],
    "content-created": ["Approved Brief", "Brand Guideline", "Approved Claim Library", "Channel Template", "Safety Statement"],
    "medical-review": ["Draft Content", "Claim Matrix", "Approved Claim Library", "Clinical Study Report", "SmPC / Prescribing Information", "Safety Statement"],
    "compliance-approval": ["MLR Approved Content", "SOP / Policy", "Legal Disclaimer", "Privacy Requirement", "Approval Matrix"],
    "localization": ["Global Approved Content", "Local Disclaimer", "Translation Memory", "Local Label / PI", "Local Style Guide"],
    "local-approval": ["Localized Content", "Local MLR Checklist", "Country Approval Matrix", "Local Label / PI"],
    "qa": ["Final Approved Asset", "Email HTML / Creative Asset", "Audience Export", "Tracking Map", "Litmus QA Report"],
    "publish": ["QA Approved Asset", "Audience Snapshot", "Publish Readiness Pack", "Monitoring Plan"],
}

for stage in ORCHESTRATION_STAGES:
    stage["name"] = STAGE_NAME_OVERRIDES.get(stage["id"], stage["name"])
    stage["modules"] = STAGE_MODULES.get(stage["id"], [])
    stage["tasks"] = STAGE_TASKS.get(stage["id"], [])
    stage["agent_steps"] = STAGE_AGENT_STEPS.get(stage["id"], [])
    stage.update(STAGE_DEEP_DATA.get(stage["id"], {}))
    stage["brand"] = FIXED_BRAND
    stage["market"] = FIXED_MARKET
    stage["channel"] = FIXED_CHANNEL
    stage["content_type"] = {
        "briefing": "Campaign Brief",
        "content-created": "HCP Approved Email + CLM / eDetail Aid",
        "medical-review": "HCP Approved Email + CLM / eDetail Aid",
        "compliance-approval": "HCP Approved Email + CLM / eDetail Aid",
        "localization": "HCP Approved Email + CLM / eDetail Aid",
        "local-approval": "HCP Approved Email + CLM / eDetail Aid",
        "qa": "HCP Approved Email + CLM / eDetail Aid",
        "publish": "HCP Approved Email + CLM / eDetail Aid",
    }.get(stage["id"], "Regulated content package")
    stage["system"] = FIXED_CHANNEL
    stage["engine_label"] = STAGE_ENGINE_LABELS.get(stage["id"], "AI Compliance Engine")
    stage["flow_scope"] = "Global Stage" if stage["order"] <= 4 else "Local Stage"
    stage["default_model_profile"] = STAGE_MODEL_PROFILE.get(stage["id"], "balanced")
    stage["required_documents"] = STAGE_REQUIRED_DOCUMENTS.get(stage["id"], [])
    stage["available_documents"] = [document["id"] for document in LIBRARY_DOCUMENTS if stage["id"] in document.get("stage_ids", [])]
    stage["model_profiles"] = list(AI_MODEL_PROFILES.values())
    stage["active_model"] = AI_MODEL_PROFILES[stage["default_model_profile"]]
    stage["validation_score"] = stage.get("score", 0)
    stage["task_count"] = len(stage.get("tasks", []))
    stage["open_task_count"] = len([task for task in stage.get("tasks", []) if task.get("status") != "complete"])
    stage["review_actions"] = [
        {"id": "accept", "label": "Accept recommendation", "impact": "Routes the current packet to the next approval gate."},
        {"id": "override", "label": "Override with reason", "impact": "Captures reviewer rationale and feedback signal."},
        {"id": "escalate", "label": "Escalate", "impact": "Notifies the accountable review lead and locks a high-risk audit event."},
    ]
    stage["agent_trace"] = [
        {
            "agent": step["agent"],
            "status": "blocked" if "block" in step["output"].lower() else "needs_review" if stage["risk"] != "low" else "passed",
            "input": step["input"],
            "output": step["output"],
            "confidence": max(72, min(98, stage.get("score", 88) - index * 2)),
        }
        for index, step in enumerate(stage["agent_steps"])
    ]

def dashboard_overview(
    markets: str = "",
    brands: str = "",
    content_types: str = "",
    risks: str = "",
    channels: str = "",
    date_range: str = "",
) -> Dict[str, Any]:
    available_markets = [FIXED_MARKET]
    available_brands = [FIXED_BRAND]
    available_content_types = FIXED_CONTENT_TYPES
    available_risks = sorted({stage["risk"] for stage in ORCHESTRATION_STAGES} | {item["risk"] for item in COMPLIANCE_KPIS["market_heatmap"]})
    available_channels = FIXED_CHANNELS
    filtered_docs = LIBRARY_DOCUMENTS
    if brands and brands != "All":
        filtered_docs = [doc for doc in filtered_docs if matches_locked_context(doc, "brand", brands)]
    if markets and markets != "All":
        filtered_docs = [doc for doc in filtered_docs if matches_locked_context(doc, "market", markets)]
    if content_types and content_types != "All":
        filtered_docs = [doc for doc in filtered_docs if matches_locked_context(doc, "document_type", content_types)]
    if channels and channels != "All":
        filtered_docs = [doc for doc in filtered_docs if matches_locked_context(doc, "channel", channels)]
    visible_doc_ids = {doc["id"] for doc in filtered_docs}
    stage_ids_from_docs = {stage_id for doc in filtered_docs for stage_id in doc.get("stage_ids", [])}
    filtered_stages = [stage for stage in ORCHESTRATION_STAGES if not stage_ids_from_docs or stage["id"] in stage_ids_from_docs]
    if risks and risks != "All":
        filtered_stages = [stage for stage in filtered_stages if stage.get("risk") == risks]
    if not filtered_stages:
        filtered_stages = ORCHESTRATION_STAGES
    blocked_stages = [stage for stage in filtered_stages if stage.get("status") == "blocked"]
    open_tasks = [task for stage in filtered_stages for task in STAGE_TASKS.get(stage["id"], []) if task.get("status") != "complete"]
    completed_tasks = [task for stage in filtered_stages for task in STAGE_TASKS.get(stage["id"], []) if task.get("status") == "complete"]
    avg_score = round(sum(stage["score"] for stage in filtered_stages) / len(filtered_stages))
    doc_volume = len(filtered_docs)
    active_brand_count = len({doc["brand"] for doc in filtered_docs if doc.get("brand") != "All Brands"})
    validation_docs = [doc for doc in filtered_docs if any(term in " ".join([doc.get("title", ""), doc.get("document_type", ""), " ".join(doc.get("taxonomy", []))]).lower() for term in ["validation", "smpc", "claim", "safety", "matrix", "test", "policy", "sop", "approval", "qa"])]
    source_system_counts = {}
    for doc in filtered_docs:
        source_system_counts[doc.get("source_name", "Unknown")] = source_system_counts.get(doc.get("source_name", "Unknown"), 0) + 1
    return {
        "filters": {
            "markets": available_markets,
            "brands": available_brands,
            "content_types": available_content_types,
            "risks": ["All"] + available_risks,
            "channels": available_channels,
            "date_range": ["Today", "7 days", "30 days", "Quarter"],
        },
        "kpi_cards": [
            {"group": "Compliance", "label": "Compliance score", "value": f"{avg_score}%", "trend": "+4 pts", "status": "good"},
            {"group": "Regulatory", "label": "Label alignment", "value": f"{min(99, avg_score + 4)}%", "trend": "+3 pts", "status": "good"},
            {"group": "Security", "label": "PHI/PII blocks", "value": "0", "trend": "clean", "status": "good"},
            {"group": "Content Ops", "label": "Indexed assets", "value": str(doc_volume), "trend": f"{active_brand_count} active brand(s)", "status": "watch"},
            {"group": "AI Performance", "label": "Validation accuracy", "value": f"{max(82, min(96, avg_score - 1))}%", "trend": "+7 pts", "status": "good"},
            {"group": "Tasks", "label": "Completion", "value": f"{len(completed_tasks)}/{len(completed_tasks) + len(open_tasks)}", "trend": f"{len(open_tasks)} open", "status": "watch"},
            {"group": "Approvals", "label": "Open gates", "value": str(len([item for item in APPROVAL_GATES if item.get("status") in {"pending", "requested"}])), "trend": "human review", "status": "watch"},
            {"group": "Alerts", "label": "Open alerts", "value": str(len([item for item in ALERTS if item.get("status") == "open"])), "trend": "2 critical watchouts", "status": "watch"},
        ],
        "workflow_funnel": [
            {"stage": stage["name"], "count": max(4, doc_volume * 2 + 48 - stage["order"] * 3), "blocked": 1 if stage.get("status") == "blocked" else len([issue for issue in stage.get("issues", []) if "No blockers" not in issue]), "score": stage["score"], "flow": "global" if stage["order"] <= 4 else "local"}
            for stage in filtered_stages
        ],
        "market_heatmap": [item for item in COMPLIANCE_KPIS["market_heatmap"] if markets in {"", "All", item["market"]}],
        "sla_timeline": [
            {"label": stage["name"], "sla": stage.get("sla", "On track"), "risk": stage["risk"], "status": stage.get("status", "ready")}
            for stage in filtered_stages
        ],
        "blocker_distribution": [
            {"label": "Claims", "value": max(1, len([doc for doc in filtered_docs if "claim" in json.dumps(doc).lower()]))},
            {"label": "References", "value": max(1, len([doc for doc in filtered_docs if "reference" in json.dumps(doc).lower() or "clinical" in json.dumps(doc).lower()]))},
            {"label": "Fair balance", "value": max(1, len([stage for stage in filtered_stages if stage.get("risk") != "low"]))},
            {"label": "Local policy", "value": max(1, len([doc for doc in filtered_docs if doc.get("region") != "Global"]))},
            {"label": "QA links", "value": max(1, len([doc for doc in filtered_docs if "qa" in json.dumps(doc).lower() or "link" in json.dumps(doc).lower()]))},
        ],
        "task_summary": {
            "open": len(open_tasks),
            "blocked": len([task for task in open_tasks if task.get("status") == "blocked"]),
            "complete": len(completed_tasks),
            "high_priority": len([task for task in open_tasks if task.get("priority") == "High"]),
        },
        "audit_exceptions": AUDIT_EVENTS[:5],
        "blocked_stages": [{"id": stage["id"], "name": stage["name"], "issue": stage["issues"][0], "owner": stage["tasks"][0]["owner"] if stage.get("tasks") else "System"} for stage in blocked_stages],
        "rule_engine": {
            "configured_stages": len(RULE_ENGINE_STAGES),
            "runs_today": len(RULE_ENGINE_RUNS),
            "pending_approvals": len([approval for approval in APPROVAL_TRACKER if approval.get("action") != "approve"]),
            "open_notifications": len([item for item in NOTIFICATIONS if not item.get("read")]),
            "gemini_available": client is not None,
        },
        "notifications": NOTIFICATIONS[:6],
        "approval_tracker": APPROVAL_TRACKER[:6],
        "alerts": ALERTS[:8],
        "document_sources": DOCUMENT_SOURCES,
        "dashboard_depth": {
            "root_cause": [
                {"label": "Affected assets", "value": str(len({doc.get("id") for doc in filtered_docs if any(term in json.dumps(doc).lower() for term in ["claim", "safety", "reference", "disclaimer"])}))},
                {"label": "Top owner", "value": "Medical Legal Review"},
                {"label": "Avg evidence age", "value": "19 days"},
                {"label": "Primary source", "value": max(source_system_counts, key=source_system_counts.get) if source_system_counts else "Veeva Vault"},
            ],
            "throughput": [
                {"label": "Gate entries", "value": str(sum(item["count"] for item in [
                    {"count": max(4, doc_volume * 2 + 48 - stage["order"] * 3)} for stage in filtered_stages
                ]))},
                {"label": "Global/local split", "value": f"{len([stage for stage in filtered_stages if stage['order'] <= 4])}:{len([stage for stage in filtered_stages if stage['order'] > 4])}"},
                {"label": "Rework queue", "value": str(len(blocked_stages) + len([task for task in open_tasks if task.get("status") == "blocked"]))},
                {"label": "Fastest gate", "value": min(filtered_stages, key=lambda stage: len(STAGE_TASKS.get(stage["id"], [])))["name"]},
            ],
            "validation_operations": [
                {"label": "Validation docs", "value": str(len(validation_docs))},
                {"label": "Rule checks", "value": str(sum(len(stage.get("validation_checks", [])) for stage in filtered_stages))},
                {"label": "Evidence links", "value": str(sum(len(doc.get("claims", [])) for doc in filtered_docs))},
                {"label": "Model profile", "value": GEMINI_MODEL},
            ],
            "audit_exceptions": [
                {"label": "Critical/high", "value": str(len([event for event in AUDIT_EVENTS if event.get("severity") in {"critical", "high"}]))},
                {"label": "Open alerts", "value": str(len([item for item in ALERTS if item.get("status") == "open"]))},
                {"label": "Latest source", "value": AUDIT_EVENTS[0].get("source_system", "Audit") if AUDIT_EVENTS else "Audit"},
                {"label": "Traceability", "value": f"{len(visible_doc_ids)} source refs"},
            ],
        },
        "document_library": {
            "total": len(filtered_docs),
            "approved": len([doc for doc in filtered_docs if doc["approval_status"] == "approved"]),
            "in_review": len([doc for doc in filtered_docs if doc["approval_status"] == "in_review"]),
            "sources": len(DOCUMENT_SOURCES),
        },
    }

def build_stage_validation(stage: Dict[str, Any]) -> Dict[str, Any]:
    blockers = []
    for group in ["validation_checks", "regulatory_checks", "claim_verifiers", "security_checks"]:
        for item in stage.get(group, []):
            if item.get("status") in {"blocked", "needs_review"}:
                blockers.append({"group": group, "name": item.get("name") or item.get("claim"), "status": item.get("status"), "detail": item.get("detail") or item.get("evidence", "")})
    decision = "ESCALATE" if any(item["status"] == "blocked" for item in blockers) else "REWORK" if blockers else "PASS"
    return {
        "stage_id": stage["id"],
        "risk_score": 100 - stage.get("score", 80),
        "validation_score": stage.get("validation_score", stage.get("score", 80)),
        "decision": decision,
        "findings": blockers,
        "recommended_action": stage["recommendation"],
        "suggested_fixes": [task["next_action"] for task in stage.get("tasks", []) if task.get("status") != "complete"][:4],
        "trace": stage.get("agent_trace", []),
        "sources": stage.get("sources", []),
    }

def now_ist() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M IST")

def clone_json(value: Any) -> Any:
    return json.loads(json.dumps(value))

def rule_stage(stage_id: str) -> Optional[Dict[str, Any]]:
    return RULE_ENGINE_STAGES.get(stage_id)

def stage_by_id(stage_id: str) -> Optional[Dict[str, Any]]:
    return next((item for item in ORCHESTRATION_STAGES if item["id"] == stage_id), None)

def stage_media(stage_id: str) -> List[Dict[str, Any]]:
    return [item for item in SAMPLE_MEDIA_FILES if item["id"] in ALLOWED_SAMPLE_MEDIA_IDS and stage_id in item.get("stage_ids", [])]

def stage_documents(stage_id: str) -> List[Dict[str, Any]]:
    return [document for document in LIBRARY_DOCUMENTS if stage_id in document.get("stage_ids", [])]

def document_by_id(document_id: str) -> Optional[Dict[str, Any]]:
    return next((document for document in LIBRARY_DOCUMENTS if document["id"] == document_id), None)

def bundle_documents(bundle_id: str) -> List[Dict[str, Any]]:
    bundle = INPUT_BUNDLES.get(bundle_id)
    if not bundle:
        return []
    return [document for document in LIBRARY_DOCUMENTS if document["id"] in bundle.get("document_ids", [])]

def matches_locked_context(doc: Dict[str, Any], key: str, value: str) -> bool:
    if not value or value == "All":
        return True
    needle = value.lower()
    if key == "document_type":
        haystack = " ".join([
            str(doc.get("document_type", "")),
            str(doc.get("title", "")),
            " ".join(doc.get("taxonomy", [])),
        ]).lower()
        aliases = {
            "email": ["email", "approved email"],
            "campaign brief": ["campaign brief", "brief"],
            "clm / edetail aid": ["clm", "edetail", "e-detail", "detail aid"],
            "hcp leave behind": ["leave behind", "brochure", "print qa", "print", "hcp handout"],
        }
        return any(term in haystack for term in aliases.get(needle, [needle]))
    if key == "channel":
        haystack = " ".join([
            str(doc.get("channel", "")),
            str(doc.get("source_name", "")),
            str(doc.get("source_id", "")),
            str(doc.get("title", "")),
            str(doc.get("document_type", "")),
        ]).lower()
        aliases = {
            "veeva crm": ["veeva crm", "campaign", "approved email"],
            "vault": ["vault", "claim", "approved content"],
            "litmus": ["litmus", "qa", "email html"],
        }
        return any(term in haystack for term in aliases.get(needle, [needle]))
    return needle in str(doc.get(key, "")).lower()

def search_documents(
    q: str = "",
    brand: str = "",
    document_type: str = "",
    region: str = "",
    market: str = "",
    channel: str = "",
    approval_status: str = "",
    source_id: str = "",
    stage_id: str = "",
) -> List[Dict[str, Any]]:
    result = LIBRARY_DOCUMENTS
    filters = {
        "brand": brand,
        "document_type": document_type,
        "region": region,
        "market": market,
        "channel": channel,
        "approval_status": approval_status,
        "source_id": source_id,
    }
    for key, value in filters.items():
        if value:
            result = [doc for doc in result if matches_locked_context(doc, key, value)]
    if stage_id:
        result = [doc for doc in result if stage_id in doc.get("stage_ids", [])]
    if q:
        needle = q.lower()
        result = [doc for doc in result if needle in json.dumps(doc).lower()]
    return result

STAGE_OUTPUT_BLUEPRINTS: Dict[str, str] = {
    "briefing": """Respivara India Campaign Brief and Plan

Brand, market, channel
- Brand: Respivara.
- Market: India.
- Channel: Veeva CRM.
- Content types in scope: Campaign Brief, HCP Approved Email, CLM / eDetail Aid, HCP Leave Behind.

Business objective
- Increase quality engagement with Indian pulmonologists and high-prescribing GPs who manage eligible adult respiratory patients.
- Move HCPs from general disease-awareness interest to a structured clinical conversation around eligible maintenance therapy review.
- Keep every benefit statement inside approved Respivara claim language, with risk context visible in the same module.

Audience plan
- Primary audience: pulmonologists in tier 1 and tier 2 cities with recent Veeva CRM activity or recent respiratory brand engagement.
- Secondary audience: high-prescribing GPs who manage chronic respiratory follow-up and refer complex cases.
- Exclusion rules: non-HCP contacts, unconsented HCPs, inactive records, restricted territories, and accounts without current consent status.

Message hierarchy
- Lead message: identify eligible adult patients whose symptom burden remains uncontrolled despite current management.
- Support point 1: Respivara may be considered for eligible maintenance-treatment patients according to approved prescribing information.
- Support point 2: clinical discussion should be grounded in patient selection, safety considerations, and local PI requirements.
- Mandatory balance: abbreviated safety statement, limitation language, PI link, and reference IDs must remain adjacent to benefit claims.

Content plan by type
- HCP Approved Email: subject line, preheader, hero, one approved claim module, safety footer, PI CTA, unsubscribe, tracking tags, and Veeva CRM campaign metadata.
- CLM / eDetail Aid: three screen sequence covering patient identification, claim/evidence support, and safety/next-step discussion; each screen needs a reference drawer and locked claim IDs.
- HCP Leave Behind: two-page HCP-only PDF/print piece with patient-selection summary, evidence sidebar, safety block, PI QR/link, local disclaimer, print QA, and representative distribution controls.
- Campaign Brief: objective, audience, claims, evidence sources, owners, approval route, QA route, launch window, and measurable success criteria.

Evidence and source packet
- DOC-CLAIM-RESP-008 controls exact claim wording and permitted short-form variants.
- DOC-SMPC-RESP-2026 controls indication, population, dosing context, and safety adjacency.
- DOC-CSR-RESP-P3-118 supports endpoint language but cannot be used to create unsupported superiority claims.
- DOC-SAF-RESP-022 controls safety module copy, footer prominence, and fair-balance rules.

Operational plan
- Brief owner: India brand team.
- Medical owner: respiratory medical reviewer.
- Compliance owner: promotional compliance reviewer.
- Channel owner: Veeva CRM campaign operations.
- Stage handoff: freeze brief, create content, validate medical/regulatory support, approve compliance, localize final copy, complete local approval, run QA, publish through Veeva CRM.

Acceptance criteria
- Every claim has a claim ID, approved source, owner, permitted use, and expiry.
- Email, CLM, and HCP Leave Behind modules use only approved Respivara language.
- India local caveat and PI link are present before local approval.
- Veeva CRM audience, suppression, tracking, and publish-window metadata are complete before activation.""",
    "content-created": """Respivara Content Package From Approved Brief

HCP Approved Email
- Subject line: Respivara clinical update for eligible adult respiratory patients.
- Preheader: Review patient selection, evidence context, and safety considerations in a concise HCP update.
- Hero copy: For eligible adult patients with ongoing symptom burden, review whether maintenance-treatment planning is aligned with approved Respivara prescribing information.
- Claim module: Respivara may support symptom-control planning in eligible adult patients when used according to the approved prescribing information.
- Evidence note: Claim aligned to DOC-CLAIM-RESP-008 and supported by DOC-CSR-RESP-P3-118; no superiority or unqualified rapid-control language is permitted.
- Safety module: Important safety information and local PI link must remain visible before CTA interaction.
- CTA: Review Respivara patient-selection considerations.
- Veeva CRM metadata: campaign RESP-IN-2026-Q2, audience HCP-consented respiratory segment, market India, channel Veeva CRM.

CLM / eDetail Aid
- Screen 1: Patient identification. Focus on eligible adult respiratory patients with persistent symptom burden; include population qualifier and local PI cue.
- Screen 2: Evidence-supported discussion. Present approved claim language, reference drawer, endpoint qualifier, and limitation note.
- Screen 3: Safety and next step. Place safety considerations before the representative discussion prompt; include PI link and final MLR code placeholder.
- Interaction rules: no free-text claim editing, reference drawer opens from every claim-bearing screen, and CRM call-object metadata captures screen sequence completion.

HCP Leave Behind
- Format: two-page HCP-only PDF/print piece for representative follow-up after a compliant HCP call.
- Page 1: patient-selection summary, approved claim module, reference ID, representative-use note, and brief evidence context.
- Page 2: safety statement, local PI QR/link, evidence sidebar, adverse event reporting cue, India local disclaimer, and MLR footer.
- Production controls: print safe area, bleed/trim, QR scan evidence, PDF/A export, version lock, and Veeva distribution record.

Content QA notes
- Remove unsupported duration and superiority language.
- Keep safety copy adjacent to benefit claims.
- Confirm all links resolve to approved India PI destinations.
- Freeze output as AST-RESP-CONTENT-042 before medical review.""",
    "medical-review": """Medical and Regulatory Validation Document

Scope
- Asset: Respivara HCP Approved Email and CLM / eDetail Aid.
- Market: India.
- Channel: Veeva CRM.

Claim extraction
- Primary benefit claim is mapped to DOC-CLAIM-RESP-008.
- Patient-selection language is aligned to DOC-SMPC-RESP-2026.
- Evidence-support language references DOC-CSR-RESP-P3-118 with endpoint qualification.

Findings
- Pass: audience and indication language remain within approved adult maintenance-treatment context.
- Pass: reference IDs are present on all claim-bearing modules.
- Rework: fair-balance copy must be expanded in the email footer and CLM safety screen before compliance approval.
- Rework: remove any phrasing implying rapid control or comparative superiority unless a specifically approved claim variant is attached.

Medical decision
- Conditional proceed to compliance after risk copy expansion and final reference drawer check.""",
    "compliance-approval": """Compliance Approval Validation Document

Scope
- Respivara India HCP Approved Email and CLM / eDetail Aid for Veeva CRM.

Policy checks
- SOP mapping complete for promotional HCP material.
- Approval authority mapped to India MLR route.
- Privacy and consent requirements rely on Veeva CRM audience eligibility and suppression rules.
- Required elements: brand name, intended audience, local PI link, safety language, reference IDs, MLR code placeholder, unsubscribe for email.

Compliance decision
- Approved for local adaptation once the fair-balance expansion from medical review is incorporated.
- No new claims may be introduced during localization.
- Audit lock must preserve source IDs, reviewer comments, model run ID, and final version hash.""",
    "localization": """India Local Adaptation Validation Document

Scope
- Local adaptation of the approved Respivara email and CLM package for India.

Checks completed
- Medical meaning preserved across localized terms.
- Local caveat, PI link, and safety placement are present.
- Veeva CRM channel metadata remains unchanged.
- Cultural and format review found no imagery or terminology conflict for the India HCP audience.

Open item
- Affiliate reviewer must confirm two glossary choices before country sign-off.

Recommendation
- Proceed to local approval after glossary confirmation and version freeze.""",
    "local-approval": """Local Approval Validation Document

Scope
- Country approval packet for Respivara India Veeva CRM activation.

Approval evidence
- Local reviewer route captured.
- Country caveat reviewed.
- Local PI destination attached.
- Version v2.1 locked against the global approved source.

Decision
- Ready for QA after final owner note is attached.
- Any post-approval copy edits must reopen local approval.""",
    "qa": """Channel Prep and QA Validation Document

Scope
- Respivara HCP Approved Email and CLM / eDetail Aid in Veeva CRM.

QA checklist
- Email rendering: desktop and mobile preview pass.
- CLM package: screen sequence, reference drawer, and safety screen present.
- Tracking: campaign, content, CTA, and audience tags attached.
- Consent: suppression and eligibility checks passed.
- Blocker: one prescribing information URL must be replaced before publish.

Recommendation
- Hold publish gate until PI URL is corrected and QA evidence is reattached.""",
    "publish": """Publish Readiness Document

Scope
- Respivara India launch through Veeva CRM.

Readiness checks
- Final asset version locked.
- Audience segment approved and suppression applied.
- Publish window and owner assigned.
- Monitoring plan covers opens, clicks, rep follow-up, incident signal, and reviewer feedback capture.
- Rollback owner and escalation path are documented.

Decision
- Ready to activate after QA blocker closure.
- Post-launch monitoring starts immediately after Veeva CRM activation."""
}

def build_stage_output(stage: Dict[str, Any], run: Optional[Dict[str, Any]], actor_email: str, output_text: str = "") -> Dict[str, Any]:
    output_id = f"OUT-{stage['id'].upper()}-{len(STAGE_OUTPUT_DOCUMENTS) + 1:04d}"
    blueprint = STAGE_OUTPUT_BLUEPRINTS.get(stage["id"], "")
    run_data = run or {}
    selected_docs = run_data.get("selected_documents", stage_documents(stage["id"]))
    content_terms = ["campaign brief", "email", "clm", "edetail", "e-detail", "leave behind", "content master", "copy deck", "storyboard", "brochure"]
    validation_terms = ["validation", "qa", "claim", "smpc", "prescribing", "safety", "clinical", "policy", "sop", "disclaimer", "approval", "test", "kpi"]
    hard_validation_terms = ["validation", "qa report", "support pack", "matrix", "test cases", "safety", "smpc", "prescribing", "clinical", "claim library", "local disclaimer", "print qa", "reference drawer", "evidence mapping", "metadata"]
    def document_text(doc: Dict[str, Any]) -> str:
        return f"{doc.get('title', '')} {doc.get('document_type', '')} {doc.get('summary', '')} {doc.get('taxonomy', [])}".lower()
    def document_identity(doc: Dict[str, Any]) -> str:
        return f"{doc.get('title', '')} {doc.get('document_type', '')}".lower()
    def is_validation_document(doc: Dict[str, Any]) -> bool:
        text = document_identity(doc)
        return any(term in text for term in hard_validation_terms)
    content_docs = [
        doc for doc in selected_docs
        if any(term in document_identity(doc) for term in content_terms) and not is_validation_document(doc)
    ]
    validation_docs = [
        doc for doc in selected_docs
        if doc not in content_docs and is_validation_document(doc)
    ]
    if not content_docs:
        content_docs = selected_docs[:4]
    if not validation_docs:
        validation_docs = [doc for doc in selected_docs if doc not in content_docs] or selected_docs[:4]
    owner_by_category = {
        "Planning": "Workflow owner",
        "Segmentation": "Commercial operations",
        "Claims": "Claims governance lead",
        "Evidence": "Medical reviewer",
        "Regulatory": "Regulatory reviewer",
        "Safety": "Medical reviewer",
        "Policy": "Compliance reviewer",
        "Legal": "Legal reviewer",
        "Approval": "Approval owner",
        "DAM": "Content operations",
        "QA": "QA specialist",
        "Litmus": "QA specialist",
        "Consent": "CRM operations",
        "Audience": "CRM operations",
        "Market": "Local market reviewer",
        "Disclosure": "Local market reviewer",
        "Audit": "Audit owner",
    }
    step_lines = []
    for step in run_data.get("steps", [])[:8]:
        score = int(step.get("score", 0))
        missing_area = "None identified" if score >= 88 else "Critical source or mandatory control gap" if score < 80 else "Reviewer confirmation required"
        improvement = step.get("suggested_fix") or ("Approve and retain evidence" if score >= 88 else "Revise content, attach missing evidence, and rerun this test")
        kpi_text = "; ".join(f"{key}: {value}" for key, value in step.get("kpis", {}).items()) or "KPI pending"
        owner = owner_by_category.get(step.get("category", ""), "Stage owner")
        step_lines.append(
            f"| {step.get('name', 'Validation step')} | {kpi_text} | {score}% | {missing_area} | {improvement} | {owner} |"
        )
    content_lines = [
        f"- {doc.get('id', 'DOC')}: {doc.get('title', 'Content file')} ({doc.get('document_type', 'content')}, {doc.get('version', 'current')})"
        for doc in content_docs[:10]
    ]
    validation_lines = [
        f"- {doc.get('id', 'DOC')}: {doc.get('title', 'Validation file')} ({doc.get('document_type', 'validation')}, {doc.get('version', 'current')})"
        for doc in validation_docs[:10]
    ]
    action_lines = [
        f"- {owner_by_category.get(step.get('category', ''), 'Stage owner')}: "
        f"{'No action beyond evidence retention' if int(step.get('score', 0)) >= 88 else step.get('suggested_fix') or step.get('summary', 'Review and close the validation gap.')}"
        for step in run_data.get("steps", [])[:8]
    ]
    content = output_text.strip() or (
        f"Output Validation Report\n"
        f"- Stage: {stage['name']}\n"
        f"- Asset: {stage.get('asset_id', '')}\n"
        f"- Content type: {stage.get('content_type', 'Regulated content package')}\n"
        f"- Audit ID: {run_data.get('audit_id', f'AUD-{len(AUDIT_EVENTS) + 1:03d}')}\n\n"
        f"Executive readout\n"
        f"- The validation run checked whether this stage output is ready to move forward without weakening claim integrity, source lineage, local-market compliance, or channel readiness.\n"
        f"- The final gate signal is intentionally shown after this report, so reviewers read the evidence before acting on the decision.\n"
        f"- Current validation score: {run_data.get('stage_score', stage.get('validation_score'))}%.\n\n"
        f"Objective\n"
        f"- Confirm that the stage output is accurate, source-grounded, compliant, and operationally ready for the next authorization gate.\n\n"
        f"Goal\n"
        f"- Give reviewers a clear decision record: what was checked, which files were used, where gaps remain, who owns each action, and what must happen before progression.\n\n"
        f"Inputs reviewed\n"
        f"- Content files and validation files were treated as separate evidence groups. The content files are the material under review; the validation files are the independent control references.\n\n"
        f"Content files considered\n"
        f"{chr(10).join(content_lines) if content_lines else '- No content files attached.'}\n\n"
        f"Validation files considered\n"
        f"{chr(10).join(validation_lines) if validation_lines else '- No validation files attached.'}\n\n"
        f"Validation analysis\n"
        f"| Test | KPIs | Score | Gap | Improvement | Owner |\n"
        f"| --- | --- | --- | --- | --- | --- |\n"
        f"{chr(10).join(step_lines) if step_lines else '| Validation run | KPI pending | 0% | Rule-engine run pending | Run validations | Stage owner |'}\n\n"
        f"Output reviewed\n"
        f"{blueprint}\n\n"
        f"Action plan by owner\n"
        f"{chr(10).join(action_lines) if action_lines else '- Stage owner: Run validation and capture reviewer action.'}\n\n"
        f"Reviewer guidance\n"
        f"- Read the validation analysis first, close any listed gap, then use the final decision card below this report to decide whether the stage can move forward.\n"
        f"- If any source bundle changes after this report is generated, rerun validation before submitting the stage.\n\n"
        f"Conclusion\n"
        f"- This is the controlled output validation report for the stage. It should travel with the brief, generated content, validation pack, and audit record.\n"
        f"- Progress only after the accountable owners close critical gaps, reviewer comments are captured, and the source bundle remains unchanged."
    )
    output = {
        "id": output_id,
        "stage_id": stage["id"],
        "stage": stage["name"],
        "title": f"Stage {stage['order']} Output Validation Report",
        "document_type": "Output Validation Report",
        "version": f"v{stage['order']}.0",
        "status": "generated",
        "created_by": USERS.get(normalize_email(actor_email), {}).get("name", "MedGuard"),
        "created_at": now_ist(),
        "content": content,
        "next_stage_id": next_stage_id(stage["id"]),
        "audit_id": run_data.get("audit_id", f"AUD-{len(AUDIT_EVENTS) + 1:03d}"),
        "source_documents": [doc["id"] for doc in selected_docs],
    }
    STAGE_OUTPUT_DOCUMENTS[output_id] = output
    return output

def next_stage_id(stage_id: str) -> str:
    ordered = sorted(ORCHESTRATION_STAGES, key=lambda item: item["order"])
    for index, stage in enumerate(ordered):
        if stage["id"] == stage_id and index + 1 < len(ordered):
            return ordered[index + 1]["id"]
    return ""

def normalize_engine_status(score: int, step: Dict[str, Any]) -> str:
    if score < 80 and step.get("critical"):
        return "blocked"
    if score < 88:
        return "rework"
    return "passed"

def static_rule_result(stage: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
    score = int(step.get("static_score", stage.get("score", 88)))
    status = normalize_engine_status(score, step)
    findings = []
    if status == "blocked":
        findings.append(f"Critical blocker in {step['name']}: reviewer action required before progression.")
    elif status == "rework":
        findings.append(f"{step['name']} is below target and needs reviewer confirmation or revision.")
    else:
        findings.append(f"{step['name']} passed static policy and source checks.")
    return {
        "score": score,
        "status": status,
        "summary": findings[0],
        "findings": findings,
        "risk_flags": [] if status == "passed" else [step["name"]],
        "suggested_fix": "Approve and continue." if status == "passed" else f"Resolve {step['name'].lower()} before stage approval.",
        "confidence": min(98, max(72, score + 2)),
    }

def parse_gemini_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).replace("JSON\n", "", 1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)

def gemini_rule_result(stage: Dict[str, Any], step: Dict[str, Any], fallback: Dict[str, Any], use_gemini: bool, model_profile: str = "balanced") -> Dict[str, Any]:
    profile = AI_MODEL_PROFILES.get(model_profile, AI_MODEL_PROFILES["balanced"])
    if not use_gemini or client is None:
        return {**fallback, "model_used": "static-rule-engine", "mode": "rules", "model_profile": profile}
    prompt = f"""
You are validating regulated pharmaceutical content inside MedGuard.
Return only JSON with keys: score, status, summary, findings, risk_flags, suggested_fix, confidence.
Allowed status values: passed, rework, blocked.

Stage: {stage['name']}
Asset: {stage.get('asset_id')}
Market: {stage.get('market')}
Channel: {stage.get('channel')}
Step: {step['name']}
Purpose: {RULE_ENGINE_STAGES[stage['id']]['purpose']}
Mandatory: {step.get('mandatory')}
Critical: {step.get('critical')}
Static rules: {', '.join(step.get('static_rules', []))}
Sources: {', '.join(step.get('source_refs', []))}
Inputs: {json.dumps(stage.get('inputs', []))}
Existing checks: {json.dumps(stage.get('validation_checks', []) + stage.get('regulatory_checks', []) + stage.get('claim_verifiers', []) + stage.get('security_checks', []))}
Use conservative pharma compliance judgment. Any critical blocker should be blocked.
Model profile: {profile['label']} — {profile['detail']}
"""
    try:
        parts: List[Any] = [prompt]
        mode = "gemini-text"
        if step.get("media_required"):
            tiny_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
            parts = [
                prompt + f"\nMedia metadata: {json.dumps(stage_media(stage['id']))}",
                types.Part.from_bytes(data=tiny_png, mime_type="image/png"),
            ]
            mode = "gemini-multimodal"
        response = client.models.generate_content(
            model=profile.get("model", GEMINI_MODEL),
            contents=parts,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
        )
        parsed = parse_gemini_json(getattr(response, "text", "") or "{}")
        score = int(parsed.get("score", fallback["score"]))
        status = parsed.get("status") if parsed.get("status") in {"passed", "rework", "blocked"} else normalize_engine_status(score, step)
        return {
            "score": score,
            "status": status,
            "summary": parsed.get("summary") or fallback["summary"],
            "findings": parsed.get("findings") if isinstance(parsed.get("findings"), list) else fallback["findings"],
            "risk_flags": parsed.get("risk_flags") if isinstance(parsed.get("risk_flags"), list) else fallback["risk_flags"],
            "suggested_fix": parsed.get("suggested_fix") or fallback["suggested_fix"],
            "confidence": max(1, min(99, int(parsed.get("confidence", fallback["confidence"])) + int(profile.get("confidence_bias", 0)))),
            "model_used": profile.get("model", GEMINI_MODEL),
            "model_profile": profile,
            "mode": mode,
        }
    except Exception as exc:
        return {
            **fallback,
            "model_used": "static-rule-engine",
            "model_profile": profile,
            "mode": "gemini-fallback",
            "summary": f"{fallback['summary']} Gemini check was unavailable, so the static rule result was used.",
            "engine_error": exc.__class__.__name__,
        }

def build_rule_engine_run(stage_id: str, actor_email: str = "", content_id: str = "AST-RESP-EMAIL-042", use_gemini: bool = True, model_profile: str = "balanced", bundle_id: str = "", action_context: str = "") -> Dict[str, Any]:
    stage = stage_by_id(stage_id)
    definition = rule_stage(stage_id)
    if not stage or not definition:
        raise HTTPException(status_code=404, detail="AI Compliance Engine is available for configured workflow stages only.")
    model_profile = STAGE_MODEL_PROFILE.get(stage_id, "balanced") if model_profile in {"", "auto"} else model_profile
    steps = []
    blockers: List[str] = []
    risk_flags: List[str] = []
    weighted_total = 0
    weight_sum = 0
    mandatory_passed = 0
    for index, step in enumerate(definition["steps"]):
        fallback = static_rule_result(stage, step)
        result = gemini_rule_result(stage, step, fallback, use_gemini, model_profile)
        score = int(result["score"])
        status = result["status"]
        if status == "passed" and step.get("mandatory"):
            mandatory_passed += 1
        if status == "blocked":
            blockers.append(step["name"])
        risk_flags.extend(result.get("risk_flags", []))
        weight = int(step.get("weight", 10))
        weighted_total += score * weight
        weight_sum += weight
        steps.append({
            "id": step["id"],
            "order": index + 1,
            "name": step["name"],
            "category": step["category"],
            "mandatory": step.get("mandatory", True),
            "critical": step.get("critical", False),
            "status": status,
            "score": score,
            "progress": 100 if status == "passed" else 72 if status == "rework" else 58,
            "summary": result["summary"],
            "findings": result.get("findings", []),
            "risk_flags": result.get("risk_flags", []),
            "suggested_fix": result.get("suggested_fix", ""),
            "confidence": result.get("confidence", score),
            "model_used": result.get("model_used", "static-rule-engine"),
            "model_profile": result.get("model_profile", AI_MODEL_PROFILES.get(model_profile, AI_MODEL_PROFILES["balanced"])),
            "mode": result.get("mode", "rules"),
            "source_refs": step.get("source_refs", []),
            "static_rules": step.get("static_rules", []),
            "kpis": step.get("kpis", {}),
            "human_approval": {"status": "pending", "actor": "", "reason": "", "timestamp": ""},
            "started_at": now_ist(),
            "completed_at": now_ist(),
        })
    stage_score = round(weighted_total / max(weight_sum, 1))
    if blockers:
        status = "BLOCK"
    elif stage_score >= definition["threshold"] and mandatory_passed == len(definition["steps"]):
        status = "PASS"
    else:
        status = "REWORK"
    audit_id = f"AUD-{len(AUDIT_EVENTS) + 1:03d}"
    run_id = f"RUN-{stage_id.upper()}-{len(RULE_ENGINE_RUNS) + 1:04d}"
    notification = {
        "id": f"NTF-{len(NOTIFICATIONS) + 1:03d}",
        "stage_id": stage_id,
        "stage": stage["name"],
        "title": "Approval required" if status != "PASS" else "Stage ready for approval",
        "message": f"{stage['name']} completed with {stage_score}% score and {len(blockers)} blocker(s).",
        "severity": "high" if status == "BLOCK" else "medium" if status == "REWORK" else "low",
        "timestamp": now_ist(),
        "read": False,
    }
    actor_user = USERS.get(normalize_email(actor_email), {})
    event = {
        "id": audit_id,
        "stage": stage["name"],
        "trigger": stage["trigger"],
        "severity": notification["severity"],
        "source_system": stage["system"],
        "asset_id": stage.get("asset_id", content_id),
        "actor": actor_user.get("name", "AI validation layer"),
        "actor_id": actor_user.get("id", "SYSTEM"),
        "actor_email": actor_user.get("email", actor_email),
        "action": "Rule engine execution",
        "agent_output": f"{len(steps)} checks executed; score {stage_score}%; status {status}",
        "decision": f"Rule engine returned {status}",
        "reviewer": "Pending human approval",
        "reason": "Mandatory stage-gate validation",
        "timestamp": now_ist(),
        "final_recommendation": "Approve and continue" if status == "PASS" else "Human review required",
        "before": "Stage awaiting rule execution",
        "after": status,
        "evidence_links": sorted({source for step in steps for source in step["source_refs"]}),
        "model_trace": [{"step": step["name"], "model": step["model_used"], "mode": step["mode"], "status": step["status"]} for step in steps],
    }
    run = {
        "run_id": run_id,
        "content_id": content_id,
        "bundle_id": bundle_id,
        "stage_id": stage_id,
        "stage": stage["name"],
        "purpose": definition["purpose"],
        "threshold": definition["threshold"],
        "stage_score": stage_score,
        "status": status,
        "mandatory_checks_passed": mandatory_passed,
        "mandatory_checks_total": len(definition["steps"]),
        "critical_blockers": blockers,
        "risk_flags": sorted(set(risk_flags)),
        "kpis": {key: value for step in steps for key, value in step.get("kpis", {}).items()},
        "reviewer_action_required": True,
        "audit_id": audit_id,
        "steps": steps,
        "media": stage_media(stage_id),
        "selected_documents": bundle_documents(bundle_id) if bundle_id else stage_documents(stage_id),
        "model_profile": AI_MODEL_PROFILES.get(model_profile, AI_MODEL_PROFILES["balanced"]),
        "action_context": action_context,
        "notification": notification,
        "approval": {"status": "pending", "actor": "", "reason": "", "timestamp": ""},
    }
    RULE_ENGINE_RUNS[run_id] = run
    stage["last_rule_run"] = run
    stage["validation_score"] = stage_score
    stage["score"] = stage_score
    stage["status"] = "blocked" if status == "BLOCK" else "attention" if status == "REWORK" else "ready"
    stage["risk"] = "high" if status == "BLOCK" else "medium" if status == "REWORK" else "low"
    stage["last_validation"] = {
        "stage_id": stage_id,
        "risk_score": 100 - stage_score,
        "validation_score": stage_score,
        "decision": status,
        "findings": [{"name": name, "status": "blocked", "detail": "Critical blocker"} for name in blockers],
        "recommended_action": run["approval"]["status"],
        "suggested_fixes": [step["suggested_fix"] for step in steps if step["status"] != "passed"][:4],
        "trace": event["model_trace"],
        "sources": stage.get("sources", []),
    }
    NOTIFICATIONS.insert(0, notification)
    AUDIT_EVENTS.insert(0, event)
    return run

def record_rule_approval(body: StepApprovalRequest) -> Dict[str, Any]:
    actor = USERS.get(normalize_email(body.actor_email))
    if not actor or actor["status"] != "active":
        raise HTTPException(status_code=403, detail="Active reviewer required.")
    stage = stage_by_id(body.stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found.")
    if body.action in {"request_changes", "override"} and not body.reason.strip():
        raise HTTPException(status_code=400, detail="Reason is required.")
    latest_run = next((run for run in RULE_ENGINE_RUNS.values() if run["stage_id"] == body.stage_id), None)
    approval = {
        "id": f"APR-{len(APPROVAL_TRACKER) + 1:03d}",
        "stage_id": body.stage_id,
        "stage": stage["name"],
        "step_id": body.step_id,
        "action": body.action,
        "reason": body.reason.strip(),
        "reason_code": body.reason_code,
        "affected_rule": body.affected_rule or body.step_id,
        "actor": actor["name"],
        "actor_email": actor["email"],
        "timestamp": now_ist(),
    }
    if latest_run:
        if body.step_id == "overall":
            latest_run["approval"] = {"status": body.action, "actor": actor["name"], "reason": body.reason, "timestamp": approval["timestamp"]}
        for step in latest_run["steps"]:
            if step["id"] == body.step_id:
                step["human_approval"] = {"status": body.action, "actor": actor["name"], "reason": body.reason, "timestamp": approval["timestamp"]}
    APPROVAL_TRACKER.insert(0, approval)
    AUDIT_EVENTS.insert(0, {
        "id": f"AUD-{len(AUDIT_EVENTS) + 1:03d}",
        "stage": stage["name"],
        "trigger": stage["trigger"],
        "severity": "medium" if body.action != "approve" else "low",
        "source_system": stage["system"],
        "asset_id": stage.get("asset_id", "AST-RESP-EMAIL-042"),
        "actor": actor["name"],
        "actor_id": actor["id"],
        "actor_email": actor["email"],
        "action": "Human approval captured",
        "agent_output": f"{body.step_id} decision captured",
        "decision": body.action,
        "reviewer": actor["name"],
        "reason": body.reason or body.reason_code,
        "timestamp": approval["timestamp"],
        "final_recommendation": "Proceed" if body.action == "approve" else "Rework / exception captured",
        "evidence_links": [body.affected_rule or body.step_id],
        "model_trace": latest_run.get("steps", []) if latest_run else [],
    })
    return approval

def apply_audit_filters(events: List[Dict[str, Any]], filters: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    result = events
    for key, value in filters.items():
        if not value:
            continue
        needle = value.lower()
        if key == "q":
            result = [event for event in result if needle in json.dumps(event).lower()]
        elif key == "actor":
            result = [
                event for event in result
                if needle in str(event.get("actor_id", "")).lower()
                or needle in str(event.get("actor_email", "")).lower()
                or needle in str(event.get("actor", "")).lower()
                or needle in str(event.get("reviewer", "")).lower()
            ]
        else:
            result = [event for event in result if needle in str(event.get(key, "")).lower()]
    return result

@app.get("/api/auth/personas")
async def get_auth_personas():
    return JSONResponse([public_user(user) for user in USERS.values()])

@app.post("/api/auth/login")
async def login(body: LoginRequest):
    email = normalize_email(body.email)
    user = USERS.get(email)
    if not user or user["password"] != body.password.strip():
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if user["status"] != "active":
        raise HTTPException(status_code=403, detail="This user is inactive.")
    user["last_login"] = "2026-04-30 13:45 IST"
    return JSONResponse({"token": f"session-token-{user['id']}", "user": public_user(user)})

def sso_provider_config(provider: str) -> Dict[str, str]:
    key = provider.lower()
    if key == "google":
        return {
            "provider": "google",
            "name": "Google",
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/sso/google/callback"),
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "scope": "openid email profile",
        }
    if key in {"microsoft", "ms"}:
        tenant = os.getenv("MICROSOFT_TENANT_ID", "common")
        return {
            "provider": "microsoft",
            "name": "Microsoft",
            "client_id": os.getenv("MICROSOFT_CLIENT_ID", ""),
            "client_secret": os.getenv("MICROSOFT_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("MICROSOFT_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/sso/microsoft/callback"),
            "authorize_url": f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            "token_url": f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
            "scope": "openid email profile User.Read",
        }
    raise HTTPException(status_code=404, detail="Unsupported SSO provider.")

def require_sso_config(config: Dict[str, str]) -> None:
    if not config["client_id"] or not config["client_secret"]:
        prefix = "GOOGLE" if config["provider"] == "google" else "MICROSOFT"
        raise HTTPException(
            status_code=503,
            detail=f"{config['name']} SSO is not configured. Add {prefix}_CLIENT_ID and {prefix}_CLIENT_SECRET to the backend environment.",
        )

def exchange_oauth_payload(url: str, payload: Dict[str, str], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"SSO token exchange failed: {detail[:280]}") from error

def fetch_oidc_userinfo(url: str, access_token: str) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"SSO profile lookup failed: {detail[:280]}") from error

def user_from_sso_profile(provider: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    email = normalize_email(profile.get("email") or profile.get("preferred_username") or profile.get("upn") or "")
    if not email:
        raise HTTPException(status_code=400, detail="SSO profile did not include an email address.")
    user = USERS.get(email)
    if not user:
        user = {
            "id": next_user_id(),
            "name": profile.get("name") or email.split("@")[0].replace(".", " ").title(),
            "email": email,
            "password": "",
            "role": "workflow_owner",
            "persona": f"{provider.title()} SSO user",
            "team": "Global Content Governance",
            "status": "active",
            "modules": ROLE_MODULES["workflow_owner"],
            "last_login": "Never",
        }
        USERS[email] = user
    if user["status"] != "active":
        raise HTTPException(status_code=403, detail="This SSO user is inactive.")
    user["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    return user

@app.get("/api/auth/sso/{provider}/start")
async def start_sso(provider: str):
    config = sso_provider_config(provider)
    require_sso_config(config)
    state = secrets.token_urlsafe(24)
    SSO_STATE_STORE[state] = {"provider": config["provider"], "created_at": time.time()}
    query = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": config["scope"],
        "state": state,
        "prompt": "select_account",
    }
    return JSONResponse({"provider": config["provider"], "authorization_url": f"{config['authorize_url']}?{urllib.parse.urlencode(query)}"})

@app.get("/api/auth/sso/{provider}/callback")
async def finish_sso(provider: str, code: str = "", state: str = "", error: str = "", error_description: str = ""):
    config = sso_provider_config(provider)
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/console?sso_error={urllib.parse.quote(error_description or error)}")
    state_record = SSO_STATE_STORE.pop(state, None)
    if not state_record or state_record["provider"] != config["provider"] or time.time() - state_record["created_at"] > 600:
        return RedirectResponse(f"{FRONTEND_URL}/console?sso_error={urllib.parse.quote('Invalid or expired SSO state.')}")
    if not code:
        return RedirectResponse(f"{FRONTEND_URL}/console?sso_error={urllib.parse.quote('Missing SSO authorization code.')}")
    require_sso_config(config)
    token = exchange_oauth_payload(config["token_url"], {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "code": code,
        "redirect_uri": config["redirect_uri"],
        "grant_type": "authorization_code",
    })
    access_token = token.get("access_token")
    if not access_token:
        return RedirectResponse(f"{FRONTEND_URL}/console?sso_error={urllib.parse.quote('SSO token response did not include an access token.')}")
    profile = fetch_oidc_userinfo(config["userinfo_url"], access_token)
    user = user_from_sso_profile(config["provider"], profile)
    session = {
        "token": f"sso-token-{config['provider']}-{user['id']}-{secrets.token_urlsafe(8)}",
        "user": public_user(user),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(session).encode("utf-8")).decode("ascii").rstrip("=")
    return RedirectResponse(f"{FRONTEND_URL}/console?sso_session={encoded}")

@app.get("/api/users")
async def list_users(actor_email: Optional[str] = None):
    actor = require_admin(actor_email or "")
    include_password = actor["role"] == "super_admin"
    return JSONResponse([public_user(user, include_password=include_password) for user in USERS.values()])

@app.post("/api/users")
async def create_managed_user(body: ManagedUserCreateRequest):
    actor = require_admin(body.actor_email)
    if body.role == "super_admin" and actor["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Only a super admin can create super admins.")
    email = normalize_email(body.email)
    if email in USERS:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    modules = body.modules or ROLE_MODULES.get(body.role, ROLE_MODULES["user"])
    user = {
        "id": next_user_id(),
        "name": body.name.strip(),
        "email": email,
        "password": body.password or DEMO_PASSWORD,
        "role": body.role,
        "persona": body.persona.strip() or "Content operations user",
        "team": body.team.strip() or "Content Operations",
        "status": "active",
        "modules": ALL_PRODUCT_MODULES if body.role == "super_admin" else modules,
        "last_login": "Never",
    }
    USERS[email] = user
    return JSONResponse(public_user(user))

@app.post("/api/users/{user_id}/password")
async def update_user_password(user_id: str, body: PasswordUpdateRequest):
    actor = require_admin(body.actor_email)
    target = find_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if not can_manage_target(actor, target):
        raise HTTPException(status_code=403, detail="Only a super admin can manage another super admin.")
    target["password"] = body.password
    return JSONResponse({"status": "updated", "user": public_user(target)})

@app.post("/api/users/{user_id}/password/reset")
async def reset_user_password(user_id: str, body: ActorRequest):
    actor = require_admin(body.actor_email)
    if actor["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Only a super admin can reset demo passwords.")
    target = find_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    target["password"] = DEMO_PASSWORD
    return JSONResponse({"status": "updated", "password": DEMO_PASSWORD, "user": public_user(target, include_password=True)})

@app.post("/api/users/{user_id}/status")
async def update_user_status(user_id: str, body: StatusUpdateRequest):
    actor = require_admin(body.actor_email)
    target = find_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if not can_manage_target(actor, target):
        raise HTTPException(status_code=403, detail="Only a super admin can manage another super admin.")
    if target["email"] == actor["email"] and body.status == "inactive":
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    target["status"] = body.status
    return JSONResponse(public_user(target))

@app.post("/api/users/{user_id}/access")
async def update_user_access(user_id: str, body: UserAccessUpdateRequest):
    actor = require_admin(body.actor_email)
    if actor["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Only a super admin can change access.")
    target = find_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target["email"] == actor["email"] and body.role != "super_admin":
        raise HTTPException(status_code=400, detail="You cannot downgrade your own super admin role.")
    target["role"] = body.role
    target["modules"] = ALL_PRODUCT_MODULES if body.role == "super_admin" else (body.modules or ROLE_MODULES.get(body.role, target.get("modules", [])))
    target["team"] = body.team.strip() or target["team"]
    target["persona"] = body.persona.strip() or target["persona"]
    return JSONResponse(public_user(target, include_password=actor["role"] == "super_admin"))

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str, actor_email: str):
    actor = require_admin(actor_email)
    if actor["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Only a super admin can delete users.")
    target = find_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target["email"] == actor["email"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")
    del USERS[target["email"]]
    return JSONResponse({"status": "deleted", "user_id": user_id})

@app.post("/api/profile/password")
async def update_profile_password(body: ProfilePasswordUpdateRequest):
    user = USERS.get(normalize_email(body.email))
    if not user or user["status"] != "active":
        raise HTTPException(status_code=403, detail="Active user required.")
    if user["password"] != body.current_password.strip():
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    user["password"] = body.new_password.strip()
    return JSONResponse({"status": "updated"})

@app.get("/api/dashboard/overview")
async def get_dashboard_overview(
    markets: str = "",
    brands: str = "",
    content_types: str = "",
    risks: str = "",
    channels: str = "",
    date_range: str = "",
):
    return JSONResponse(dashboard_overview(markets, brands, content_types, risks, channels, date_range))

@app.get("/api/ai-models")
async def get_ai_models():
    return JSONResponse(list(AI_MODEL_PROFILES.values()))

@app.get("/api/documents/search")
async def get_documents_search(
    q: str = "",
    brand: str = "",
    document_type: str = "",
    region: str = "",
    market: str = "",
    channel: str = "",
    approval_status: str = "",
    source_id: str = "",
    stage_id: str = "",
):
    documents = search_documents(q, brand, document_type, region, market, channel, approval_status, source_id, stage_id)
    facets = {
        "sources": DOCUMENT_SOURCES,
        "brands": [FIXED_BRAND],
        "document_types": sorted({doc["document_type"] for doc in LIBRARY_DOCUMENTS}),
        "regions": [FIXED_MARKET],
        "markets": [FIXED_MARKET],
        "channels": FIXED_CHANNELS,
        "approval_statuses": sorted({doc["approval_status"] for doc in LIBRARY_DOCUMENTS}),
    }
    return JSONResponse({"documents": documents, "facets": facets, "total": len(documents)})

@app.get("/api/documents/detail/{document_id}")
async def get_document(document_id: str):
    document = document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    related = [doc for doc in LIBRARY_DOCUMENTS if doc["id"] != document_id and (doc["brand"] == document["brand"] or set(doc.get("stage_ids", [])).intersection(document.get("stage_ids", [])))][:5]
    return JSONResponse({"document": document, "related": related})

@app.post("/api/documents/compare")
async def compare_documents(body: DocumentCompareRequest):
    docs = [document for document in LIBRARY_DOCUMENTS if document["id"] in body.document_ids]
    if len(docs) < 2:
        raise HTTPException(status_code=400, detail="Select at least two documents to compare.")
    comparison = {
        "documents": docs,
        "shared_taxonomy": sorted(set.intersection(*(set(doc.get("taxonomy", [])) for doc in docs))) if docs else [],
        "conflicts": [
            "Approval status differs across selected documents." if len({doc["approval_status"] for doc in docs}) > 1 else "",
            "Selected packet includes multiple markets; local overlay review required." if len({doc["market"] for doc in docs}) > 1 else "",
        ],
        "recommendation": "Create a controlled input bundle and route to the selected stage engine.",
    }
    comparison["conflicts"] = [item for item in comparison["conflicts"] if item]
    return JSONResponse(comparison)

@app.get("/api/documents/{document_id}")
async def get_document_by_short_path(document_id: str):
    return await get_document(document_id)

@app.post("/api/input-bundles")
async def create_input_bundle(body: InputBundleRequest):
    actor = USERS.get(normalize_email(body.actor_email)) if body.actor_email else None
    if actor and not can_access_stage(actor, body.stage_id, write=True):
        raise HTTPException(status_code=403, detail="Your role cannot create a bundle for this stage.")
    documents = [document for document in LIBRARY_DOCUMENTS if document["id"] in body.document_ids]
    if not documents:
        raise HTTPException(status_code=400, detail="Select at least one source document.")
    if body.stage_id == "briefing":
        selected_brands = {doc["brand"] for doc in documents if doc.get("brand") and doc["brand"] != "All Brands"}
        linked_docs = [
            document for document in LIBRARY_DOCUMENTS
            if (
                document["id"] in {doc["id"] for doc in documents}
                or (document.get("brand") in selected_brands and document.get("approval_status") == "approved")
                or (document.get("brand") == "All Brands" and document.get("approval_status") == "approved")
            )
        ]
        documents = linked_docs or documents
    bundle_id = f"BND-{len(INPUT_BUNDLES) + 1:04d}"
    bundle = {
        "id": bundle_id,
        "name": body.name.strip(),
        "stage_id": body.stage_id,
        "document_ids": [doc["id"] for doc in documents],
        "documents": documents,
        "taxonomy": sorted({tag for doc in documents for tag in doc.get("taxonomy", [])}),
        "approval_status": "ready" if all(doc["approval_status"] == "approved" for doc in documents) else "needs_review",
        "created_by": actor["name"] if actor else "MedGuard",
        "created_at": now_ist(),
        "notes": body.notes,
    }
    INPUT_BUNDLES[bundle_id] = bundle
    AUDIT_EVENTS.insert(0, {
        "id": f"AUD-{len(AUDIT_EVENTS) + 1:03d}",
        "stage": stage_by_id(body.stage_id)["name"] if stage_by_id(body.stage_id) else body.stage_id,
        "trigger": "Document source selection",
        "severity": "low" if bundle["approval_status"] == "ready" else "medium",
        "source_system": "MedGuard Document Library",
        "asset_id": bundle_id,
        "actor": bundle["created_by"],
        "actor_id": actor.get("id", "SYSTEM") if actor else "SYSTEM",
        "actor_email": actor.get("email", body.actor_email) if actor else body.actor_email,
        "action": "Input bundle created",
        "agent_output": f"{len(documents)} document(s) selected using IMCP taxonomy.",
        "decision": bundle["approval_status"],
        "reviewer": bundle["created_by"],
        "reason": body.notes or "Source bundle prepared for AI validation.",
        "timestamp": bundle["created_at"],
        "final_recommendation": "Run stage engine",
        "evidence_links": [doc["id"] for doc in documents],
    })
    return JSONResponse(bundle)

@app.get("/api/input-bundles/{bundle_id}")
async def get_input_bundle(bundle_id: str):
    bundle = INPUT_BUNDLES.get(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Input bundle not found.")
    return JSONResponse(bundle)

@app.get("/api/stage-outputs")
async def get_stage_outputs(stage_id: str = ""):
    outputs = list(STAGE_OUTPUT_DOCUMENTS.values())
    if stage_id:
        outputs = [output for output in outputs if output["stage_id"] == stage_id]
    return JSONResponse(outputs)

@app.get("/api/orchestration/stages")
async def get_orchestration_stages():
    return JSONResponse(ORCHESTRATION_STAGES)

@app.post("/api/orchestration/run")
async def run_orchestration(body: Dict[str, Any]):
    stage_id = body.get("stage_id")
    stage = next((item for item in ORCHESTRATION_STAGES if item["id"] == stage_id), ORCHESTRATION_STAGES[0])
    actor = USERS.get(normalize_email(body.get("actor_email", ""))) if body.get("actor_email") else None
    if actor and not can_access_stage(actor, stage["id"], write=True):
        raise HTTPException(status_code=403, detail="Your role does not have write access to this stage.")
    rule_run = None
    if stage["id"] in RULE_ENGINE_STAGES:
        rule_run = build_rule_engine_run(
            stage["id"],
            body.get("actor_email", ""),
            stage.get("asset_id", body.get("content_id", "AST-RESP-EMAIL-042")),
            bool(body.get("use_gemini", True)),
            body.get("model_profile", "balanced"),
            body.get("bundle_id", ""),
            body.get("action_context", ""),
        )
    validation = build_stage_validation(stage)
    event = {
        "id": f"AUD-{len(AUDIT_EVENTS) + 1:03d}",
        "stage": stage["name"],
        "trigger": stage["trigger"],
        "severity": "high" if validation["decision"] == "ESCALATE" else "medium" if validation["decision"] == "REWORK" else "low",
        "source_system": stage["system"],
        "asset_id": stage.get("asset_id", "AST-RESP-EMAIL-042"),
        "actor": actor.get("name", "AI validation layer") if actor else "AI validation layer",
        "actor_id": actor.get("id", "SYSTEM") if actor else "SYSTEM",
        "actor_email": actor.get("email", body.get("actor_email", "")) if actor else body.get("actor_email", ""),
        "action": "Stage validation run",
        "agent_output": f"{stage['score']}% validation score; {len(validation['findings'])} finding(s)",
        "decision": f"Validation returned {validation['decision']}",
        "reviewer": "AI validation layer",
        "reason": "Stage trigger received from connected system",
        "timestamp": "2026-05-04 09:55 IST",
        "final_recommendation": stage["recommendation"],
        "before": "Stage awaiting validation",
        "after": validation["decision"],
        "evidence_links": [source["id"] for source in stage.get("sources", [])],
        "model_trace": validation["trace"],
    }
    AUDIT_EVENTS.insert(0, event)
    stage["last_validation"] = validation
    stage["audit_events"] = [event] + stage.get("audit_events", [])[:4]
    output_document = build_stage_output(stage, rule_run, body.get("actor_email", ""), body.get("output_text", ""))
    stage["stage_output_document"] = output_document
    if output_document.get("next_stage_id"):
        next_stage = stage_by_id(output_document["next_stage_id"])
        if next_stage:
            next_stage.setdefault("inputs", []).insert(0, {"name": output_document["title"], "value": output_document["version"], "source": "MedGuard Stage Output"})
            next_stage.setdefault("available_documents", []).append(output_document["id"])
    return JSONResponse({"status": "completed", "stage": stage, "validation": validation, "rule_engine": rule_run, "audit_event": event, "output_document": output_document, "dashboard": dashboard_overview()})

@app.post("/api/orchestration/decision")
async def record_orchestration_decision(body: DecisionRequest):
    actor = USERS.get(normalize_email(body.actor_email))
    if not actor or actor["status"] != "active":
        raise HTTPException(status_code=403, detail="Active reviewer required.")
    stage = next((item for item in ORCHESTRATION_STAGES if item["id"] == body.stage_id), None)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found.")
    if body.action == "override" and not body.reason.strip():
        raise HTTPException(status_code=400, detail="Override reason is required.")
    decision = "Reviewer accepted AI recommendation" if body.action == "accept" else "Reviewer overrode AI recommendation"
    event = {
        "id": f"AUD-{len(AUDIT_EVENTS) + 1:03d}",
        "stage": stage["name"],
        "trigger": stage["trigger"],
        "severity": "medium" if body.action == "override" else "low",
        "source_system": stage["system"],
        "asset_id": stage.get("asset_id", "AST-RESP-EMAIL-042"),
        "actor": actor["name"],
        "actor_id": actor["id"],
        "actor_email": actor["email"],
        "action": "Reviewer decision",
        "agent_output": f"{stage['score']}% score; {stage['risk'].upper()} risk",
        "decision": decision,
        "reviewer": actor["name"],
        "reason": body.reason.strip() or "Accepted recommendation",
        "timestamp": "2026-05-04 10:02 IST",
        "final_recommendation": stage["recommendation"],
        "before": "AI recommendation pending",
        "after": decision,
        "evidence_links": [source["id"] for source in stage.get("sources", [])],
        "model_trace": stage.get("agent_trace", []),
    }
    AUDIT_EVENTS.insert(0, event)
    return JSONResponse({"status": "captured", "event": event})

@app.post("/api/workflow/actions")
async def record_workflow_action(body: WorkflowActionRequest):
    actor = USERS.get(normalize_email(body.actor_email))
    if not actor or actor["status"] != "active":
        raise HTTPException(status_code=403, detail="Active user required.")
    if not can_access_stage(actor, body.stage_id, write=True):
        raise HTTPException(status_code=403, detail="Your role cannot action this stage.")
    stage = stage_by_id(body.stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found.")
    if body.action_type in {"override", "reject", "request_rework", "escalate"} and not body.command.strip():
        raise HTTPException(status_code=400, detail="A comment or reason is required for this action.")
    output_document = None
    if body.action_type == "edit_output":
        output_document = build_stage_output(stage, stage.get("last_rule_run"), body.actor_email, body.output_text or body.command)
        stage["stage_output_document"] = output_document
    if body.action_type == "send_next_stage":
        latest_output = stage.get("stage_output_document") or build_stage_output(stage, stage.get("last_rule_run"), body.actor_email)
        stage["stage_output_document"] = latest_output
        if latest_output.get("next_stage_id"):
            next_stage = stage_by_id(latest_output["next_stage_id"])
            if next_stage:
                next_stage.setdefault("inputs", []).insert(0, {"name": latest_output["title"], "value": latest_output["version"], "source": "MedGuard Stage Output"})
    action = {
        "id": f"ACT-{len(WORKFLOW_ACTIONS) + 1:04d}",
        "stage_id": body.stage_id,
        "stage": stage["name"],
        "action_type": body.action_type,
        "command": body.command,
        "output_document": output_document,
        "reason_code": body.reason_code,
        "affected_rule": body.affected_rule,
        "actor": actor["name"],
        "actor_email": actor["email"],
        "timestamp": now_ist(),
    }
    WORKFLOW_ACTIONS.insert(0, action)
    AUDIT_EVENTS.insert(0, {
        "id": f"AUD-{len(AUDIT_EVENTS) + 1:03d}",
        "stage": stage["name"],
        "trigger": "Human-in-the-loop action",
        "severity": "medium" if body.action_type in {"override", "request_rework", "escalate"} else "low",
        "source_system": "MedGuard workflow",
        "asset_id": stage.get("asset_id", ""),
        "actor": actor["name"],
        "actor_id": actor["id"],
        "actor_email": actor["email"],
        "action": body.action_type.replace("_", " ").title(),
        "agent_output": body.command or "Workflow action captured",
        "decision": body.action_type,
        "reviewer": actor["name"],
        "reason": body.command or body.reason_code,
        "timestamp": action["timestamp"],
        "final_recommendation": "Next stage ready" if body.action_type == "send_next_stage" else "Action captured",
        "evidence_links": [body.affected_rule] if body.affected_rule else [stage.get("asset_id", "")],
    })
    return JSONResponse({"status": "captured", "action": action, "stage": stage, "dashboard": dashboard_overview()})

@app.post("/api/workflow/approvals")
async def record_workflow_approval(body: WorkflowApprovalRequest):
    mapped_action = "approve" if body.decision in {"approve", "final_authorize"} else "request_changes" if body.decision == "request_rework" else "override"
    approval = record_rule_approval(StepApprovalRequest(
        actor_email=body.actor_email,
        stage_id=body.stage_id,
        step_id=body.step_id,
        action=mapped_action,
        reason=body.reason,
        reason_code=body.decision,
        affected_rule=body.step_id,
    ))
    gate = {
        "id": f"GATE-{len(APPROVAL_GATES) + 1:04d}",
        "stage_id": body.stage_id,
        "bundle_id": body.bundle_id,
        "decision": body.decision,
        "status": "approved" if body.decision in {"approve", "final_authorize"} else "requested",
        "actor": approval["actor"],
        "timestamp": approval["timestamp"],
        "reason": body.reason,
    }
    APPROVAL_GATES.insert(0, gate)
    return JSONResponse({"status": "captured", "approval_gate": gate, "approval": approval, "dashboard": dashboard_overview()})

@app.get("/api/rule-engine/stages")
async def get_rule_engine_stages():
    return JSONResponse([
        {
            "stage_id": stage_id,
            "threshold": definition["threshold"],
            "purpose": definition["purpose"],
            "steps": definition["steps"],
        }
        for stage_id, definition in RULE_ENGINE_STAGES.items()
    ])

@app.get("/api/rule-engine/runs")
async def get_rule_engine_runs(stage_id: Optional[str] = None):
    runs = list(RULE_ENGINE_RUNS.values())
    if stage_id:
        runs = [run for run in runs if run["stage_id"] == stage_id]
    return JSONResponse(runs)

@app.post("/api/rule-engine/run")
async def run_rule_engine(body: RuleRunRequest):
    actor = USERS.get(normalize_email(body.actor_email)) if body.actor_email else None
    if body.actor_email and (not actor or actor["status"] != "active"):
        raise HTTPException(status_code=403, detail="Active user required.")
    if actor and not can_access_stage(actor, body.stage_id, write=True):
        raise HTTPException(status_code=403, detail="Your role does not have write access to this stage.")
    run = build_rule_engine_run(body.stage_id, body.actor_email, body.content_id, body.use_gemini, body.model_profile, body.bundle_id, body.action_context)
    stage = stage_by_id(body.stage_id)
    output_document = build_stage_output(stage, run, body.actor_email) if stage else None
    if stage and output_document:
        stage["stage_output_document"] = output_document
    return JSONResponse({"status": "completed", "run": run, "stage": stage, "output_document": output_document, "dashboard": dashboard_overview()})

@app.post("/api/rule-engine/approval")
async def approve_rule_engine_step(body: StepApprovalRequest):
    approval = record_rule_approval(body)
    return JSONResponse({"status": "captured", "approval": approval, "runs": list(RULE_ENGINE_RUNS.values()), "dashboard": dashboard_overview()})

@app.get("/api/notifications")
async def get_notifications():
    return JSONResponse(NOTIFICATIONS)

@app.get("/api/sample-media")
async def get_sample_media(stage_id: Optional[str] = None):
    media = stage_media(stage_id) if stage_id else [item for item in SAMPLE_MEDIA_FILES if item["id"] in ALLOWED_SAMPLE_MEDIA_IDS]
    return JSONResponse(media)

@app.get("/api/connections/status")
async def get_connections_status():
    return JSONResponse(CONNECTIONS)

@app.post("/api/connections")
async def create_connection(body: ConnectorRequest):
    if body.actor_email:
        require_admin(body.actor_email)
    connector_id = body.name.lower().replace(" ", "-").replace("/", "-")
    if any(item["id"] == connector_id for item in CONNECTIONS):
        connector_id = f"{connector_id}-{len(CONNECTIONS) + 1}"
    connector = {
        "id": connector_id,
        "name": body.name.strip(),
        "icon": body.icon,
        "scope": body.scope.strip(),
        "status": body.status,
        "health": 74 if body.status in {"candidate", "planned"} else 92,
        "auth_method": body.auth_method.strip(),
        "owner": body.owner.strip(),
        "scopes": body.scopes,
        "handoff": "Configured connector awaiting first workflow signal",
        "last_event": "Created in connector manager",
        "last_sync": "Pending",
        "latency_ms": 0,
        "actions": ["test", "edit", "rotate_secret", "view_logs", "disable"],
    }
    CONNECTIONS.insert(0, connector)
    return JSONResponse(connector)

@app.put("/api/connections/{connection_id}")
async def update_connection(connection_id: str, body: ConnectorRequest):
    if body.actor_email:
        require_admin(body.actor_email)
    connector = next((item for item in CONNECTIONS if item["id"] == connection_id), None)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")
    connector.update({
        "name": body.name.strip(),
        "icon": body.icon,
        "scope": body.scope.strip(),
        "status": body.status,
        "auth_method": body.auth_method.strip(),
        "owner": body.owner.strip(),
        "scopes": body.scopes,
        "last_event": "Connector settings updated",
    })
    return JSONResponse(connector)

@app.delete("/api/connections/{connection_id}")
async def delete_connection(connection_id: str, actor_email: str = ""):
    if actor_email:
        require_admin(actor_email)
    index = next((idx for idx, item in enumerate(CONNECTIONS) if item["id"] == connection_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Connector not found.")
    connector = CONNECTIONS.pop(index)
    return JSONResponse({"status": "deleted", "connector": connector})

@app.post("/api/connections/{connection_id}/test")
async def test_connection(connection_id: str, body: ActorRequest):
    if body.actor_email:
        require_admin(body.actor_email)
    connector = next((item for item in CONNECTIONS if item["id"] == connection_id), None)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found.")
    result = {
        "connector_id": connection_id,
        "status": "passed" if connector["status"] != "disabled" else "failed",
        "auth": "valid" if connector["status"] != "disabled" else "revoked",
        "webhook": "reachable" if connector["status"] != "disabled" else "disabled",
        "latency_ms": connector.get("latency_ms") or 246,
        "permissions": [{"scope": scope, "status": "granted"} for scope in connector.get("scopes", [])],
        "checked_at": "2026-05-04 10:34 IST",
    }
    connector["last_event"] = f"Connection test {result['status']}"
    connector["last_sync"] = "Just now"
    connector["health"] = 97 if result["status"] == "passed" else 41
    return JSONResponse(result)

@app.get("/api/architecture/flow")
async def get_architecture_flow():
    return JSONResponse(ARCHITECTURE_FLOW)

@app.post("/api/compliance/validate")
async def validate_compliance(body: ComplianceValidationRequest):
    stage = next((item for item in ORCHESTRATION_STAGES if item["id"] == body.stage_id), ORCHESTRATION_STAGES[1])
    claim_text = (body.claim or body.content).strip()
    overclaim = "10 year" in claim_text.lower() or "10-year" in claim_text.lower() or "10 years" in claim_text.lower()
    missing_safety = "safety" not in body.content.lower() and "adverse" not in body.content.lower()
    market_sensitive = body.market.lower() in {"india", "saudi arabia", "ksa"}
    blockers = []
    if overclaim:
        blockers.append("Evidence supports 8 years while the claim states 10 years.")
    if missing_safety:
        blockers.append("Safety context is missing from the content body.")
    if market_sensitive:
        blockers.append(f"{body.market} market caveat requires local reviewer confirmation.")

    risk_score = 86 if overclaim else 54 if missing_safety or market_sensitive else 22
    risk_level = "high" if risk_score >= 80 else "medium" if risk_score >= 45 else "low"
    decision = "ESCALATE" if risk_score >= 85 else "REWORK" if risk_score >= 45 else "PASS"
    confidence = 0.91 if overclaim else 0.84 if risk_level == "medium" else 0.78
    recommendation = (
        "Replace the 10-year duration claim with approved 8-year evidence wording and route to medical review."
        if overclaim
        else "Add required safety context and capture local reviewer confirmation."
        if risk_level == "medium"
        else "Proceed with audit capture and normal approval routing."
    )
    audit_id = f"AUD-{len(AUDIT_EVENTS) + 1:03d}"
    event = {
        "id": audit_id,
        "stage": stage["name"],
        "trigger": stage["trigger"],
        "agent_output": f"{risk_level.upper()} risk; {len(blockers)} blocker(s); confidence {round(confidence * 100)}%",
        "decision": f"Validation workflow returned {decision}",
        "reviewer": "AI validation layer",
        "reason": recommendation,
        "timestamp": "2026-05-04 10:18 IST",
        "final_recommendation": recommendation,
    }
    AUDIT_EVENTS.insert(0, event)

    agent_trace = [
        {
            "agent": "Claim Agent",
            "status": "needs_review" if overclaim else "passed",
            "output": "Duration claim extracted and classified as efficacy/durability.",
            "evidence": claim_text,
        },
        {
            "agent": "Reference Agent",
            "status": "blocked" if overclaim else "passed",
            "output": "Approved evidence supports 8-year durability data.",
            "evidence": "REF-SHINGRIX-008; label-aligned evidence packet",
        },
        {
            "agent": "Regulatory Agent",
            "status": "needs_review" if market_sensitive else "passed",
            "output": f"{body.market} promotional caveat checked against local guidance.",
            "evidence": "Country rule pack and local affiliate policy",
        },
        {
            "agent": "Compliance Policy Agent",
            "status": "needs_review" if missing_safety else "passed",
            "output": "Fair-balance and mandatory safety language assessed.",
            "evidence": "Global SOP, brand guardrails, fair-balance threshold",
        },
        {
            "agent": "Security Agent",
            "status": "passed",
            "output": "No PII/PHI tokens detected in submitted content.",
            "evidence": "PII/PHI scanner and content integrity check",
        },
        {
            "agent": "Audit Agent",
            "status": "captured",
            "output": f"Validation event stored as {audit_id}.",
            "evidence": "Trigger, inputs, checks, recommendation, and reviewer action are ready for audit.",
        },
    ]

    return JSONResponse({
        "asset_id": body.asset_id,
        "market": body.market,
        "channel": body.channel,
        "stage": {"id": stage["id"], "name": stage["name"], "trigger": stage["trigger"], "system": stage["system"]},
        "risk_score": risk_score,
        "risk_level": risk_level,
        "decision": decision,
        "confidence": confidence,
        "blockers": blockers,
        "recommendation": recommendation,
        "corrected_claim": "Immunavax demonstrated durable immune response supported by 8-year follow-up data." if overclaim else claim_text,
        "workflow": ARCHITECTURE_FLOW["validation_workflow"],
        "agent_trace": agent_trace,
        "audit_event": event,
    })

@app.get("/api/kpis/compliance")
async def get_compliance_kpis():
    return JSONResponse(COMPLIANCE_KPIS)

@app.get("/api/audit/events")
async def get_audit_events(q: Optional[str] = None, stage: Optional[str] = None, severity: Optional[str] = None, actor: Optional[str] = None, source_system: Optional[str] = None):
    return JSONResponse(apply_audit_filters(AUDIT_EVENTS, {"q": q, "stage": stage, "severity": severity, "actor": actor, "source_system": source_system}))

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
        "claims-governance": AgentStep(
            agent="ClaimsGovernanceAgent",
            task="Validate claim lifecycle, evidence support, permitted use, market eligibility, and expiry status.",
            inputs=["claim register", "evidence map", "market policy pack", "asset claims"],
            output_schema="ClaimGovernancePacket",
            handoff_to="ComplianceAgent",
            risk_level="high",
        ),
        "responsible-ai": AgentStep(
            agent="ResponsibleAIGovernanceAgent",
            task="Assess AI use-case risk, source-grounding, human gates, audit evidence, and policy controls.",
            inputs=["AI use-case register", "model policy", "prompt logs", "tool-call audit"],
            output_schema="ResponsibleAIControlReport",
            handoff_to="WorkflowOrchestrationAgent",
            risk_level="high",
        ),
        "workflow-orchestration": AgentStep(
            agent="WorkflowOrchestrationAgent",
            task="Design downstream handoffs, owners, gates, SLA escalation, and deployment-readiness checks.",
            inputs=["workflow stages", "review queue", "RACI", "market handoffs"],
            output_schema="DownstreamOperatingModel",
            handoff_to="IntegrationLayerAgent",
            risk_level="medium",
        ),
        "integration-layer": AgentStep(
            agent="IntegrationLayerAgent",
            task="Map data contracts and handoffs across authoring, DAM, MLR workflow, CRM, model gateway, and analytics systems.",
            inputs=["system inventory", "API candidates", "metadata schema", "audit requirements"],
            output_schema="EcosystemIntegrationMap",
            handoff_to="PilotReadinessAgent",
            risk_level="medium",
        ),
        "poc-readiness": AgentStep(
            agent="PilotReadinessAgent",
            task="Prepare build-vs-buy evaluation, pilot scope, acceptance criteria, and RFP-ready assumptions.",
            inputs=["business objectives", "platform options", "pilot data set", "security constraints"],
            output_schema="PilotEvaluationBrief",
            risk_level="low",
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
    if {"claims-governance", "responsible-ai", "compliance"}.issubset(set(requested_modules)):
        pattern = "parallel_review"

    return AgentPlan(
        objective=body.objective,
        market=body.market,
        orchestration_pattern=pattern,
        steps=steps,
        human_review_gates=[
            "Medical owner signs off evidence trace map.",
            "Claims owner approves permitted-use and market-eligibility decisions.",
            "Compliance owner reviews high-risk claims before MLR submission.",
            "Responsible AI owner validates model, prompt, source, and audit controls.",
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
    reference_corpus = {
        "references": [
            ("REF-210", "Respiratory guideline update", "Guideline reference for COPD burden and HCP education."),
            ("REF-311", "Phase III exacerbation endpoint", "Endpoint support for exacerbation reduction claims."),
            ("REF-427", "Real-world persistence study", "RWE limitations and persistence signal summary."),
        ],
        "claims": [
            ("CLM-184", "COPD burden claim", "Approved disease burden claim with reference mapping."),
            ("CLM-229", "Adult immunisation education claim", "Non-promotional HCP education claim."),
            ("CLM-314", "Localized COPD email variant", "Short-form claim pending permitted-market and caveat validation."),
            ("CLM-402", "Oncology biomarker testing claim", "Evidence-backed claim requiring market-specific diagnostic pathway notes."),
        ],
        "assets": [
            ("DAM-884", "Oncoryn MOA animation", "Animation asset missing expiry owner and usage-right metadata."),
            ("DAM-731", "COPD patient journey diagram", "Market restriction metadata incomplete."),
        ],
        "policies": [
            ("POL-ABPI", "ABPI digital promotional checklist", "Fair balance, certification, reference, and prescribing information checks."),
            ("POL-CDSCO", "India promotional review checklist", "Local review and prescribing information expectations."),
            ("POL-RAI-01", "Responsible AI content policy", "Source-grounding, prompt logging, model approval, human-gate, and audit requirements."),
            ("POL-MCP-03", "Tool-use governance policy", "Approved MCP tool boundaries, risk tiers, owner review, and evidence retention expectations."),
        ],
    }
    docs = reference_corpus.get(body.corpus, reference_corpus["references"])[:body.top_k]
    return [
        RAGDocument(
            id=doc_id,
            title=title,
            corpus=body.corpus,
            snippet=snippet,
            score=round(0.92 - index * 0.07, 2),
            metadata={"query": body.query, "source": "rag_index"},
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
            name="claim_register_lookup",
            description="Retrieve claim owner, allowed markets, allowed channels, expiry, variants, and permitted-use notes.",
            input_schema={"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]},
            risk_level="medium",
        ),
        MCPTool(
            name="responsible_ai_policy_check",
            description="Check whether an AI workflow has approved model, source-grounding, logging, and human-gate controls.",
            input_schema={"type": "object", "properties": {"use_case_id": {"type": "string"}}, "required": ["use_case_id"]},
            risk_level="high",
        ),
        MCPTool(
            name="workflow_handoff_map",
            description="Map downstream owners, review gates, SLA risk, and deployment readiness blockers for a content package.",
            input_schema={"type": "object", "properties": {"asset_id": {"type": "string"}, "market": {"type": "string"}}, "required": ["asset_id", "market"]},
            risk_level="medium",
        ),
        MCPTool(
            name="ecosystem_capability_scan",
            description="Compare existing platform capability against custom orchestration needs for a proposed pilot.",
            input_schema={"type": "object", "properties": {"capability": {"type": "string"}}, "required": ["capability"]},
            risk_level="low",
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
        {"id": 1, "name": "Respivara COPD eDetailAid Q2 2026", "type": "eDA", "status": "Approved", "therapeutic": "Respiratory", "channel": "Remote Detailing", "audience": "Pulmonologist", "region": "Global", "updated": "2026-04-15"},
        {"id": 2, "name": "Vaxilora Adult Immunisation HCP Email", "type": "Email", "status": "Draft", "therapeutic": "Vaccines", "channel": "Email", "audience": "GP", "region": "UK", "updated": "2026-04-20"},
        {"id": 3, "name": "Oncology Scientific Narrative v3", "type": "Document", "status": "In Review", "therapeutic": "Oncology", "channel": "Medical", "audience": "Oncologist", "region": "Global", "updated": "2026-04-18"},
        {"id": 4, "name": "ImmunoLift Patient Support Brochure", "type": "Print", "status": "Approved", "therapeutic": "Immunology", "channel": "Multi-channel", "audience": "Patient", "region": "US", "updated": "2026-04-10"},
        {"id": 5, "name": "Adult Immunisation Congress Slides", "type": "Presentation", "status": "Approved", "therapeutic": "Vaccines", "channel": "Congress", "audience": "HCP", "region": "Global", "updated": "2026-04-08"},
        {"id": 6, "name": "India Asthma Campaign Module", "type": "Module", "status": "Draft", "therapeutic": "Respiratory", "channel": "Email", "audience": "HCP", "region": "India", "updated": "2026-04-22"},
        {"id": 7, "name": "Saudi Oncology Content Adaptation", "type": "Module", "status": "In Review", "therapeutic": "Oncology", "channel": "Email", "audience": "Oncologist", "region": "Saudi Arabia", "updated": "2026-04-21"},
        {"id": 8, "name": "Oncoryn Efficacy Claims Module", "type": "Module", "status": "Approved", "therapeutic": "Oncology", "channel": "Multi-channel", "audience": "Oncologist", "region": "Global", "updated": "2026-04-01"},
        {"id": 9, "name": "Respivara COPD Claim Block", "type": "Module", "status": "Approved", "therapeutic": "Respiratory", "channel": "Multi-channel", "audience": "Pulmonologist", "region": "Global", "updated": "2026-03-28"},
        {"id": 10, "name": "Vaxorin Phase III Data Summary", "type": "Document", "status": "Expired", "therapeutic": "Vaccines", "channel": "Medical", "audience": "HCP", "region": "US", "updated": "2026-02-01"},
        {"id": 11, "name": "ImmunoLift Rheumatoid Arthritis Social Content Pack", "type": "Social", "status": "Approved", "therapeutic": "Immunology", "channel": "Social Media", "audience": "Patient", "region": "UK", "updated": "2026-04-12"},
        {"id": 12, "name": "Oncoryn MOA Animation", "type": "Video", "status": "In Review", "therapeutic": "Oncology", "channel": "eDA", "audience": "Oncologist", "region": "US", "updated": "2026-04-23"},
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
            "content-lab": {"status": "active", "label": "Content Lab", "icon": "content", "detail": "23 in progress · 8 pending review"},
            "dam": {"status": "active", "label": "DAM", "icon": "asset", "detail": "2,847 assets · 14 expiring soon"},
            "scp": {"status": "active", "label": "Sci Comm (SCP)", "icon": "evidence", "detail": "6 active platforms · 3 pending updates"},
            "evidence": {"status": "active", "label": "Evidence Synthesis", "icon": "evidence", "detail": "4 reviews in progress · 18 completed MTD"},
            "email-qa": {"status": "active", "label": "Email QA", "icon": "email", "detail": "34 tests today · 2 issues flagged"},
            "compliance": {"status": "warning", "label": "Compliance", "icon": "compliance", "detail": "17 pending MLR · avg 7.8 days cycle"},
            "claims-governance": {"status": "warning", "label": "Claims Governance", "icon": "claims", "detail": "318 active claims · 11 evidence gaps"},
            "responsible-ai": {"status": "warning", "label": "Responsible AI", "icon": "ai", "detail": "14 AI use cases · 3 high-risk controls"},
            "workflow-orchestration": {"status": "active", "label": "Workflow Orchestration", "icon": "workflow", "detail": "24 markets · 6 deployment blockers"},
            "integration-layer": {"status": "active", "label": "Integration Layer", "icon": "integration", "detail": "12 API candidates · 7 metadata mappings"},
            "poc-readiness": {"status": "active", "label": "Pilot Readiness", "icon": "strategy", "detail": "6-week pilot · 4 open brief questions"},
            "localization": {"status": "active", "label": "Localisation", "icon": "localization", "detail": "9 in progress · 4 markets active"},
            "analytics": {"status": "active", "label": "Analytics", "icon": "analytics", "detail": "Last updated: 25 Apr 09:00 UTC"}
        }
    })

@app.get("/api/integrations/status")
async def get_integrations_status():
    return JSONResponse([
        {
            "id": "veeva-crm",
            "name": "Veeva CRM",
            "role": "Field engagement and approved-content activation",
            "status": "connected",
            "fit": "Receive approved, metadata-clean content packages and activation readiness signals.",
            "handoff": "Approved asset ID, market, channel, audience, claim IDs, expiry, and activation owner.",
            "owner": "Commercial operations",
            "risk": "Do not duplicate CRM workflows; enrich activation with governance status.",
        },
        {
            "id": "veeva-promomats",
            "name": "Veeva PromoMats",
            "role": "MLR workflow, content lifecycle, claims, DAM, and source of truth",
            "status": "planned",
            "fit": "Prepare reviewer-ready claim packets and audit evidence before formal workflow submission.",
            "handoff": "Claim packet, reference map, risk tier, reviewer notes, and modular-content lineage.",
            "owner": "MLR operations",
            "risk": "Keep formal approval and records in the system of record.",
        },
        {
            "id": "litmus",
            "name": "Litmus",
            "role": "Email previews, links, accessibility, spam, and pre-send QA",
            "status": "connected",
            "fit": "Trigger QA checks and merge Litmus findings into compliance and deployment readiness.",
            "handoff": "HTML email, market, selected clients, accessibility status, link check, spam score, and screenshots.",
            "owner": "Email operations",
            "risk": "Use Litmus results as QA evidence, not as medical or regulatory approval.",
        },
        {
            "id": "aem",
            "name": "Adobe / AEM",
            "role": "Authoring, web content, components, and brand experience management",
            "status": "candidate",
            "fit": "Pull authored modules and push governance metadata, claim status, and reviewer watchouts.",
            "handoff": "Component ID, copy block, asset usage, claim IDs, market tags, and approved status.",
            "owner": "Digital experience",
            "risk": "Do not compete with authoring; govern the downstream validation path.",
        },
        {
            "id": "partner-lanes",
            "name": "Agency and operations partners",
            "role": "Content production, deployment support, activation, and measurement operations",
            "status": "candidate",
            "fit": "Standardize briefs, prompts, handoffs, metadata requirements, and evidence expectations.",
            "handoff": "Brief, module rules, asset checklist, review gates, production SLA, and issue log.",
            "owner": "Content operations",
            "risk": "Make partner work auditable without slowing production.",
        },
        {
            "id": "model-gateway",
            "name": "Enterprise model gateway",
            "role": "Approved model access, prompt logging, policy controls, and data boundary enforcement",
            "status": "planned",
            "fit": "Route all regulated AI tasks through approved model and source-grounding controls.",
            "handoff": "Use-case ID, model ID, prompt, retrieved sources, tool calls, reviewer decision, and output hash.",
            "owner": "Responsible AI office",
            "risk": "Block high-risk AI use cases without logging and human gates.",
        },
    ])

@app.get("/api/modules")
async def get_content_modules():
    return JSONResponse([
        {"id": "claim-copd-efficacy", "name": "COPD Efficacy Claim", "type": "Claim", "therapeutic": "Respiratory", "status": "Approved", "channels": ["eDA", "Email", "Social"]},
        {"id": "safety-copd-01", "name": "COPD Safety Statement", "type": "Safety", "therapeutic": "Respiratory", "status": "Approved", "channels": ["eDA", "Email", "Print"]},
        {"id": "claim-vaxilora-efficacy", "name": "Vaxilora Adult Immunisation Claim", "type": "Claim", "therapeutic": "Vaccines", "status": "Approved", "channels": ["eDA", "Email", "Social", "Congress"]},
        {"id": "header-brand-logo", "name": "Brand Header", "type": "Brand", "therapeutic": "Global", "status": "Approved", "channels": ["All"]},
        {"id": "footer-legal-uk", "name": "UK Legal Footer", "type": "Legal", "therapeutic": "Global", "status": "Approved", "channels": ["Email", "eDA"]},
        {"id": "footer-legal-us", "name": "US Legal Footer / ISI", "type": "Legal", "therapeutic": "Global", "status": "Approved", "channels": ["Email", "eDA", "Print"]},
        {"id": "claim-immunolift-efficacy", "name": "ImmunoLift Exacerbation Reduction", "type": "Claim", "therapeutic": "Immunology", "status": "Approved", "channels": ["eDA", "Email"]},
        {"id": "moa-oncoryn", "name": "Oncoryn MOA Visual", "type": "Visual", "therapeutic": "Oncology", "status": "In Review", "channels": ["eDA", "Congress"]},
        {"id": "ref-block-01", "name": "Standard Reference Block", "type": "Reference", "therapeutic": "Global", "status": "Approved", "channels": ["All"]},
        {"id": "cta-learn-more", "name": "Learn More CTA Button", "type": "CTA", "therapeutic": "Global", "status": "Approved", "channels": ["Email", "Social"]},
        {"id": "claim-respivara-efficacy", "name": "Respivara Triple Therapy Claim", "type": "Claim", "therapeutic": "Respiratory", "status": "Approved", "channels": ["eDA", "Email", "Print"]},
        {"id": "safety-vaccines-01", "name": "Vaccines General Safety Block", "type": "Safety", "therapeutic": "Vaccines", "status": "Approved", "channels": ["eDA", "Email", "Print", "Social"]},
        {"id": "claim-register-copd", "name": "COPD Claim Register Packet", "type": "Governance", "therapeutic": "Respiratory", "status": "Needs Evidence Review", "channels": ["All"]},
        {"id": "rai-policy-promo-01", "name": "Responsible AI Promo Content Control", "type": "Policy", "therapeutic": "Global", "status": "Draft", "channels": ["All"]},
        {"id": "workflow-global-local-01", "name": "Global-To-Local Approval Workflow", "type": "Workflow", "therapeutic": "Global", "status": "In Review", "channels": ["All"]},
        {"id": "integration-audit-map-01", "name": "Content Governance Integration Map", "type": "Integration", "therapeutic": "Global", "status": "Draft", "channels": ["All"]},
    ])

@app.get("/")
async def serve_index():
    return RedirectResponse(FRONTEND_URL)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
