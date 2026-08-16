# EU AI Act — Guidelines & Compliance Overview
> Secondary Knowledge Base Document  
> Sources: Regulation (EU) 2024/1689 | European Commission AI Office | artificialintelligenceact.eu | DLA Piper | GDPR Local | European Parliament | ISACA  
> Last reviewed: May 2026

---

## 1. What Is the EU AI Act?

The EU AI Act (Regulation (EU) 2024/1689) is the world's first comprehensive legal framework for artificial intelligence. It establishes harmonised rules across the European Union for the development, deployment, and use of AI systems, with the aim of ensuring trustworthy, human-centric AI while protecting fundamental rights.

**Scope:** The Act applies to any organisation placing AI systems on the EU market or whose AI system outputs are used in the EU — regardless of where the organisation is based. This means global companies are subject to compliance requirements if they operate in or serve the EU.

**Formal citation:** Regulation (EU) 2024/1689 of the European Parliament and of the Council laying down harmonised rules on artificial intelligence.

---

## 2. Implementation Timeline

The Act uses a phased rollout — obligations became active at different dates depending on risk level.

| Date | What Applies |
|---|---|
| **1 August 2024** | Act enters into force. EU AI Office and AI Board established. |
| **2 February 2025** | Prohibited AI practices banned. AI literacy obligations (Article 4) take effect for all providers and deployers. |
| **2 August 2025** | Obligations for General Purpose AI (GPAI) model providers take effect. Penalty regime activated. Governance infrastructure (notified bodies, conformity assessment system) must be operational. |
| **2 August 2026** | Full applicability. Remaining obligations for high-risk AI system providers and deployers take effect. Majority of enforcement powers apply. |
| **2 August 2027** | Obligations for AI systems that are safety components of products requiring third-party conformity assessments under existing EU law. |
| **31 December 2030** | AI systems that are components of large-scale IT systems listed in Annex X must be compliant. |

---

## 3. The Four-Tier Risk Framework

The AI Act categorises all AI systems into one of four risk levels. Obligations and penalties scale with risk.

### Tier 1: Unacceptable Risk — Prohibited
Banned outright from 2 February 2025. These practices are considered incompatible with EU values and fundamental rights.

**Prohibited AI practices include:**
- **Manipulative AI** — subliminal or deceptive techniques that distort individual decision-making and cause significant harm
- **Exploitative AI** — exploiting vulnerabilities of individuals or groups (age, disability, socio-economic status) to materially distort behaviour
- **Social scoring** — classifying people based on behaviour, socio-economic status, or personal characteristics by public authorities
- **Real-time remote biometric identification** in publicly accessible spaces (narrow law enforcement exceptions exist, requiring judicial authorisation)
- **Emotion recognition** in workplace and educational settings
- **Cognitive behavioural manipulation** of specific vulnerable groups (e.g. voice-activated toys encouraging dangerous behaviour in children)
- **Biometric categorisation** inferring sensitive characteristics (race, political opinions, sexual orientation)
- **Predictive policing** based solely on profiling without objective evidence

**Penalty:** Up to **€35 million or 7% of global annual turnover** (whichever is higher).

---

### Tier 2: High Risk — Strict Compliance Required
AI systems that could significantly impact health, safety, or fundamental rights. Full compliance required from **2 August 2026**.

**High-risk use cases include (Annex III):**
- AI used in **education and vocational training** — determining access to education, assessing students, evaluating learning outcomes
- AI used in **employment** — recruitment, CV screening, job matching, performance evaluation, promotion decisions
- AI in **critical infrastructure** — transport, utilities, water, gas, electricity
- AI in **healthcare** — medical devices, diagnostics
- AI in **law enforcement** — polygraphs, risk assessments, deepfake detection
- AI in **border control and migration** — asylum processing, visa applications
- AI in **administration of justice** — legal research, dispute resolution assistance
- AI in **essential private and public services** — credit scoring, insurance, emergency dispatch

**Key obligations for HIGH-RISK AI providers:**
- Establish a **quality management system**
- Conduct **conformity assessment** before market placement
- Maintain comprehensive **technical documentation**
- Design systems for **automatic event logging** (audit trails)
- Ensure **transparency** — provide instructions for use to deployers
- Achieve appropriate **accuracy, robustness, and cybersecurity** standards
- Register in the **EU AI database** before deployment
- Implement **post-market monitoring**
- Report **serious incidents and malfunctions** to authorities
- Affix **CE marking** to demonstrate compliance

**Key obligations for HIGH-RISK AI deployers:**
- Use the system **in accordance with provider instructions**
- Assign qualified **human oversight** — competent, trained persons with authority to intervene
- Ensure **input data is relevant and sufficiently representative**
- Keep automatically generated **logs for at least 6 months**
- **Inform workers** before deploying systems that affect them
- Conduct a **Fundamental Rights Impact Assessment (FRIA)** before deployment
- Do not use systems **not registered in the EU database**
- Report incidents to the provider and relevant authorities

**Penalty:** Up to **€15 million or 3% of global annual turnover** (whichever is higher).

---

### Tier 3: Limited Risk — Transparency Obligations Only
Systems with specific interaction or content generation risks. Lighter touch obligations.

**Examples:** Chatbots, deepfakes, AI-generated content, emotion recognition (outside banned contexts).

**Obligations:**
- Developers and deployers must ensure **end-users know they are interacting with AI**
- Deepfakes and AI-generated content must be **disclosed as such**
- Emotion recognition systems must **notify individuals** being analysed

---

### Tier 4: Minimal Risk — No Additional Requirements
The majority of AI applications fall here. No regulatory obligations beyond general EU law.

**Examples:** Spam filters, AI-enabled video games, basic recommendation systems, most productivity tools.

Organisations must still ensure that relevant personnel have sufficient **AI literacy** (Article 4 applies to all AI deployers regardless of risk tier).

---

## 4. General Purpose AI (GPAI) Models

GPAI models are treated separately from the risk-tier system. They are AI models capable of performing a wide range of distinct tasks — large language models (LLMs) are the primary example.

GPAI obligations came into force on **2 August 2025**.

### All GPAI Model Providers Must:
- Create and maintain **technical documentation** (training processes, architecture, capabilities)
- Provide **instructions for use** to downstream AI system providers
- Comply with **EU Copyright Directive**
- Publish a **public summary of training data content**

### GPAI Models with Systemic Risk (additional obligations)
A GPAI model is considered to present **systemic risk** if the cumulative compute used for training exceeds **10²⁵ floating point operations (FLOPs)**. Providers must notify the Commission within 2 weeks of meeting this threshold.

**Additional obligations for systemic-risk GPAI providers:**
- Conduct **model evaluations and adversarial testing** (red-teaming)
- **Track and report serious incidents**
- Ensure **cybersecurity protections**
- Assess and **mitigate systemic risks**

**Open-source exception:** Free and open-licence GPAI models only need to comply with copyright requirements and publish the training data summary — unless they present systemic risk.

### Key July 2025 Commission Guidelines for GPAI
The European Commission published three key instruments in July 2025:
1. **Guidelines on the scope of obligations for GPAI model providers** — clarifying who must comply and what is covered
2. **GPAI Code of Practice** — voluntary compliance tool providing practical guidance on transparency, copyright, and safety
3. **Template for public summary of training content** — standardised format for disclosing training data sources

---

## 5. AI Literacy Obligation (Article 4) — Applies to All

In force since **2 February 2025**. This applies to all organisations deploying or developing AI, regardless of the risk tier of the systems they use.

**What "AI literacy" means:**
- The ability to make **informed decisions** regarding AI deployment and its risks
- Understanding the **potential harms** AI systems can cause
- Ability to handle AI systems **responsibly** in their operational context

**What organisations must do:**
- Ensure all individuals **involved in the operation or use** of AI systems have sufficient skills, knowledge, and understanding
- Training must be **tailored** to: the technical expertise of staff, the context of deployment, and the characteristics of individuals or groups affected by the AI

**Note:** The Act does not specify penalties directly for Article 4 non-compliance, but regulators are expected to treat insufficient AI literacy training as an **aggravating factor** in penalty determinations for other violations.

---

## 6. Key Roles Defined by the Act

Understanding which role your organisation plays determines your obligations.

| Role | Definition |
|---|---|
| **Provider** | Develops an AI system and places it on the market or puts it into service (includes in-house development for own use) |
| **Deployer** | Uses an AI system in a professional context (previously called "user" in draft versions) |
| **Importer** | Places an AI system from a third country on the EU market |
| **Distributor** | Makes an AI system available on the EU market without altering it |
| **Operator** | Umbrella term covering providers, deployers, importers, and distributors |

**Important:** If a deployer modifies an AI system substantially, they become a **provider** and take on provider obligations.

---

## 7. Penalties Summary

| Violation | Maximum Fine |
|---|---|
| Prohibited AI practices (Tier 1) | €35 million **or** 7% of global annual turnover (whichever is higher) |
| Other obligations (high-risk, transparency, GPAI) | €15 million **or** 3% of global annual turnover |
| Supplying incorrect/misleading information to authorities | €7.5 million **or** 1% of global annual turnover |

**Note:** Penalty provisions for GPAI model providers are postponed to **2 August 2026**, aligned with the full enforcement powers taking effect. National authorities (not just the EU AI Office) can impose fines on operators. Some Member States are implementing additional national legislation — Italy's Law No. 132/2025 (in force October 2025) includes criminal penalties for deepfake dissemination (1–5 years imprisonment).

Penalties under the AI Act **exceed those of GDPR** in their maximum thresholds.

---

## 8. Governance Structure

| Body | Role |
|---|---|
| **EU AI Office** | Operational from 2 August 2025. Established within the European Commission. Oversees GPAI models, supports implementation, and coordinates enforcement. |
| **AI Board** | Representatives from Member States. Advises the Commission and coordinates national enforcement. |
| **Scientific Panel** | Independent experts focused on GPAI systemic risks. Can issue "qualified alerts" to the AI Office. |
| **Advisory Forum** | Stakeholder representatives (industry, civil society, academia). Provides non-binding advice. |
| **National Competent Authorities** | Each Member State designates national authorities for market surveillance, investigation, and enforcement of high-risk AI obligations. |

---

## 9. Relevance to the Education Sector

The EU AI Act specifically identifies **education and vocational training** as a high-risk domain under Annex III. This has direct implications for universities and EdTech providers.

**High-risk AI uses in education include:**
- AI systems that **determine access to educational institutions** (admissions scoring, ranking)
- AI that **assesses or evaluates students** (automated grading, learning performance scoring)
- AI that **determines the course of someone's professional life** through educational pathways
- AI tools used in **recruitment within educational institutions**

**What this means for a deploying organisation:**
- Using AI to rank or score applicants = likely **high-risk** — requires conformity assessment, technical documentation, human oversight, and FRIA
- Using AI chatbots for student queries = **limited risk** — transparency obligation only (disclose it's AI)
- Using AI tools for marketing personalisation = likely **minimal risk** — no additional obligations beyond AI literacy
- Using AI for staff recruitment screening = **high-risk** — employment category under Annex III

**AI literacy obligation applies universally** — An organisation deploying AI systems, like any other, must ensure staff have sufficient understanding of the AI systems they use, their risks, and how to operate them responsibly.

---

## 10. Practical Compliance Checklist

For organisations deploying AI systems in the EU, recommended immediate actions:

- [ ] **Inventory all AI systems** in use — classify each by risk tier
- [ ] **Identify your role** for each system (provider vs. deployer)
- [ ] **Implement AI literacy training** for all staff involved in AI operation (required since Feb 2025)
- [ ] **Discontinue any prohibited AI practices** (required since Feb 2025)
- [ ] **For high-risk systems:** Begin conformity assessment, documentation, and FRIA preparation ahead of August 2026 deadline
- [ ] **For GPAI model providers:** Ensure technical documentation, instructions for use, copyright compliance, and training data summary are in place (required since Aug 2025)
- [ ] **Set up logging and incident reporting** procedures for high-risk deployments
- [ ] **Monitor national implementing legislation** — Member States are adding their own penalty and enforcement rules
- [ ] **Assign human oversight** roles for any high-risk AI systems
- [ ] **Register high-risk systems** in the EU AI database before deployment (required from Aug 2026)

---

## 11. Key Resources

| Resource | URL |
|---|---|
| Official EU AI Act text | eur-lex.europa.eu |
| EU AI Office | digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai |
| AI Act independent tracker | artificialintelligenceact.eu |
| GPAI Guidelines (July 2025) | digital-strategy.ec.europa.eu/en/library/guidelines-scope-obligations-gpai |
| AI Act Compliance Checker (SMEs) | artificialintelligenceact.eu/assessment/eu-ai-act-compliance-checker |
| AI Act Service Desk | Available via EU AI Office website |

---

*Document type: Secondary Knowledge Base — Regulatory & Compliance Context*  
*Next review: August 2026 (full applicability date)*
