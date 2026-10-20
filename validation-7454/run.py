import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORTS = ROOT / 'validation-results-7454'
REPORTS.mkdir(exist_ok=True)
MANIFEST = json.loads((HERE / 'manifest.json').read_text())
METHOD = 'test_converted_module_resolves_plain_and_origin_library_names'


def suite_result(suite, name):
    start = time.monotonic()
    with (REPORTS / (name + '.log')).open('w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    return {'tests': result.testsRun, 'passed': result.testsRun - len(result.skipped) if result.wasSuccessful() else None,
            'failures': len(result.failures), 'errors': len(result.errors),
            'skipped': [{'test': str(test), 'reason': reason} for test, reason in result.skipped],
            'seconds': time.monotonic() - start}


def cli_cases(tests, snapshot, scenario):
    results = []
    for case in ('converted', 'missing-module', 'registry-origin', 'host-origin', 'missing-host', 'plain'):
        work = tests.Workspace()
        try:
            folder = work.root / 'inputs with spaces'
            folder.mkdir()
            registry, report = folder / 'game.registry.json', folder / 'audit.json'
            provider = 'Provider.prx.guest.prx'
            library = '$ORIGIN/' + provider if case == 'registry-origin' else 'Provider.prx'
            tests.write_registry(registry, [] if case in ('host-origin', 'missing-host') else [('AAAAAAAAAAA', library)])
            (work.libs / 'libc.prx').write_bytes(tests.exporting())
            if case not in ('missing-module', 'missing-host'):
                (work.modules / provider).write_bytes(tests.exporting('AAAAAAAAAAA'))
            if case in ('host-origin', 'missing-host'):
                (work.libs / 'Host.prx').write_bytes(tests.build_elf([], ['$ORIGIN/' + provider]))
            elif case != 'plain':
                (work.modules / 'Consumer.prx').write_bytes(tests.build_elf([], ['$ORIGIN/' + provider]))
            command = [sys.executable, str(snapshot / 'tools/import_audit.py'), str(registry),
                       '--libs', str(work.libs), '--modules', str(work.modules), '--source', str(work.source),
                       '--json', str(report)]
            run = subprocess.run(command, capture_output=True, text=True)
            (REPORTS / (scenario + '-cli-' + case + '.log')).write_text(run.stdout + run.stderr, encoding='utf-8')
            expected = 1 if case in ('missing-module', 'missing-host') else 0
            assert run.returncode == expected, (case, run.returncode, run.stderr)
            data = json.loads(report.read_text(encoding='utf-8'))
            row = {'case': case, 'exit_code': run.returncode, 'references': data['references'],
                   'classes': data['unique_by_class'], 'missing_libraries': data['missing_libraries'],
                   'missing_host_dependencies': data['missing_host_dependencies']}
            if expected == 0:
                assert data['unique_by_class']['absent'] == 0 and not data['missing_libraries']
                assert not data['missing_host_dependencies']
            if case == 'missing-host':
                assert data['missing_host_dependencies'] == [
                    {'importer': 'Host.prx', 'chain': ['Host.prx', '$ORIGIN/' + provider]}]
            if case in ('converted', 'registry-origin', 'plain'):
                assert data['references'] == 1 and data['unique_by_class']['module'] == 1
            results.append(row)
        finally:
            work.close()
    return results


def cross_result(snapshot, name, expected_failures):
    run = subprocess.run([sys.executable, str(HERE / 'cross-integration-tests.py'), str(snapshot), '--pe'],
                         capture_output=True, text=True)
    (REPORTS / (name + '.log')).write_text(run.stdout + run.stderr, encoding='utf-8')
    result = json.loads(run.stdout.strip().splitlines()[-1])
    assert result == {'methods': 4, 'failed_subcases': expected_failures, 'errors': 0, 'skipped': 0}, result
    assert run.returncode == int(bool(expected_failures)), run.returncode
    return result


def worker(scenario):
    source = HERE / 'snapshots' / scenario
    for name, blob in MANIFEST['files'][scenario].items():
        data = (source / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == blob, name
    with tempfile.TemporaryDirectory(prefix='audit-7454-') as directory:
        snapshot = Path(directory) / scenario
        shutil.copytree(source, snapshot)
        subprocess.run(['git', 'init', '-q', str(snapshot)], check=True)
        sys.path.insert(0, str(snapshot / 'tools'))
        spec = importlib.util.spec_from_file_location('fixtures', snapshot / 'tools/tests/test_import_audit.py')
        tests = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tests)
        suite = suite_result(unittest.defaultTestLoader.loadTestsFromModule(tests), scenario + '-suite')
        expected_tests = {'original': 109, 'rebased': 121, 'combined': 128}[scenario]
        assert suite['tests'] == expected_tests and suite['failures'] == suite['errors'] == 0, suite
        result = {'scenario': scenario, 'tested_commit': MANIFEST['pins'][scenario], 'suite': suite,
                  'cli': cli_cases(tests, snapshot, scenario)}
        if scenario != 'combined':
            spec = importlib.util.spec_from_file_location('baseline', HERE / 'baselines' / (scenario + '.py'))
            baseline = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(baseline)
            tests.import_audit = baseline
            control = suite_result(unittest.TestSuite([tests.ImportAuditTests(METHOD)]), scenario + '-baseline')
            assert control['failures'] > 0 and control['errors'] == 0, control
            result['baseline_control'] = control
        else:
            result['cross'] = cross_result(snapshot, 'combined-cross', 0)
            tool = snapshot / 'tools/import_audit.py'
            content = tool.read_text()
            normalized = ('    requested = {strip_origin(name) for name in needed_names}\n'
                          '    requested |= {strip_origin(name) for _, needed in imports.values() for name in needed}')
            assert normalized in content
            tool.write_text(content.replace(normalized, '    requested = set(needed_names) | {name for _, needed in imports.values() for name in needed}'))
            result['cross_without_identity_adjustment'] = cross_result(snapshot, 'combined-cross-control', 8)
        return result


if len(sys.argv) == 3 and sys.argv[1] == '--scenario':
    result = worker(sys.argv[2])
    (REPORTS / (sys.argv[2] + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
else:
    results = []
    for scenario in ('original', 'rebased', 'combined'):
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--scenario', scenario], check=True,
                       env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        results.append(json.loads((REPORTS / (scenario + '.json')).read_text(encoding='utf-8')))
    summary = {'workflow_commit': os.environ.get('GITHUB_SHA'), 'python': sys.version,
               'platform': platform.platform(), 'os_name': os.name, 'pins': MANIFEST['pins'], 'results': results}
    (REPORTS / 'results.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
