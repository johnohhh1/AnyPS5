import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from tools.tests import test_import_audit as tests

REPORTS = ROOT / 'validation-results'
REPORTS.mkdir(exist_ok=True)
METHODS = [
    'test_declared_module_names_resolve_imports_and_dependencies',
    'test_module_identity_does_not_fold_undeclared_filename_case',
    'test_ambiguous_module_names_preserve_report',
    'test_exact_module_filename_precedes_other_module_identities',
    'test_multiple_module_names_and_identical_files_do_not_repeat_imports',
    'test_invalid_declared_module_name_preserves_report',
    'test_host_dependencies_require_filenames_not_module_identities',
]


def run_suite(suite, name):
    start = time.monotonic()
    with (REPORTS / (name + '.log')).open('w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    return {'tests': result.testsRun, 'passed': result.testsRun - len(result.skipped) if result.wasSuccessful() else None,
            'failures': len(result.failures), 'errors': len(result.errors),
            'skipped': [{'test': str(test), 'reason': reason} for test, reason in result.skipped],
            'seconds': time.monotonic() - start}


suite = run_suite(unittest.defaultTestLoader.loadTestsFromModule(tests), 'suite')
spec = importlib.util.spec_from_file_location('baseline_import_audit', ROOT / 'validation' / 'main_import_audit.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
original = tests.import_audit
tests.import_audit = baseline
try:
    regression = run_suite(unittest.TestSuite(tests.ImportAuditTests(method) for method in METHODS), 'baseline-regressions')
finally:
    tests.import_audit = original

cli_results = []
for name, tag, format, expected in [
        ('soname', 14, 'sections', 0),
        ('sce-sysv', 0x6100000d, 'sysv', 0),
        ('sce-gnu', 0x61000043, 'gnu', 0),
        ('undeclared-case', None, 'sections', 1),
        ('ambiguous', 0x61000043, 'sections', 2),
        ('multiple-aliases', 0x61000043, 'sections', 0)]:
    work = tests.Workspace()
    try:
        folder = work.root / 'CLI inputs with spaces'
        folder.mkdir()
        registry, report = folder / 'game.registry.json', folder / 'audit.json'
        (work.libs / 'libc.prx').write_bytes(tests.exporting())
        symbol = [('AAAAAAAAAAA', 1, tests.GLOBAL_FUNCTION)]
        declared = 'Declared.prx' if tag == 14 else 'Declared'
        module_names = [(tag, declared)] if tag is not None else []
        if name == 'multiple-aliases':
            module_names += [(14, 'Second.prx')]
            symbol += [('BBBBBBBBBBB', 0, tests.GLOBAL_FUNCTION)]
            (work.libs / 'libc.prx').write_bytes(tests.exporting('BBBBBBBBBBB'))
        if format == 'sections':
            image = tests.build_elf(symbol, module_names=module_names)
        else:
            image = tests.build_sectionless_elf(symbol, gnu_hash=format == 'gnu', module_names=module_names)
        (work.modules / 'Different.prx').write_bytes(image)
        if name == 'ambiguous':
            (work.modules / 'Other.prx').write_bytes(image)
        entries = [('AAAAAAAAAAA', 'Declared.prx')]
        if name == 'undeclared-case':
            entries = [('AAAAAAAAAAA', 'different.prx')]
        if name == 'multiple-aliases':
            entries += [('AAAAAAAAAAA', 'Second.prx'), ('AAAAAAAAAAA', 'Different.prx')]
        tests.write_registry(registry, entries)
        previous = b'{"previous":"complete report"}\n'
        report.write_bytes(previous)
        command = [sys.executable, str(ROOT / 'tools/import_audit.py'), str(registry),
                   '--libs', str(work.libs), '--modules', str(work.modules), '--source', str(work.source),
                   '--json', str(report)]
        run = subprocess.run(command, capture_output=True, text=True)
        (REPORTS / ('cli-' + name + '.log')).write_text(run.stdout + run.stderr, encoding='utf-8')
        row = {'case': name, 'exit_code': run.returncode, 'expected_exit': expected}
        assert run.returncode == expected, (row, run.stderr)
        if expected == 2:
            assert report.read_bytes() == previous
            row['previous_report_preserved'] = True
        else:
            data = json.loads(report.read_text(encoding='utf-8'))
            row.update(references=data['references'], missing_libraries=data['missing_libraries'], classes=data['unique_by_class'])
            if expected == 0:
                assert data['missing_libraries'] == {} and data['unique_by_class']['absent'] == 0
            if name == 'multiple-aliases':
                assert data['references'] == 4
        cli_results.append(row)
    finally:
        work.close()

result = {'pr_head': '74c5e7029f1a3d69089c3fa081ed644bc2f2f4ac',
          'baseline': 'b6583dd8687f359c2caea295cde23e4732b73433',
          'workflow_commit': os.environ.get('GITHUB_SHA'), 'python': sys.version,
          'platform': platform.platform(), 'os_name': os.name,
          'suite': suite, 'baseline_regressions': regression, 'cli': cli_results}
(REPORTS / 'results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
assert suite['tests'] == 122 and suite['failures'] == 0 and suite['errors'] == 0, suite
assert regression['failures'] == 83 and regression['errors'] == 0, regression
