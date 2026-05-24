# Notion Workspace Exploration for Brand3 Context

Date: 2026-05-14
Mode: read-only workspace exploration
Scope: FLOC*, Brand3, branding, project, case-study, client, and design-project knowledge structures

## Executive Summary

The connected Notion workspace contains useful contextual material for Brand3 perceptual vocabulary and report generation, but it should be treated as a curated reference layer rather than ingested directly.

The strongest candidates are:

- FLOC*Brain: internal terminology, service model, BrandOS / Brand3 methodology, writing conventions, and process language.
- FLOC*Ops: operational hub linking project, account, opportunity, task, contact, team, and social planning databases.
- Projects Database: structured project metadata with service tags, client/account relation, status, start/due dates, Figma/Pinterest links, and budget fields.
- Accounts database: client/brand-level metadata, especially industry/sector, website, status, preview, and relations to opportunities/contacts.
- Social Media Planning database: case-study announcement copy and public-facing project summaries, with asset links and platform/status fields.
- Case-study pages: compact descriptions of project context, strategic framing, deliverables, outcomes, and public links.

No Notion content was edited, moved, created, deleted, or ingested.

## Main Structures Found

### FLOC*Space

Observed as the top-level ancestor for the operational and knowledge pages. It appears to contain the FLOC* operational and knowledge ecosystem.

### FLOC*Ops

Role: operational hub.

Observed linked structures:

- Projects Database
- Ongoing Projects
- Opportunities
- FLOC*Team
- Accounts
- Contacts
- account-communication page

Usefulness for Brand3:

- High for identifying where project, client, service, status, and asset links live.
- Medium for vocabulary/report generation by itself, because most useful context sits in related databases and project pages.
- Sensitive operational CRM data exists here, so ingestion should be selective and explicitly filtered.

### FLOC*Brain

Role: shared internal knowledge base.

Observed child pages:

- What FLOC* is
- Core team
- BrandOS framework
- Glossary and conventions
- Instructions for Claude
- Decision changelog
- Services
- Distribution / Contra
- Events and networking
- Skills and team-brain pages

Usefulness for Brand3:

- High for report voice, naming conventions, conceptual vocabulary, and methodology.
- High for mapping Brand3 / BrandOS language to the report generator.
- Should be used as a style and method reference, not as raw report content.

### BrandOS Framework Page

Role: methodology description.

Observed structure:

- What BrandOS is
- Current state
- Brand3 philosophy
- Three framework phases
- How services apply the framework
- Tooling
- Visual-context pipeline
- Future direction

Candidate use:

- Report voice: translate Brand3 from static audit language to evolution-oriented language.
- Perceptual vocabulary: terms around brand DNA, territory, tone, visual direction, system, normalization, evolution, and launch readiness.
- Tension patterns: static delivery versus living/evolving brand systems; generic AI output versus curated visual context; human curation versus model generation.

### Glossary and Conventions Page

Role: terminology and writing rules.

Observed structure:

- FLOC* terminology
- BrandOS / Brand3 / BRND naming
- internal area names
- service terms
- writing conventions
- tone guidance

Candidate use:

- Report voice: direct, professional, close, non-corporate language.
- Perceptual vocabulary: controlled naming and terminology.
- System guardrails: avoid drifting between FLOC*, Brand3, BrandOS, and BRND meanings.

### Services Page

Role: service model overview.

Observed structure:

- Go Sprint
- Go to Market
- Go Beyond
- comparison table by audience, duration, web scope, strategy depth, post-delivery model, price band, signal, and example cases

Candidate use:

- Case examples: map project maturity to strategic needs.
- Report voice: describe brand readiness by stage and ambition.
- Tension patterns: early-stage seriousness, fundraising readiness, durability/scale.

### Projects Database

Role: central project index.

Observed schema fields:

- Title
- Account
- Opportunity
- Services
- Status
- Start Date
- Due Date
- Leaders
- Budget
- Lead
- Notion Link
- Preview
- Pinterest
- Pinterest Link
- WORK Figma File
- Remaining days formula

Observed service options include:

- Brand Identity
- Brand Strategy
- Brand3
- Branding in Public
- Branding Lite
- Design Sprint
- Digital Product
- Evolution Guardian
- Identity Pack
- Landing Lite
- Naming
- Product Guardian
- Side Project
- Starter-Kit
- UX/UI Website
- UX/UI MVP
- Website Evolution
- Website Pack

Candidate use:

- Project name: `Title`
- Client/brand: relation via `Account`
- Type of work: `Services`
- Deliverables/assets: Figma, Pinterest, Preview, Notion Link, related page content
- Timeline context: Start Date, Due Date, Status
- Not ideal for: brief/strategy/visual identity prose unless project pages are fetched selectively.

### Accounts Database

Role: client/brand index.

Observed schema fields:

- Account
- Company Name
- Industry
- Website
- Status
- Location / City
- Preview
- Opportunities relation
- Contacts relation
- legal/admin fields

Observed industry options include broad categories such as fintech, crypto, gaming, education, fashion, media, community, IT, development, DeFi, CeFi, blockchain services, art, tourism, agency, and related sectors.

Candidate use:

- Client/brand: `Account`, `Company Name`
- Sector: `Industry`
- Public context: `Website`
- Visual reference: `Preview`
- Avoid ingesting legal/admin fields.

### Opportunities Database

Role: sales/proposal CRM.

Observed schema fields:

- Opportunity
- Account
- Contacts
- Stage
- Source
- Priority
- Estimated budget
- Website
- Mail thread
- Leader
- Last contact / Date sent / Close Date
- Loss Reason

Candidate use:

- Limited. Useful for understanding proposal/project lifecycle and source channels.
- Do not use for perceptual vocabulary by default because it contains CRM-sensitive fields and sales-state metadata.
- Possible exception: sanitized, aggregate patterns about project type, stage, and source if needed.

### Ongoing Projects Database

Role: task/calendar layer.

Observed schema fields:

- Task
- Projects Database relation
- Project
- Type
- Type Task
- Status
- Date
- Responsable
- Priority
- Link
- Github
- web
- rollups for project title and Figma file

Candidate use:

- Low for vocabulary/report generation.
- Useful only to locate current work or project pages.
- Avoid ingestion; operational task details are not necessary for Brand3 report language.

### Social Media Planning Database

Role: content calendar and case-study publication planner.

Observed schema fields:

- Name
- Type
- Networks
- Status
- Date
- Person
- DRIVE - ASSETS
- FIGMA - ASSETS
- URL
- Inflynce Invest.

Observed relevant page types include case studies, WorkFLOC*, Brand3, BRND, FLOC*Packs, and platform-specific posts.

Candidate use:

- Public-facing report voice and case-study summaries.
- Case examples from already-published or externally intended content.
- Tension patterns and verbal framing from concise launch copy.
- Should be filtered to public/published statuses and stripped of people, investment, and internal scheduling metadata.

## Candidate Project Fields

The workspace appears to support the requested candidate fields as follows:

| Candidate field | Notion source | Notes |
| --- | --- | --- |
| Project name | Projects Database `Title`; Social Media Planning `Name`; page title | Strong support |
| Client/brand | Projects Database `Account`; Accounts `Account` / `Company Name`; page title | Strong support |
| Sector | Accounts `Industry` | Strong support |
| Type of work | Projects Database `Services`; Social Media Planning `Type`; Services page | Strong support |
| Brief | Project/proposal pages; case-study pages | Available, but requires selective page fetch |
| Strategy | Brand strategy pages; BrandOS framework; case-study pages | Strong candidate, should be curated |
| Visual identity | Project pages; Figma links; Pinterest links; case-study copy | Available, but assets should not be ingested yet |
| Deliverables | Projects `Services`; service pages; case-study summaries | Strong support |
| Notes | Page body content; Ongoing Projects tasks | Available, but operational notes may be sensitive |
| Links/assets | Figma, Drive, Pinterest, Website, URL fields | Strong support, but links should be treated as pointers only |

## Possible Brand3 Uses

### Surface Perception Language

Useful sources:

- case-study pages
- BrandOS framework
- project pages with visual strategy
- public social posts
- Figma/Pinterest links as pointers, not ingest targets

Potential contribution:

- language for describing first-glance visual signals
- density, texture, composition, palette, motion, editorial style, and brand-system behavior
- distinction between visual direction, identity system, and launch surface

Recommended constraint:

- Use only public/published case-study content or explicitly approved project pages.

### Report Voice

Useful sources:

- FLOC*Brain glossary and conventions
- BrandOS framework
- Services page
- public case-study copy

Potential contribution:

- direct, professional, close tone
- less generic audit phrasing
- stronger observation-to-implication language
- stronger language around evolution, readiness, system maturity, and brand behavior

Recommended constraint:

- Convert into a compact voice guide, not a raw corpus.

### Perceptual Vocabulary

Useful sources:

- BrandOS framework visual-context pipeline
- case-study summaries
- design/project pages
- glossary terms

Potential vocabulary domains:

- brand DNA
- territory
- tone
- visual direction
- system
- normalization
- evolution
- launch readiness
- identity behavior
- strategic clarity
- narrative focus
- visual soul / visual foundation
- worldbuilding, product clarity, and public debut language

Recommended constraint:

- Normalize vocabulary into controlled terms with definitions and banned/avoid alternatives.

### Tension Patterns

Useful sources:

- BrandOS framework
- services comparison
- case-study pages
- proposal / strategy pages

Observed candidate patterns:

- static brand delivery versus living/evolving brand system
- generic AI output versus curated visual context
- early-stage existence signal versus fundraising-ready credibility
- visual expression versus strategic clarity
- internal product maturity versus external public signal
- playful/emotional universe versus serious product trust
- speed of sprint delivery versus long-term system durability

Recommended constraint:

- Store as abstract patterns, not client-specific details.

### Case Examples

Useful sources:

- Social Media Planning case-study pages
- Services page example rows
- published work links

Observed examples include public-facing case-study pages such as Alchemain, CHARMS, DEGEN, ATH21, AUT, and FOUNT.

Recommended constraint:

- Use case examples only when public/published and summarize at high level.
- Avoid copying client-sensitive internal notes, CRM status, budgets, people, or private links.

## Ingestion Recommendation

Do not ingest anything yet.

If this workspace is later used for Brand3, use a staged ingestion model:

1. Schema-only inventory.
2. User-approved source allowlist.
3. Public/published content filter.
4. PII/client-sensitive field exclusion.
5. Abstracted vocabulary and pattern extraction.
6. Manual review before adding anything to Brand3 prompts, fallback prose, or report generation.

Recommended allowlist candidates:

- FLOC*Brain glossary/conventions
- FLOC*Brain BrandOS framework
- FLOC*Brain services overview
- published case-study pages from Social Media Planning
- selected public project pages with explicit approval

Recommended exclusions:

- Contacts
- FLOC*Team
- legal/admin account fields
- mail threads
- budgets unless used only as private operational metadata
- loss reasons and sales-stage details
- people/person/responsable fields
- unpublished proposal pages unless explicitly approved
- raw Drive/Figma/Pinterest assets until a separate asset policy exists

## Read-Only Evidence Log

Read-only Notion tools used:

- workspace searches for FLOC*, Brand3, branding, case studies, project fields, and perceptual vocabulary terms
- page fetches for FLOC*Ops, FLOC*Brain, BrandOS framework, Glossary and Conventions, Services, and representative case-study pages
- data-source fetches for Projects Database, Ongoing Projects, Opportunities, Accounts, and Social Media Planning

No write-capable Notion tools were used.
