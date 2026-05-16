You are running Vesta live eval T09.

Use tools; do not only describe actions.

Goal: create a very small evidence-backed research smoke note showing that
Vesta is a multi-surface harness, not only a coding-agent wrapper.

Hard contract:
1. Keep this small. Do not exceed 10 tool calls.
2. Record the expected artifact first with artifact_record.
3. Read only these narrow source windows unless you hit a real blocker:
   - VESTA_PRODUCT_IDEA.md, offset 1, limit 90
   - VESTA_LEDGER_DESIGN.md, offset 154, limit 95
   - work/vesta-runtime/prd.md, offset 195, limit 135
4. Write the artifact file with write_file:
   /Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t09-vesta-multisurface-smoke.md
5. The artifact must include:
   - 3 supported non-coding harness surfaces;
   - 2 coding/eval surfaces;
   - 1 current caveat or gap;
   - source refs with file paths and line ranges.
6. After write_file, call artifact_record again with status exists.
7. Add one ledger_append claim or gap.
8. Call finalize_run with a skip_reason if no tests are relevant.
9. Final answer must be only:
   artifact path, finalization verdict, and one caveat if any.

Do not use broad reads. Do not inspect unrelated files.
