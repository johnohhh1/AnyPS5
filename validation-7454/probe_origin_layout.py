import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SNAPSHOTS = ROOT / 'snapshots'

if len(sys.argv) == 1:
    results = []
    for scenario in ('original', 'rebased', 'combined'):
        run = subprocess.run([sys.executable, str(Path(__file__).resolve()), scenario], capture_output=True, text=True, check=True)
        results.extend(json.loads(run.stdout))
    (ROOT / 'origin-layout-results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    raise SystemExit(0)

scenario = sys.argv[1]
sys.path.insert(0, str(SNAPSHOTS / scenario / 'tools'))
spec = importlib.util.spec_from_file_location('fixtures', SNAPSHOTS / scenario / 'tools/tests/test_import_audit.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
results = []
for case in ('same-folder', 'sibling-folder', 'executable-needed'):
    work = fixtures.Workspace()
    try:
        app = work.root / 'app0'
        consumer_dir = app / 'sce_module'
        consumer_dir.mkdir(parents=True)
        provider_dir = consumer_dir if case == 'same-folder' else app / 'Media/Modules'
        provider_dir.mkdir(parents=True, exist_ok=True)
        work.modules = consumer_dir
        filename = 'Provider.prx.guest.prx'
        provider = provider_dir / filename
        provider.write_bytes(fixtures.exporting('AAAAAAAAAAA'))
        registry, report = work.root / 'game.registry.json', work.root / 'audit.json'
        fixtures.write_registry(registry, [])
        needed = '$ORIGIN/' + filename if case == 'same-folder' else '$ORIGIN/../Media/Modules/' + filename
        if case == 'executable-needed':
            needed = '$ORIGIN/app0/Media/Modules/' + filename
            (work.root / 'game.needed.json').write_text(json.dumps([needed]))
        consumer_needed = [] if case == 'executable-needed' else [needed]
        (consumer_dir / 'Consumer.prx.guest.prx').write_bytes(fixtures.build_elf(
            [('AAAAAAAAAAA', 0, fixtures.GLOBAL_FUNCTION)], consumer_needed))
        (work.libs / 'libc.prx').write_bytes(fixtures.exporting())
        origin = work.root if case == 'executable-needed' else consumer_dir
        resolved = (origin / needed.removeprefix('$ORIGIN/')).resolve()
        assert resolved == provider.resolve() and resolved.is_file()
        code, out, err = work.run(registry, '--modules', str(provider_dir), '--json', str(report))
        assert err == ''
        data = json.loads(report.read_text())
        results.append({'scenario': scenario, 'case': case, 'needed': needed,
                        'dependency_resolves_to_present_provider': True, 'exit_code': code,
                        'missing_libraries': data['missing_libraries'], 'references': data['references']})
        (ROOT / (scenario + '-layout-' + case + '.log')).write_text(out + err)
    finally:
        work.close()
print(json.dumps(results))
