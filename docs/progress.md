# Execution record

Task 1: complete — 24 tests passed. Initial run failed because implementation modules were absent.
Ruling: native execution in a new dedicated repository on codex/initial-service; no extra worktree is necessary because no existing project work can be disturbed.
Ruling: use OpenSpec tasks as the implementation ledger, as requested by the user, rather than a second task system.
Task 2: complete — 42 tests passed, one upstream TestClient deprecation warning. API/SDK tests failed before implementation. Numeric-marker regression reproduced and fixed (IP999).
Task 3: local smoke passed on port 8765: /docs=200, incomplete=200 needs_clarification, both sourced products=503 without API credentials. Port 8000 belongs to another application; README uses 8765. Real examples pending key.
Final review: two Important findings reproduced and fixed with RED→GREEN regressions: complete-name numeric exemption (including a name repeated in description) and mixed refusal/text rejection without retry. No minor findings deferred.
Ruling: hosted API acceptance and quality are verified by real runs, not by schema inspection. Whether mixed refusal occurs in practice does not change rejection behavior. General semantic verification remains outside this local prototype and is documented.
Real API run: both products returned HTTP429; diagnostic code credit_balance_exhausted, type insufficient_quota. Task3.2 remains blocked by provider balance, not key expiry; no fabricated outputs saved. Added actionable quota error regression RED→GREEN.
Ruling: publish the verified implementation to initial main in the new empty repository, as authorized; this does not merge into an existing shared project. Do not archive OpenSpec while real examples remain unfinished.
