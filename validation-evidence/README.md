# PR 6171 October 19 refresh

PR: https://github.com/boykopovar/AnyPS5/pull/6171

Contribution `74c5e7029f1a3d69089c3fa081ed644bc2f2f4ac` is rebased onto main `b6583dd8687f359c2caea295cde23e4732b73433`. Previous head `a12828cf6` is preserved on `backup/pr-6171-pre-rebase-20261019`.

## Coordination and integration

[The author of #7454 confirmed the combined resolution and agreed to #7454 before #6171](https://github.com/boykopovar/AnyPS5/pull/6171#issuecomment-6264417521). A [Windows follow-up contributor reports the same order and passing combined checks](https://github.com/boykopovar/AnyPS5/pull/6171#issuecomment-6269733077). These are contributor confirmations, not maintainer approval of #6171.

#7159 has merged. Main also gained Unicode input diagnostics and a Windows host-library case lookup. The rebase keeps PE guest-module support, normalizes PE exports, retains the PE-importer `windows` set, and passes physical `host_modules` to the host checker. Guest identities cannot substitute for missing host filenames. The existing PE reader test now consumes the three-value `read_modules` result and checks its filename set.

#7454 remains a separate prerequisite, tested at `11840ad87c4065873cb2923b2367232d33bbe5ee`. Its implementation is not included in the contribution. The prepared combined resolution:

- preserves both test insertions and current main's Windows importer metadata;
- applies #7454's `strip_origin` before the requested-name identity lookup;
- passes 122 existing tests with one Windows-only skip on Linux (123 total);
- passes all four cross-feature methods, including SCE identity/origin resolution, ambiguity/report preservation, the host filename guard, and mixed PE/ELF providers.

The normalization and any further conflict resolution will be applied when rebasing after #7454 lands. `joint-7454-preview.patch` is a replay candidate combining that author's prerequisite with our identity resolution, not extra production implementation submitted in #6171. Keep the evidence outside a disposable checkout, select contribution `74c5e7029`, apply that patch, then run the complete audit suite and `cross-integration-tests.py <checkout> --pe`.

## Standalone checks

[Fresh author-run Windows/Linux CI](https://github.com/johnohhh1/AnyPS5/actions/runs/39295544635) uses workflow commit `b3cd929f8d4455cf47440511ccd13531b9c95ee9`, a child of the contribution with identical audit tool/test blobs. Only a fork-only validation workflow, its runner and the baseline tool are added. It uses pinned official actions and read-only permissions, no submodules or game assets. Detailed per-platform results and skips are attached in this directory and as workflow artifacts.

On local Ubuntu 26.04.1/Python 3.14.4 the standalone suite passes 121 tests with one Windows-only skip (122 total). Registered CTest passes in 0.99 seconds. Conventions against current upstream and the contribution whitespace diff pass. The prescribed comparison against old fork `origin/main` also ran; it scans unrelated upstream history and reports four errors (two upstream revert subjects, an environment-variable documentation check and a technical-debt path check), plus upstream warnings. None is in the contribution's three-file diff.

The runner executes the full suite, the seven contribution regression methods against main's tool (expected 83 failed subcases and zero errors), and six subprocess CLI cases from paths containing spaces. The CLI checks cover SONAME, both SCE name tags, SysV/GNU tables, undeclared casing, ambiguity preserving a prior JSON report, and count preservation across aliases. These checks are synthetic Python validation; no upstream native CI or new native build is claimed.

| Runner | Python | Suite | CLI |
| --- | --- | --- | --- |
| Linux-7.0.0-1017-azure-x86_64-with-glibc2.39 | 3.14.8 | 121 passed, 1 skipped | 6 passed |
| Windows-2025Server-10.0.26100-SP0 | 3.12.10 | 120 passed, 2 skipped | 6 passed |
| Windows-2025Server-10.0.26100-SP0 | 3.14.8 | 120 passed, 2 skipped | 6 passed |

## Actual-title audit

The public developer release of [Middle Ages Ping Pong, PPSA28319 01.000.000](https://github.com/STL1te/MedievalTennis/releases/tag/01.000.000), package SHA-256 `6426468091b42f6512a456004e47a0807ae83fc2af82a4408bef8a51103fbd48`, remains the single confirmed affected title.

A new audit comparison reuses all five registries and 129 hash-checked libraries from the recorded main `2626e5ee7` runtime, with current source classification. Main's tool exits 1 with four absent imports and a false missing `Il2cppUserAssemblies.prx`; the PR exits 0 with none. Both retain 2,355 references, 1,052 unique imports and eight stub classifications. There are no missing host dependencies. The decrease from nine historical stub classifications reflects the newer source snapshot, not a runtime change in this PR.

For a Linux reproduction, `source/` is the unwrapped developer release and `runtime/` contains the relinker's five registries and built `libs/`. Keep those inputs identical for the main and PR tools:

```sh
python3 tools/import_audit.py runtime/app*.registry.json --libs runtime/libs \
  --modules source/sce_module --modules source/Media/Modules \
  --modules source/Media/Plugins --json audit.json
```

This refresh does not rerun the game. The recorded `2626e5ee7` run renders a match and exits 0 after SIGINT at 45.47 seconds on RTX 5070/NVIDIA 595.99.02 with SDL dummy audio. The old shutdown crash did not reproduce in that later run. No full playability, audible audio, performance, console result or additional affected title is claimed.

AI-assisted implementation, testing and reporting: OpenAI Codex; johnohhh1 is responsible for the submission.
