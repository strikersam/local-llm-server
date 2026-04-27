# Skill: feature-flag

## Purpose
Implement new features behind feature flags to enable safe, gradual rollouts and easy rollbacks without code deployments.

## Trigger
Use when:
- Implementing a risky or large feature
- A feature needs gradual rollout
- A/B testing is desired
- The feature might need to be disabled quickly in production

## Process

### Step 1: Assess Flag Need
Determine if a feature flag is appropriate:
- **Always flag**: breaking changes, major UI changes, experimental features
- **Consider flagging**: new integrations, significant logic changes
- **Skip flagging**: bug fixes, minor improvements, refactors

### Step 2: Define the Flag
```python
# Flag definition
FLAG_NAME = "feature_[descriptive_name]"
FLAG_DEFAULT = False  # default to OFF for new features
FLAG_DESCRIPTION = "[what this flag controls]"
FLAG_OWNER = "[team or person responsible]"
FLAG_CREATED = "[date]"
FLAG_PLANNED_REMOVAL = "[date or milestone when flag should be cleaned up]"
```

### Step 3: Implement the Guard
```python
# Python example
from agent.config import get_feature_flag

def some_feature():
    if not get_feature_flag("feature_new_thing"):
        return existing_behavior()
    return new_behavior()
```

```typescript
// TypeScript example
import { isFeatureEnabled } from './config/flags';

function someFeature() {
    if (!isFeatureEnabled('feature_new_thing')) {
        return existingBehavior();
    }
    return newBehavior();
}
```

### Step 4: Test Both Paths
Write tests for BOTH flag states:
```python
def test_feature_disabled(monkeypatch):
    monkeypatch.setenv("FEATURE_NEW_THING", "false")
    assert some_feature() == expected_old_behavior

def test_feature_enabled(monkeypatch):
    monkeypatch.setenv("FEATURE_NEW_THING", "true")
    assert some_feature() == expected_new_behavior
```

### Step 5: Document the Flag
Add to `docs/feature-flags.md`:
```markdown
| Flag | Default | Description | Owner | Remove By |
|------|---------|-------------|-------|-----------|
| feature_new_thing | false | [description] | [owner] | [milestone] |
```

### Step 6: Plan Removal
Feature flags are technical debt. Schedule cleanup:
- Set a calendar reminder or create an issue for flag removal
- Flag removal = merge the "enabled" path as the only path
- Delete the disabled path and the flag check entirely

## Rules
- Default to `false` (off) for new feature flags
- Every flag must have a planned removal date
- Never ship permanent flags — they are always temporary
- Test both code paths, always
- Keep flag logic at the boundary (entry point), not scattered through business logic
- Never nest feature flags more than 1 level deep

## Anti-Patterns
- Flags that have been on for >6 months without a removal plan
- Flags that control more than one conceptually distinct feature
- Business logic that reads flags directly (flags belong at the interface layer)
- Flags without tests for both states
