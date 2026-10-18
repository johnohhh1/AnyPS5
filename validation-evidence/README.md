# PR 6171 validation

PR: https://github.com/boykopovar/AnyPS5/pull/6171

Contribution `a12828cf6e1b9e8f5df4a1cc4dfbf2c7ff269a7a` rebases the previous `79b5bcd4a` onto main `fc623324a2ab3443cb69a6d0199141b8b2fee604`. Tool and test blobs are unchanged by this rebase; only the documentation hunk moves.

## Windows and Linux

[Author-run GitHub Actions validation](https://github.com/johnohhh1/AnyPS5/actions/runs/39174439746) executes workflow commit `26e82e9586edeef0072f6443f55c1195935b0f36`, whose parent is the contribution. The contribution's tool and test files are unchanged in that workflow commit. It uses pinned official actions, read-only permissions, synthetic inputs, no submodules, no game files and no native build.

| Runner | Python | Complete suite | Baseline regressions | Subprocess CLI |
| --- | --- | --- | --- | --- |
| Windows Server 2025 | 3.12.10 | 111 passed, 2 POSIX-only skips | 83 failed subcases, 0 errors | 6 passed |
| Windows Server 2025 | 3.14.8 | 111 passed, 2 POSIX-only skips | 83 failed subcases, 0 errors | 6 passed |
| Ubuntu | 3.14.8 | 112 passed, 1 Windows-only skip | 83 failed subcases, 0 errors | 6 passed |

The Windows read-only replacement test, symlink report test and source-commit stamping test all execute and pass on both Windows jobs. Baseline failures are the expected control result from running the seven contribution regressions against main's tool, not failed CI jobs. The CLI cases cover SONAME, both SCE name tags, SysV/GNU dynamic tables, undeclared casing, ambiguity preserving a prior JSON report, and aliases preserving import counts, from paths containing spaces.

To repeat on a Windows laptop with Python installed, use a disposable clone of this fork, select the workflow commit above, then run `python validation/run_import_audit.py`. It writes text logs and `validation-results/results.json`. No PS5 or game is needed for these synthetic tests. These are our own runner checks; the separate independent Windows 11 report on the original PR revision remains historical.

Local Ubuntu 26.04.1/Python 3.14.4 also passes 112 tests with the one Windows-only skip, and the registered `import_audit` CTest passes in 0.90 seconds. Conventions pass against the current upstream base and whitespace checks pass. The requested `--base origin/main` invocation was also run: the fork's old main causes it to scan unrelated upstream commits and flag two upstream revert subjects (`20c11e733`, `b8db74198`). Neither is part of this contribution. The current-upstream comparison has no findings.

## Actual title audit

Middle Ages Ping Pong, PPSA28319 version 01.000.000, uses the [developer's public release](https://github.com/STL1te/MedievalTennis/releases/tag/01.000.000), package SHA-256 `6426468091b42f6512a456004e47a0807ae83fc2af82a4408bef8a51103fbd48`.

Repeat the documented import-audit command on all five generated registries, supplying the original `sce_module`, `Media/Modules` and `Media/Plugins` directories to `--modules`, and the same built libraries to both tools. The new run uses registries and all 129 libraries from the recorded main `2626e5ee7e57df6e952a93a997a8b9fc79d80c08` runtime; library hashes were rechecked. Source classification is from the current rebased checkout. This is a new audit comparison, not a new game run or new native build.

For the Linux shell command below, `source/` is the unpacked release with its modules unwrapped, and `runtime/` is the relinker's output directory containing the five `app*.registry.json` files and the built `libs/`. Run the same command with main's tool and the PR's tool, without changing these inputs:

```sh
python3 tools/import_audit.py runtime/app*.registry.json --libs runtime/libs \
  --modules source/sce_module --modules source/Media/Modules \
  --modules source/Media/Plugins --json audit.json
```

| Tool | Exit | References | Unique imports | Implemented | Stub | Absent | Module | Missing module |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Main `fc623324a` | 1 | 2355 | 1052 | 889 | 9 | 4 | 150 | `Il2cppUserAssemblies.prx` (5 references) |
| PR `a12828cf6` | 0 | 2355 | 1052 | 888 | 9 | 0 | 155 | none |

Neither report has missing host dependencies. The title file is `Il2CppUserAssemblies.prx`, while its declared SCE identity is `Il2cppUserAssemblies`. The relinker accepts the identity; main's audit does not. This corrects preflight diagnostics and avoids investigating four nonexistent missing implementations. It does not unblock this already-running game. No second independently confirmed affected title was found in the targeted report search.

The recorded runtime on main `2626e5ee7` renders a match and exits 0 after SIGINT at 45.47 seconds. It uses RTX 5070/NVIDIA 595.99.02 and SDL dummy audio. The old shutdown SIGSEGV on `ab9a47684` did not reproduce in this later run. No full-playability, audible-audio or performance claim is made.

## Overlap integration

Heads checked: #7159 `abea0949a96076cebba5217410e654652f80c0de` (MarcZX10), #7454 `0df919176fc8d00fb56491d3469850ab8f633249` (ggkouujere-debug). The supplied patches are candidate integration resolutions for testing; neither other author's implementation was added to PR 6171.

| Combination on the current base | Resolution | Existing suite |
| --- | --- | --- |
| 6171 + 7159 | Combine PE dispatch with declared-name collection and the three-value `read_modules` return; adapt the companion PE test's unpacking | 113 passed, 1 Windows-only skip |
| 6171 + 7454 | Preserve both test insertions | 113 passed, 1 Windows-only skip |
| 6171 + 7159 + 7454 | Both resolutions | 114 passed, 1 Windows-only skip |

Cross-feature checks reveal a further interaction that those existing suites miss. `$ORIGIN/Declared.prx` dependencies fail to resolve an SCE identity declared by `Different.prx`; a prefix also prevents detecting ambiguous SCE identities. The 6171+7454 and triple combinations each produce 8 failed subcases with no errors: 6 valid-resolution cases across the two SCE tags and section/SysV/GNU layouts, plus 2 ambiguity cases. SONAME controls already pass.

Normalizing requested names with #7454's `strip_origin` before the identity lookup resolves all 8 failures. Both existing suites still pass. The cross-feature test also verifies that a host dependency still needs an actual filename, and the triple combination verifies that PE exports and declared ELF providers resolve together.

In a disposable checkout of the contribution, apply `6171-7159-7454-on-6171.patch`, followed by `6171-7159-7454-origin-resolution.patch`. Then run:

```sh
python -m unittest tools.tests.test_import_audit -v
python validation-evidence/cross-integration-tests.py . --pe
```

The first patch alone preserves the existing suites but fails the additional cross-feature checks. Both patches pass 114 existing tests with one Windows-only skip and all four cross-feature methods, including their subcases. Other authors' changes retain their authorship; these are local integration proposals, not an agreed merge order. A coordination request is being made on PR 6171. No upstream CI has been triggered.

AI-assisted testing and reporting: OpenAI Codex; johnohhh1 is responsible for the submission.
