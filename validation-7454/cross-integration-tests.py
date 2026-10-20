import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(sys.argv[1]).resolve()
PE = '--pe' in sys.argv[2:]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('fixtures', ROOT / 'tools/tests/test_import_audit.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
audit = fixtures.import_audit


class CrossIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.work = fixtures.Workspace()
        (self.work.libs / 'libc.prx').write_bytes(fixtures.exporting())

    def tearDown(self):
        self.work.close()

    def test_origin_dependency_resolves_declared_name(self):
        work = self.work
        registry, report = work.root / 'game.registry.json', work.root / 'report.json'
        fixtures.write_registry(registry, [])
        for tag in (14, 0x6100000d, 0x61000043):
            for format in ('sections', 'sysv', 'gnu'):
                with self.subTest(tag=hex(tag), format=format):
                    name = 'Declared.prx' if tag == 14 else 'Declared'
                    arguments = {'module_names': [(tag, name)]}
                    symbols = [('AAAAAAAAAAA', 1, fixtures.GLOBAL_FUNCTION)]
                    if format == 'sections':
                        image = fixtures.build_elf(symbols, **arguments)
                    else:
                        image = fixtures.build_sectionless_elf(symbols, gnu_hash=format == 'gnu', **arguments)
                    (work.modules / 'Different.prx').write_bytes(image)
                    (work.modules / 'consumer.prx').write_bytes(fixtures.build_elf(
                        [('AAAAAAAAAAA', 0, fixtures.GLOBAL_FUNCTION)], ['$ORIGIN/Declared.prx']))
                    code, _, err = work.run(registry, '--json', str(report))
                    self.assertEqual((code, err), (0, ''))
                    data = json.loads(report.read_text())
                    self.assertEqual(data['missing_libraries'], {})
                    self.assertEqual((data['references'], data['unique_imports']), (1, 1))

    def test_origin_identity_ambiguity_preserves_report(self):
        work = self.work
        registry, report = work.root / 'game.registry.json', work.root / 'report.json'
        fixtures.write_registry(registry, [])
        for tag in (14, 0x6100000d, 0x61000043):
            with self.subTest(tag=hex(tag)):
                name = 'Declared.prx' if tag == 14 else 'Declared'
                image = fixtures.build_elf([], module_names=[(tag, name)])
                for filename in ('first.prx', 'second.prx'):
                    (work.modules / filename).write_bytes(image)
                (work.modules / 'consumer.prx').write_bytes(fixtures.build_elf([], ['$ORIGIN/Declared.prx']))
                previous = b'{"previous":"complete report"}\n'
                report.write_bytes(previous)
                code, out, err = work.run(registry, '--json', str(report))
                self.assertEqual((code, out), (2, ''))
                self.assertIn('ambiguous guest module', err)
                self.assertEqual(report.read_bytes(), previous)

    def test_origin_host_dependency_still_requires_filename(self):
        work = self.work
        registry, report = work.root / 'game.registry.json', work.root / 'report.json'
        fixtures.write_registry(registry, [('AAAAAAAAAAA', 'Declared.prx')])
        (work.libs / 'host.prx').write_bytes(fixtures.build_elf([], ['$ORIGIN/Declared.prx']))
        (work.modules / 'Different.prx').write_bytes(fixtures.build_elf(
            [('AAAAAAAAAAA', 1, fixtures.GLOBAL_FUNCTION)], module_names=[(0x61000043, 'Declared')]))
        code, _, err = work.run(registry, '--json', str(report))
        self.assertEqual((code, err), (1, ''))
        data = json.loads(report.read_text())
        self.assertEqual(data['missing_libraries'], {})
        self.assertEqual(data['missing_host_dependencies'], [
            {'importer': 'host.prx', 'chain': ['host.prx', '$ORIGIN/Declared.prx']}])

    @unittest.skipUnless(PE, 'requires PE guest-module change; pass --pe')
    def test_pe_and_declared_elf_modules_resolve_together(self):
        work = self.work
        registry, report = work.root / 'game.registry.json', work.root / 'report.json'
        fixtures.write_registry(registry, [])
        (work.modules / 'pe.prx.guest.prx').write_bytes(fixtures.build_pe(['AAAAAAAAAAA#guest']))
        (work.modules / 'Different.prx').write_bytes(fixtures.build_elf([
            ('AAAAAAAAAAA', 0, fixtures.GLOBAL_FUNCTION), ('BBBBBBBBBBB', 1, fixtures.GLOBAL_FUNCTION)],
            ['pe.prx.guest.prx'], module_names=[(0x61000043, 'Declared')]))
        (work.modules / 'consumer.prx').write_bytes(fixtures.build_elf(
            [('BBBBBBBBBBB', 0, fixtures.GLOBAL_FUNCTION)], ['Declared.prx']))
        code, _, err = work.run(registry, '--json', str(report))
        self.assertEqual((code, err), (0, ''))
        data = json.loads(report.read_text())
        self.assertEqual(data['missing_libraries'], {})
        self.assertEqual((data['references'], data['unique_imports']), (2, 2))


suite = unittest.defaultTestLoader.loadTestsFromTestCase(CrossIntegrationTests)
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({'methods': result.testsRun, 'failed_subcases': len(result.failures),
                  'errors': len(result.errors), 'skipped': len(result.skipped)}))
raise SystemExit(not result.wasSuccessful())
