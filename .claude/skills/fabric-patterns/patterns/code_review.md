---
name: code_review
description: Review code for correctness, security, and maintainability
version: "1.0.0"
---
{{content}}

Review the above code and report on:
- **Correctness**: logic errors, off-by-ones, null handling, edge cases
- **Security**: injection risks, secret handling, input validation gaps
- **Maintainability**: naming clarity, unnecessary complexity, missing types
- **Performance**: obvious inefficiencies or blocking calls

Keep each finding concise. Flag severity as [CRITICAL], [MAJOR], or [MINOR].
End with a one-line overall verdict.
