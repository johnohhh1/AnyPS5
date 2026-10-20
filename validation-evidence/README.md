# PR 6171 October 20 refresh

Contribution `98596149e2ce227c69ad1e625a1af957e63b1d7d` rebases the previous `74c5e7029` onto main `892a4f1328a14a123eca4af8f3c9ea5d176133ab`. The old head is preserved on `backup/pr-6171-pre-rebase-20261020`.

The main conflict combines declared module identities with newly merged `ModuleNames` matching. The resolution retains main's filename-suffix matching and Windows case rules, then adds the declared-name aliases to the guest-name collection. Host dependency lookup continues to receive physical `host_modules`, with the PE-importer set preserved. Main's new unscoped guest-import lookup and NID disambiguation normalization remain unchanged.

The complete audit suite passes on local Ubuntu: 126 tests, one Windows-only skip (127 total). Current-upstream conventions and contribution whitespace checks pass. The prescribed comparison with old fork `origin/main` was also run and reports four unrelated upstream errors plus warnings; it is not the comparison used by this PR against its real upstream base.

[Fresh author-run Windows/Linux CI](https://github.com/johnohhh1/AnyPS5/actions/runs/39469990531) runs workflow commit `aa423feee6a780d1b6f6a2fb81d9098fbf5fa480`, a child of the contribution with identical audit tool/test blobs. The separate fork branch adds only a pinned read-only workflow, its runner and main's baseline tool. Detailed platform results are included below and in workflow artifacts. No game binaries, submodules or native build are needed for these Python tests.

The seven contribution regression methods against main retain the expected 83 failed subcases with zero errors. Six subprocess CLI cases check declared names, paths containing spaces, undeclared casing, ambiguity/report preservation and alias import counts. Existing tests cover the newly merged module-name matching, unscoped guest imports and NID normalization.

The agreed order remains **#7454, then #6171**, as confirmed by [#7454's author](https://github.com/boykopovar/AnyPS5/pull/6171#issuecomment-6264417521). #7454 remains open and conflicting; its implementation is not included in this contribution. The identity-side origin normalization remains prepared for the subsequent rebase. The [October 19 joint preview](https://github.com/johnohhh1/AnyPS5/blob/4f8e016da6e0731476fc9c35563af6d0ea457a15/validation-evidence/README.md) and independent reports keep their old pins; no new combined result on this October 20 head is claimed. That combination must be revalidated when #7454 lands.

The actual-title audit is repeated with the same five registries and 129 hash-checked libraries from the recorded main `2626e5ee7` runtime of Middle Ages Ping Pong (PPSA28319 01.000.000), with current source classification. Input provenance and the before/after result are recorded in `title-reproduction.json`. This reruns the audit only, not the game or native build. No additional affected title, console measurement, audio result or performance claim is made. Earlier rendered-game evidence and old Windows reports retain their original tested revisions.

AI-assisted implementation, testing and reporting: OpenAI Codex; johnohhh1 is responsible for the contribution.

| Runner | Python | Passed | Skipped | CLI |
| --- | --- | --- | --- | --- |
| Linux-7.0.0-1017-azure-x86_64-with-glibc2.39 | 3.14.8 | 126 | 1 | 6 |
| Windows-2025Server-10.0.26100-SP0 | 3.12.10 | 125 | 2 | 6 |
| Windows-2025Server-10.0.26100-SP0 | 3.14.8 | 125 | 2 | 6 |
