**Requirements (draft) v1 1/3/2026**

**1. Overview**

Shanghan-TCM Evidence is a small, domain-specific AI project initiated
by a nonprofit organization (WASFS). The goal is to build a secure,
expert-level assistant centered on classical Traditional Chinese
Medicine (TCM), starting with the Treatise on Cold Damage (Shang Han
Lun). The system will combine:

- Curated classical texts and commentaries.

- Structured formula knowledge.

- Expert-reviewed clinical cases mapped to those texts and formulas.

Primary use cases:

- Clinical decision support for trained TCM professionals.

- Learning and teaching support for students and practitioners.

- Bilingual (Chinese--English) access for users in North America and
  worldwide.

**2. Core Knowledge Base (Internal, Not User-Visible)**

This internal corpus is the "engine" of the system and must remain
hidden from end-users. It will be used for retrieval, reasoning, and
training.

1.  Classical texts and annotations

    - Start with Shang Han Lun; later optionally extend to Jin Gui Yao
      Lue, Wen Bing, etc.

    - Content includes:

      - Original classical Chinese text and, where available,
        authoritative Chinese and English translations.

      - (Only seen by AI) Expert annotations: clause explanations,
        pattern analysis, formula-symptom mapping, and pathomechanism
        notes.

    - All entries must have clear source, edition, and version metadata
      for auditability.

2.  Formula and structured TCM knowledge

    - For each formula related to Shang Han Lun clauses:

      - Name, source citation, composition, roles of ingredients
        (jun/chen/zuo/shi), functions, indications, modifications, and
        cautions.

    - Create structured links: symptom clusters / patterns → clauses →
      formulas → common modifications.

    - This structure is critical for safe and explainable formula
      suggestions.

3.  Clinical cases and outcome evidence

    - (Only seen by AI) Expert-submitted, professionally reviewed case
      records that:

      - Are fully de-identified and privacy-safe.

      - Include chief complaint, four examinations (including tongue and
        pulse), pattern differentiation, formula used, follow-up and
        outcome.

    - Each case is explicitly linked to:

      - One or more classical clauses.

      - Core formula(s) and modifications.

    - Cases undergo review by an expert panel before entering the
      internal knowledge base, and can be graded (e.g., high-quality
      evidence, empirical experience, etc.).

4.  Visibility and access control

    - Raw texts, full annotations, and full case records are never shown
      directly to end-users.

    - The model's outputs must be synthesized, privacy-safe, and
      non-identifiable.

    - Internal data should be stored with versioning and access logs to
      support future audits.

**3. Conversational Clinical Support**

The system provides a chat-based interface for TCM-savvy users (licensed
practitioners or advanced students). It is a decision-support and
learning tool, not a diagnostic engine.

1.  Input modality

    - Users can describe:

      - Chief complaints and symptom narratives.

      - Tongue and pulse features.

      - Relevant history, constitution, cold/heat, deficiency/excess,
        etc.

    - System should handle free-text in Chinese or English and can ask
      follow-up questions to clarify missing key information.

2.  Reasoning and retrieval

    - The system should:

      - Normalize user input into TCM patterns and key features.

      - Retrieve and rank relevant clauses, formulas, and internal cases
        from the knowledge base.

      - Produce a small set of candidate formulas or formula directions
        with clear reasoning.

3.  Output and safety requirements

    - Outputs may include:

      - 1--3 candidate formulas or directions, with short explanations
        of pattern reasoning and classical basis (e.g., reference to
        clause ideas, without exposing full raw text).

      - Suggestions for further assessment questions a practitioner
        might consider.

    - Mandatory safety rules:

      - Always display a clear disclaimer: the system is for education
        and professional support only, not for layperson self-diagnosis
        or emergency use.

      - For high-risk contexts (pregnancy, pediatrics, severe acute
        conditions, red-flag symptoms), the system must advise immediate
        in-person medical evaluation and avoid detailed self-medication
        guidance.

      - The system must handle "insufficient information" cases by
        explicitly stating that it cannot provide a reliable suggestion.

4.  Target users and permissions

    - Advanced clinical suggestions (pattern--formula support) should be
      restricted to authenticated professional users (licensed
      acupuncturists/TCM doctors or vetted advanced students).

    - General educational explanations of TCM theory may be more broadly
      accessible.

**4. Expert Case Contribution Workflow**

The platform should support a collaborative workflow for expert users to
contribute de-identified clinical cases, enriching the knowledge base
over time.

1.  Authenticated expert users

    - A role-based access system where "approved contributors" can:

      - Submit cases using a structured template.

      - View the status of their submissions (pending review, accepted,
        rejected, revised).

2.  Case submission template

    - Fields may include:

      - Patient demographics (highly abstracted, non-identifiable).

      - Chief complaint, history, four examinations (tongue, pulse,
        etc.).

      - Pattern differentiation, reasoning notes.

      - Prescription details: base formula, modifications, course of
        treatment.

      - Outcome and follow-up.

3.  Review and integration

    - All cases go through an administrative/expert review process for:

      - Professional quality and internal consistency.

      - Compliance, privacy, and de-identification.

      - Standardization of patterns, clause links, and formula labels.

    - Only approved cases enter the internal knowledge base and can
      influence retrieval and model behavior.

4.  Optional incentives

    - The system may provide non-monetary incentives:

      - Access to advanced features.

      - Recognition in internal or academic contexts (e.g., aggregated
        contributor lists, with consent).

**5. Learning and Teaching Functions**

Beyond clinical support, the system should act as a bilingual study
assistant.

1.  Clause and formula exploration

    - Users can ask:

      - "Show me the main clauses and formulas related to
        \[pattern/symptom description\]."

      - "Help me study Gui Zhi Tang and its classical basis."

    - The system should:

      - Locate relevant clauses and formulas.

      - Provide summarized explanations and teaching-oriented notes in
        the chosen language.

      - Optionally surface anonymized patterns and outcomes from the
        internal case base in a generalized way.

2.  Bilingual learning

    - All core content (clause summaries, formula explanations, pattern
      descriptions) should support both Chinese and English.

    - Users can choose:

      - Chinese-first with English support.

      - English-first with key Chinese terms and pinyin preserved.

3.  Educational scenarios

    - Designed to support:

      - Study groups and reading circles using Shang Han Lun.

      - Case-based learning for students.

      - Instructor-led teaching where the tool can be used live in
        classroom or webinar settings.

**6. Product Structure, Access and Business Model**

This is a nonprofit project but will likely adopt a mixed free/paid
model to sustain development and infrastructure.

1.  Nonprofit positioning

    - Operated by a nonprofit (WASFS), with focus on education,
      research, and professional support.

    - Pricing and access control should reflect a mission-driven, not
      purely commercial, orientation.

2.  Example access tiers

    - Free tier:

      - Basic TCM conceptual Q&A.

      - Limited clause/formula study features (e.g., rate-limited
        queries).

    - Professional / paid tier:

      - Full access to clinical decision-support features
        (pattern--formula reasoning, more detailed educational
        explanations).

      - Access to advanced teaching tools and curated learning paths.

    - Contributor / institutional tier (optional):

      - Additional tools for institutions or expert groups contributing
        cases and annotations.

3.  Compliance and privacy

    - Main user base expected in North America, with global reach.

    - The system must:

      - Apply strong de-identification and data protection practices.

      - Respect applicable regional regulations for health-related data
        and AI tools.

    - All logging and monitoring should be designed to protect user
      confidentiality.

**7. Language and Internationalization**

1.  Bilingual UX

    - User interface, messages, and help text must support full Chinese
      and English localization.

    - Users can switch languages at any time; the system should remember
      preferences per user account where possible.

2.  Terminology management

    - Maintain a standardized bilingual terminology glossary for:

      - Key TCM concepts (yin/yang, exterior/interior, etc.).

      - Formula names, ingredient names, and preparation methods.

    - This glossary should be consistently used across:

      - UI text.

      - Generated outputs.

      - Internal data tagging.

3.  Regional context

    - For formula ingredients and dosage forms, provide clear notes
      when:

      - Herbs or preparations are not readily available or are regulated
        in certain regions.

      - Western unit conversions or safety notes are needed for clarity.
