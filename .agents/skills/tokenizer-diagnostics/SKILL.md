# Skill: tokenizer-diagnostics

## Purpose
Deep-dive diagnostics for tokenizer behavior in LLM training and inference. Tokenizer bugs are uniquely dangerous because they're silent — the model trains fine, but on subtly wrong data.

## Trigger
Use when:
- Switching tokenizers between training phases
- Seeing unexpected token counts for known inputs
- Model performs poorly on specific input types (numbers, code, non-English)
- Vocabulary size was changed and you need to verify embedding alignment

## Background
From LLM-from-scratch practitioners:

> "We switched from a byte-level BPE to a unigram tokenizer mid-project. The model kept failing on numeric inputs. Turns out the new tokenizer split '2024' into ['20', '24'] while the old one kept it as ['2024']. Three weeks of investigation, one config line to fix."

Key lessons:
1. **Tokenizer consistency across train/eval/inference is critical** — any mismatch is a silent bug
2. **Number tokenization varies wildly** — test your tokenizer on numbers explicitly
3. **Whitespace handling** — leading space matters in many BPE tokenizers (▁hello ≠ hello)
4. **Unknown token rate** — >0.1% unk tokens in training data is a warning sign
5. **Vocabulary coverage** — check domain-specific terms (code keywords, medical terms, etc.)

## Checks Performed

### 1. Round-trip Consistency
```python
# text -> tokens -> text should be lossless
original = "Hello, world! This is a test: 2+2=4"
tokens = tokenizer.encode(original)
decoded = tokenizer.decode(tokens)
assert original == decoded, f"Round-trip failed: {original!r} != {decoded!r}"
```

### 2. Numeric Tokenization
```
Test suite for numbers:
  Integer:     42, 1000, 1000000
  Float:       3.14, 0.001, 1e-10
  Negative:    -42, -3.14
  Year:        2024, 1999
  Phone:       555-1234
  
Report: tokens per number, consistency, surprising splits
```

### 3. Whitespace Handling
```
Test: "hello" vs " hello" vs "hello " vs "  hello"
Report: whether leading/trailing space creates different tokens
```

### 4. Special Character Coverage
```
Test: <, >, &, ", ', \n, \t, \r, null bytes, unicode (🎉, 中文, العربية)
Report: which characters cause unk tokens
```

### 5. Fertility by Domain
```
English prose:   target ~4.0 chars/token
Python code:     target ~3.2 chars/token  
HTML:            target ~2.5 chars/token
JSON:            target ~2.8 chars/token

Flag: if actual differs from target by >20%
```

### 6. Vocabulary Overlap Check (for model updates)
```python
# When updating tokenizer, check what changed
old_vocab = set(old_tokenizer.vocab.keys())
new_vocab = set(new_tokenizer.vocab.keys())
added = new_vocab - old_vocab
removed = old_vocab - new_vocab
# Large removed set = embeddings need re-initialization
```

## Output Format
```
=== Tokenizer Diagnostics Report ===
Tokenizer: [name/path]
Vocabulary Size: [N]

[PASS/WARN/FAIL] Round-trip Consistency
[PASS/WARN/FAIL] Numeric Tokenization  
[PASS/WARN/FAIL] Whitespace Handling
[PASS/WARN/FAIL] Special Character Coverage
[PASS/WARN/FAIL] Fertility by Domain
[PASS/WARN/FAIL] Vocabulary Overlap (if comparing)

Surprising Tokenizations:
  "2024"  → ['20', '24']  ← WARNING: year split
  "..."   → ['▁', '.', '.', '.']  ← INFO: ellipsis expansion

CRITICAL ISSUES: N
WARNINGS: N
```

## Integration Points
- Pairs with `data-quality-audit` — run tokenizer-diagnostics first to validate tokenizer, then data-quality-audit on the tokenized data
- Pairs with `training-stability-monitor` — tokenizer bugs can cause loss spikes on specific token patterns
