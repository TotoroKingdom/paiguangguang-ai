# Homepage Content Restructure PRD

> Status: Draft  
> Scope: Homepage information architecture & content restructuring only  
> Branch: `dev`  
> Target repository: `TotoroKingdom/paiguangguang-ai`

---

## 1. Background

The homepage visual direction has already been redesigned and accepted around a light neumorphic / spatial AI style with 3D elements.

The next phase is **not another visual redesign**. The goal is to restructure the homepage content so that it communicates a clear personal narrative:

> Who I am → What I can do → What I have built → What I am building → What I am studying → Where I am going.

The homepage should function as a long-term personal showcase for future job opportunities, technical branding, and public project promotion.

The target positioning is:

**AI Agent Engineer → AI Agent Architect**

The page should present engineering capability through systems, projects, and current technical exploration rather than through a traditional résumé layout.

---

## 2. Product Goal

Rebuild the homepage content structure around six primary questions:

1. Who am I?
2. What can I do?
3. What have I built?
4. What am I building now?
5. What open-source systems am I studying?
6. Where is my career heading?

The homepage should let a visitor understand the following within a short browsing session:

- current professional identity;
- core AI engineering capabilities;
- completed project evidence;
- active project direction;
- current technical exploration;
- long-term career trajectory.

---

## 3. Design Principles

### 3.1 Preserve the current visual system

This phase must keep the currently accepted visual direction:

- light neumorphism;
- spatial layout;
- 3D AI elements;
- soft motion;
- minimal / premium AI-product feel.

Do not return to:

- dark cyberpunk;
- hacker dashboard;
- terminal-heavy UI;
- strong neon glow;
- dense technology-logo walls.

### 3.2 Evidence over slogans

The homepage should avoid generic claims such as:

- “proficient in AI”;
- “expert in LangChain”;
- “90% Python”;
- “full-stack 85%”.

Capabilities should be demonstrated by concrete engineering problems and systems.

### 3.3 Separate ownership states

Projects must be visually and semantically separated into:

- **BUILT** — completed systems built by me;
- **BUILDING** — active systems currently being developed;
- **EXPLORING** — external open-source systems I am studying.

Visitors must not confuse open-source projects being studied with projects authored by me.

### 3.4 Homepage is not a résumé

Do not add:

- education history;
- long employment timelines;
- skill progress bars;
- large certificate walls;
- GitHub contribution heatmaps;
- long autobiographical paragraphs.

The page should communicate an engineering trajectory, not reproduce a CV.

---

## 4. Target Audience

Primary audiences:

### 4.1 Recruiters / hiring managers

They need to quickly understand:

- current role positioning;
- actual AI engineering capability;
- project depth;
- technical growth direction.

### 4.2 AI engineers / architects

They should be able to see:

- system thinking;
- engineering choices;
- areas of technical exploration;
- open-source interests.

### 4.3 Potential collaborators

They should understand:

- what kinds of systems are being built;
- what areas are currently active;
- where collaboration may be relevant.

---

## 5. Homepage Information Architecture

The homepage should follow this narrative:

```text
HERO
  ↓
01 / WHO I AM
  ↓
02 / WHAT I CAN DO
  ↓
03 / WHAT I'VE BUILT
  ↓
04 / WHAT I'M BUILDING
  ↓
05 / WHAT I'M EXPLORING
  ↓
06 / WHERE I'M GOING
  ↓
CONTACT / GITHUB
```

This order is intentional:

> Identity → Capability → Evidence → Current Action → Technical Curiosity → Career Direction

---

# 6. Section Requirements

## 6.1 Hero / Who I Am

### Goal

Answer immediately:

- Who is this person?
- What kind of engineer is he?
- What kind of systems does he build?

### Recommended content

Primary identity:

**AI Agent Engineer**

Secondary identity:

**Full-stack Engineer**

Core statement:

> I build AI systems that actually ship.

Supporting direction:

- AI Agents
- RAG / Knowledge Systems
- AI Applications
- Agent Harness / Runtime

A short professional evolution line may be shown:

```text
Backend → AI Application → Agent Engineering → Agent Architecture
```

### Requirements

- Keep the current 3D Hero visual.
- Do not turn this section into a long “About Me”.
- Do not repeat the same identity again later in the page.
- CTA should primarily point to projects / work and GitHub.

---

## 6.2 What I Can Do / Capabilities

### Goal

Explain engineering capability as systems, not a technology checklist.

### Capability Pillars

#### A. Agent Engineering

Capability themes:

- LangGraph / stateful workflow;
- planning and execution loops;
- tool calling;
- Human-in-the-loop;
- memory;
- state management;
- verification / evaluation;
- failure recovery.

Expected message:

> Can design and implement observable, stateful Agent workflows rather than only single-shot LLM calls.

---

#### B. RAG & Knowledge Systems

Capability themes:

- document ingestion;
- chunking;
- embedding;
- hybrid retrieval;
- RRF;
- rerank;
- context assembly;
- citation;
- permission filtering;
- evaluation.

Expected message:

> Can build a complete knowledge retrieval pipeline with traceable sources and controllable access boundaries.

---

#### C. Backend & AI Infrastructure

Capability themes:

- Java backend;
- Python / FastAPI;
- Redis;
- PostgreSQL;
- vector databases;
- Docker;
- CI/CD;
- observability;
- API / service design.

Expected message:

> Can provide reliable application and infrastructure foundations for AI systems.

---

#### D. AI Product Engineering

Capability themes:

- Next.js;
- AI UX;
- streaming interaction;
- Agent UI;
- model / provider integration;
- Vibe Coding workflows;
- deployment;
- product delivery.

Expected message:

> Can convert AI capabilities into usable and deployable products instead of isolated demos.

### Requirements

- Do not use skill percentages.
- Frameworks and tools should appear as supporting evidence under a capability.
- Keep descriptions concise and scannable.

---

## 6.3 What I've Built / Completed Projects

### Goal

Provide concrete proof of engineering capability.

This section represents systems that have reached a meaningful end-to-end stage and can be explained as completed engineering work.

### Project 1 — RAG System

Positioning:

**KNOWLEDGE**

Suggested title:

**Production-oriented RAG System**

Core chain:

```text
Document Ingestion
→ Chunking
→ Embedding
→ Hybrid Retrieval
→ RRF
→ Rerank
→ Context Assembly
→ Citation
→ Evaluation
```

Primary capability evidence:

- retrieval engineering;
- context quality;
- traceability;
- evaluation.

Preferred CTA:

**Explore System →**

If an internal RAG page already exists, this card should link to the internal project/system explanation page rather than only GitHub.

---

### Project 2 — AI Chatbot

Positioning:

**CONVERSATION**

Suggested title:

**Production AI Chatbot**

Capability themes:

- multi-conversation management;
- persistent history;
- streaming response;
- short-term memory;
- long-term memory;
- semantic memory;
- checkpoint;
- Redis;
- PostgreSQL;
- LLM gateway / provider abstraction.

Primary capability evidence:

- conversational infrastructure;
- memory architecture;
- persistence;
- production-style chat flow.

---

### Project 3 — Office Automation Agent

Positioning:

**ACTION**

Suggested title:

**Office Automation Agent**

Capability themes:

- Agent workflow;
- tool calling;
- Human-in-the-loop;
- approval;
- business API integration;
- structured output;
- auditability.

Primary capability evidence:

- Agent action;
- enterprise workflow;
- tool integration;
- controlled execution.

---

### Completed Projects Narrative

The three projects should be presented together as:

```text
KNOWLEDGE
RAG System

CONVERSATION
AI Chatbot

ACTION
Office Automation Agent
```

This creates a stronger system narrative than three unrelated project cards.

### Requirements

Each project should include:

- project name;
- one-line positioning;
- short problem / purpose;
- key engineering capabilities;
- project status;
- internal or external link when available.

Do not overload project cards with implementation detail. Deeper architecture belongs on project detail pages.

---

## 6.4 What I'm Building / Active Projects

### Goal

Show current technical investment and direction.

These are not “finished portfolio pieces”. They represent active engineering work.

Each item must clearly display an **ACTIVE / BUILDING** state.

---

### Active Project 1 — Knowledge Platform

Suggested positioning:

**Enterprise Knowledge Platform / Knowledge Governance**

Possible focus areas:

- knowledge governance;
- knowledge objects;
- ACL / permission;
- governance rules;
- Agent governance;
- enterprise knowledge infrastructure.

Expected message:

> Building enterprise-grade knowledge infrastructure that can be consumed safely by Agents.

---

### Active Project 2 — Enterprise Digital Employee

Suggested positioning:

**Enterprise Digital Employee**

Possible focus areas:

- Agent runtime;
- enterprise tools;
- workflow orchestration;
- Human-in-the-loop;
- enterprise integration;
- approval / audit;
- task execution.

Expected message:

> Exploring how Agents can perform controlled, auditable work inside enterprise workflows.

---

### Active Project 3 — ChatGPT Harness

Suggested positioning:

**ChatGPT Harness**

Possible focus areas:

- model harness;
- Agent runtime;
- tool protocol;
- memory;
- context engineering;
- execution environment;
- developer experience.

Expected message:

> Building a controllable Harness around models, tools, context and Agent execution.

---

### Requirements

- Clearly distinguish these projects from completed work.
- Use “ACTIVE”, “BUILDING”, or similar visible state labels.
- Avoid presenting unfinished projects as completed outcomes.
- Project cards may link to GitHub or internal pages when available.

---

## 6.5 What I'm Exploring / Open Source I'm Studying

### Goal

Show technical curiosity and the systems currently being studied.

This section must **not** imply authorship.

Recommended title:

**What I'm Exploring**

Supporting label:

**Open Source I'm Studying**

### Projects

Initial set:

- OpenAI Codex
- DeepSeek
- Pi
- Hermes
- OpenClaw
- PyTorch / `pytorch-deep-learning`

### Card Model

Each card should contain:

- project name;
- source / organization;
- one short reason for studying it;
- 2–4 technical topics;
- GitHub external-link indicator.

Example:

```text
OpenAI Codex ↗

Coding Agent / Harness

Exploring:
Agent Harness
Tool Execution
Context Engineering
```

### Interaction

- Entire project card is clickable.
- Click opens the corresponding official GitHub/open-source repository in a new tab.
- External-link behavior must be visually clear.
- External repositories should not be represented as personal projects.

### Known link

PyTorch learning project:

`https://github.com/mrdbourke/pytorch-deep-learning`

### Open requirement

The canonical GitHub repository links for:

- Codex;
- DeepSeek;
- Pi;
- Hermes;
- OpenClaw;

must be confirmed before implementation if they are not already known from repository context.

Do not guess ambiguous repository URLs.

---

## 6.6 Where I'm Going / Career Journey

### Goal

Show career direction as a capability evolution rather than a résumé timeline.

### Recommended structure

```text
BACKEND ENGINEER
Reliable application engineering
        ↓
AI APPLICATION ENGINEER
RAG · LLM · AI Product
        ↓
AI AGENT ENGINEER
Workflow · Tools · Memory · HITL
        ↓
AI AGENT ARCHITECT
Agent Runtime · Knowledge Infrastructure
Distributed Agent Systems
Evaluation · Governance
```

### Current Position

The current stage should be visually highlighted as:

**AI Agent Engineer**

The future target is:

**AI Agent Architect**

### Requirements

- Do not use specific calendar years unless explicitly required later.
- Do not duplicate the full employment history.
- Focus on capability evolution.
- The final stage should clearly communicate the architectural capabilities being pursued.

---

# 7. Contact Section

Keep a concise final CTA.

Minimum links:

- GitHub
- Email

Optional future extension:

- Resume / CV
- LinkedIn or other professional profile

The contact section should remain secondary to the engineering narrative.

---

# 8. Navigation

The homepage navigation should be aligned with the new information architecture.

Recommended top-level anchors:

- About
- Capabilities
- Built
- Building
- Exploring
- Journey
- GitHub

The final exact number of visible nav items may be reduced for responsive simplicity.

Possible compact navigation:

```text
About
Work
Exploring
Journey
GitHub ↗
```

Where “Work” can cover both BUILT and BUILDING.

The navigation must not become visually dense.

---

# 9. Content Model

Homepage content should be data-driven rather than hard-coded repeatedly inside individual components.

Recommended logical entities:

```ts
Identity
Capability
CompletedProject
ActiveProject
ExplorationProject
CareerStage
```

This PRD does not prescribe the exact TypeScript implementation, but content should be maintainable from a centralized data structure where practical.

This is especially important for:

- project status changes;
- adding new open-source exploration;
- changing GitHub links;
- updating career stages.

---

# 10. Suggested Component Direction

Existing homepage structure can evolve without rewriting the whole frontend architecture.

Recommended direction:

```text
homepage-hero.tsx

homepage-identity.tsx
homepage-capabilities.tsx
homepage-built.tsx
homepage-building.tsx
homepage-exploring.tsx
homepage-journey.tsx
homepage-contact.tsx
```

Existing components may be reused or renamed where sensible.

Potential mapping:

```text
HomepageOverview
→ HomepageCapabilities

HomepageProjects
→ HomepageBuilt
   + HomepageBuilding
   + HomepageExploring

HomepageRoadmap
→ HomepageJourney
```

The exact component split belongs in Architecture / Plan rather than this PRD.

---

# 11. Non-Goals

This phase does not include:

- redesigning the accepted neumorphic visual language;
- replacing the current Hero 3D system;
- backend changes;
- authentication changes;
- API redesign;
- RAG system implementation;
- Agent functionality changes;
- project-detail-page redesign unless required for navigation consistency;
- adding new external services;
- adding a CMS;
- rewriting the entire website architecture.

---

# 12. Responsive Requirements

The new content structure must work across:

- desktop;
- tablet;
- mobile.

On mobile:

- sections remain in the same semantic order;
- project state labels remain visible;
- open-source cards remain clearly external;
- Career Journey may change from horizontal to vertical;
- capability cards should stack cleanly;
- no section may rely only on hover interaction.

---

# 13. Accessibility Requirements

- External links must be identifiable.
- Interactive cards must be keyboard accessible.
- Card click targets must use semantic links.
- Focus states must remain visible.
- Content meaning must not depend only on color.
- Motion must continue respecting `prefers-reduced-motion`.
- Heading hierarchy must remain valid.

---

# 14. Success Criteria

The restructure is successful when a visitor can answer all six questions after browsing the homepage:

1. Who is the engineer?
2. What systems can he build?
3. What has he already built?
4. What is he actively building?
5. What open-source systems is he studying?
6. What professional direction is he pursuing?

Additional acceptance signals:

- completed, active, and external projects are visually distinct;
- the homepage does not look like a traditional résumé template;
- the current visual design remains recognizable;
- technical content is concise but credible;
- project cards have clear navigation targets;
- no external open-source project is presented as personal authorship.

---

# 15. Acceptance Checklist

## Information Architecture

- [ ] Hero communicates current identity.
- [ ] Capabilities section contains four capability pillars.
- [ ] Completed work contains RAG, Chatbot, and Office Automation Agent.
- [ ] Active work contains Knowledge Platform, Enterprise Digital Employee, and ChatGPT Harness.
- [ ] Exploration section contains the defined external open-source systems.
- [ ] Career Journey ends at AI Agent Architect.
- [ ] Contact remains available at the bottom.

## Ownership & Status

- [ ] Completed work is labeled as completed / built.
- [ ] Active work is labeled as active / building.
- [ ] Exploration projects are explicitly external open-source projects.
- [ ] External repository links open correctly.
- [ ] No ambiguous authorship exists.

## Content Quality

- [ ] No skill percentage bars.
- [ ] No excessive framework/logo wall.
- [ ] No long résumé-style biography.
- [ ] Capabilities are described as engineering outcomes.
- [ ] Project descriptions focus on system capability and value.

## Visual Consistency

- [ ] Existing neumorphic design language is preserved.
- [ ] Existing 3D Hero direction is preserved.
- [ ] New sections reuse the current design system.
- [ ] Mobile hierarchy remains readable.

---

# 16. Open Questions / Decisions Before SPEC

These items do not block the PRD, but should be resolved before implementation SPEC / PLAN:

1. **Project naming**
   - Should “Knowledge Platform” be presented publicly as “Knowledge Platform”, “Knowledge Governance Platform”, or another final product name?
   - Should “Enterprise Digital Employee” use a public-facing project name?

2. **Project links**
   - What are the target links for the AI Chatbot and Office Automation Agent?
   - Which active projects have public GitHub repositories versus internal-only descriptions?

3. **Exploration repositories**
   - Confirm canonical GitHub links for Codex, DeepSeek, Pi, Hermes and OpenClaw.

4. **Personal identity label**
   - Preferred homepage primary title:
     - “AI Agent Engineer”
     - “AI Agent Engineer · Full-stack Engineer”
     - or another wording.

5. **Language strategy**
   - Current site mixes English headings with Chinese descriptions.
   - Recommendation: keep this bilingual pattern:
     - short English structural labels;
     - concise Chinese explanation;
     - technical terms remain in English.

---

# 17. Product Recommendation

The strongest homepage narrative is not “six independent sections”.

It should feel like one continuous engineering story:

```text
I am an AI Agent Engineer
        ↓
These are the systems I can build
        ↓
These are the systems I have already delivered
        ↓
These are the problems I am working on now
        ↓
These are the open-source systems shaping my thinking
        ↓
This is the architecture-level role I am growing toward
```

This narrative should guide all later SPEC, content writing and implementation decisions.
