# Test results

| Check | Result | Boundary |
|---|---|---|
| Roadmap required-section assertions | PASS | Planning document only |
| ADR required-decision and rollback assertions | PASS | Proposed architecture only |
| Requirements entries remain Planned | PASS | No implementation claim |
| Prohibited dash and fixed contrast-pattern scan | PASS | Changed formal documents |
| `git diff --check` | PASS | Repository text changes |
| Production database queries | PASS, read only | Point-in-time operational evidence |
| Backend full test suite | PASS, 193 passed, 4 skipped, 85.24% coverage | Required project test command |
| Frontend tests and build | Not run | No frontend behavior changed |
| Browser, Console and screenshot | Not applicable | No UI change and no runtime behavior acceptance claimed |

The first test invocation was interrupted by the outer command channel before
pytest produced a result and raised a stdout flush error while terminating. The
same required command was rerun through a sustained execution cell and
completed successfully in 157.51 seconds.
