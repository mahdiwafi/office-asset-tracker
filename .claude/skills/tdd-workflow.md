---
name: tdd-workflow
description: Red-green-refactor discipline — write the failing test first, confirm it fails for the expected reason, implement minimally, refactor. Never write implementation code when no failing test exists for it.
---

# TDD workflow

The discipline that erodes by week two if not encoded. Follow it every time.

1. **Write the failing test first.** The test name is the specification — write the name before any implementation.
2. **Run it. Confirm it fails for the expected reason.** A test that fails for an unexpected reason is a bug, not a red light. If it fails because the import path is wrong, that's not a meaningful red.
3. **Implement minimally.** The smallest change that makes the test pass. No speculative generality.
4. **Refactor.** Only after green, and only while the tests stay green.
5. **Run the full suite** before committing.

**Refuse** to write implementation code when no failing test exists for it. If the candidate asks for implementation without a test, say no and write the test first with them.

**What is not TDD:** writing the implementation, then a test that documents it. The test must exist and be seen failing before the implementation exists.
