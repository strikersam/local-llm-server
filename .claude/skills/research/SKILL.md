# Skill: Research

## Purpose
Conduct structured, systematic research on any topic — synthesizing sources, extracting key findings, identifying gaps, and producing a clear research brief. Designed for both technical and non-technical research tasks.

## When to Use
- Investigating a new technology, library, or approach before implementation
- Competitive analysis or market research
- Literature review before writing documentation or proposals
- Due diligence on a tool, service, or vendor
- Pre-planning research before starting a feature

## Instructions

### Step 1: Define the Research Question
Before searching, clarify:
- **Primary question**: What is the core thing you need to know?
- **Scope**: How deep? How broad? Time constraints?
- **Output type**: Decision brief? Technical summary? Comparison table?
- **Audience**: Who will read this? What do they already know?

### Step 2: Identify Source Categories
Structure the research across these source types:
- **Official docs / primary sources** — authoritative, current
- **Community knowledge** — GitHub issues, forums, Stack Overflow
- **Comparisons / reviews** — third-party analysis
- **Case studies / examples** — real-world usage
- **Critiques / limitations** — known problems, caveats

### Step 3: Extract & Synthesize
For each source:
- Record the key claim or finding
- Note the source credibility and recency
- Flag contradictions between sources
- Identify consensus vs. contested points

### Step 4: Identify Gaps
Document what you **couldn't find** or what remains **uncertain**:
- Missing data points
- Questions that need primary research (e.g., direct testing)
- Assumptions that need validation

### Step 5: Produce Research Brief
```markdown
## Research Brief: [Topic]
**Date:** [Date]
**Researcher:** Claude
**Question:** [Primary research question]

---

### Executive Summary
[2–3 sentences: what was found and what it means]

### Key Findings
1. [Finding] — Source: [URL or description] (Confidence: High/Medium/Low)
2. ...

### Comparison / Options (if applicable)
| Option | Pros | Cons | Best For |
|--------|------|------|----------|
| ...    | ...  | ...  | ...      |

### Gaps & Uncertainties
- [What remains unknown]
- [What needs direct testing]

### Recommendation
[Clear recommendation based on findings, with rationale]

### Sources
- [Source 1]: [URL or description]
- [Source 2]: ...
```

## Example Prompt to Trigger
```
/research
Topic: [what to research]
Question: [specific question to answer]
Output: [decision brief / comparison / summary]
```

## Output Format
- Structured research brief in markdown
- Executive summary at the top
- Comparison tables where options exist
- Clear recommendation with rationale
- Sources listed at the bottom

## Notes
- Always distinguish between **facts** (verifiable), **claims** (stated by sources), and **opinions** (subjective assessments)
- Flag information older than 2 years as potentially outdated
- If web browsing is available, use it; otherwise synthesize from provided content
- For technical research in this repo, consider saving to `docs/research/[topic]-YYYY-MM-DD.md`
- Cross-reference with existing repo skills (e.g., use `insights` skill after research to extract patterns)
