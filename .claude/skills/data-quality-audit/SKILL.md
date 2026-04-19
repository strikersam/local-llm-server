# Skill: data-quality-audit

## Purpose
Audit training data and tokenizer pipelines for quality issues that silently degrade LLM training. Data problems are the #1 underdiagnosed cause of poor model performance — most tutorials skip this entirely.

## Trigger
Use when:
- Preparing a dataset for LLM pretraining or fine-tuning
- Model outputs seem degenerate (repetition, wrong language, truncated responses)
- Tokenizer was recently changed or vocabulary was updated
- Merging datasets from multiple sources

## Background (Why This Matters)
From LLM-from-scratch practitioners:

> "I spent two weeks debugging a model that kept outputting garbled text. The issue was 0.3% of my training data had HTML entities that the tokenizer split into hundreds of tokens, dominating the loss landscape."

Key lessons:
1. **Token length distribution matters** — outlier-length documents dominate gradient updates disproportionately
2. **Deduplication is not optional** — even 1% duplicate data causes memorization artifacts
3. **Tokenizer fertility (chars/token)** should be consistent — sudden drops indicate encoding bugs
4. **BOS/EOS tokens must be consistent** — missing end tokens cause the model to never learn to stop
5. **Language distribution** — unlabeled multilingual data causes unexpected behavior in monolingual models

## Usage
```
/data-quality-audit [dataset_path_or_glob] [--tokenizer model_name_or_path] [--sample 10000]
```

## Checks Performed

### 1. Token Length Distribution
```
P5:   [tokens]
P50:  [tokens]  
P95:  [tokens]
P99:  [tokens]
MAX:  [tokens]  ← flag if >> context_window

WARNING: Documents at P99+ length will be truncated, losing their tail content.
         Consider splitting or filtering documents > 0.8 * context_window.
```

### 2. Deduplication Check
- Exact match on first 64 tokens (cheap, catches near-duplicates)
- MinHash LSH for near-duplicate detection (sampled)
- Reports estimated duplicate % in dataset

### 3. Tokenizer Fertility Check
```python
# chars_per_token should be stable across document types
# English prose: ~4.0 chars/token
# Code: ~3.0-3.5 chars/token
# Sudden drop to <2.0 suggests tokenizer is splitting on noise
fertility = total_chars / total_tokens
```

### 4. Special Token Consistency
- Every document has BOS token at start
- Every document has EOS token at end
- No document contains raw `<unk>` tokens (tokenizer coverage issue)
- No document contains padding tokens mid-sequence

### 5. Language Detection (if langdetect available)
- Reports language distribution
- Flags documents with mixed-language content
- Warns if distribution differs from intended training target

### 6. Content Quality Signals
- Repetition ratio: flag documents where any 4-gram repeats >5x
- Average line length: flag documents with lines >500 chars (likely minified/encoded data)
- Punctuation density: flag documents with <1% punctuation (may be code or structured data)
- HTML/XML tag density: flag documents with >5% tag content

## Output Format
```
=== Data Quality Audit Report ===
Dataset: [path]
Sampled: [N] documents

[PASS/WARN/FAIL] Token Length Distribution
[PASS/WARN/FAIL] Deduplication
[PASS/WARN/FAIL] Tokenizer Fertility  
[PASS/WARN/FAIL] Special Token Consistency
[PASS/WARN/FAIL] Language Distribution
[PASS/WARN/FAIL] Content Quality

CRITICAL ISSUES: N
WARNINGS: N

Estimated affected documents: [N] ([%] of dataset)

Recommended Actions:
1. Filter documents where token_length > [threshold]
2. Remove [N] near-duplicate clusters
3. [other specific actions]
```

## Common Dataset Issues by Source

| Source         | Common Issue                              | Fix                              |
|----------------|-------------------------------------------|----------------------------------|
| Common Crawl   | HTML artifacts, boilerplate               | trafilatura extraction           |
| GitHub         | Minified JS/CSS, generated files          | Filter by file extension         |
| Wikipedia      | Citation markup, table syntax             | WikiExtractor preprocessing      |
| Books          | Gutenberg headers/footers                 | Trim first/last 1000 chars       |
| Reddit         | Deleted/removed comments ([deleted])      | Filter short or placeholder text |
| PDFs           | OCR noise, column merging artifacts       | Quality score threshold          |

## Integration Points
- Pairs with `dependency-audit` for checking data pipeline library versions
- Pairs with `training-stability-monitor` when data issues cause training instability
- Pairs with `insights` for tracking data quality metrics across dataset versions

## Notes
- This skill is **read-only** — it analyzes but does not modify data
- For large datasets (>100GB), always use `--sample` to get fast estimates
- Re-run after any tokenizer change — fertility and special token checks are tokenizer-dependent
