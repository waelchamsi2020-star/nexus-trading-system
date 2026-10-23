"""Archived-card verification and byte-preserving prefixes on synthetic fixtures."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from nexus.strategies import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('context_cache_fixture', ROOT / 'tools/context_input_cache.py')
cache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cache)


class ContextInputCache(unittest.TestCase):
    def source_fixture(self, root):
        blobs = {
            'src/nexus/strategies.py': b'# SYNTHETIC STRATEGY FIXTURE\r\n',
            'src/nexus/engine.py': b'# SYNTHETIC ENGINE FIXTURE\r\n',
            'src/nexus/execution.py': b'# SYNTHETIC EXECUTION FIXTURE\r\n',
            'src/nexus/config/models.yaml': b'{"fixture":true}\r\n',
        }
        algorithm = b'# SYNTHETIC CACHE ALGORITHM\r\n'
        for name, data in {**blobs, 'tools/long_signal_cache.py': algorithm}.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        digest = hashlib.sha256()
        for name in sorted(blobs, key=Path):
            digest.update(name.encode())
            digest.update(b'\0')
            digest.update(blobs[name])
            digest.update(b'\0')
        digest.update(algorithm)
        return blobs, algorithm, digest.hexdigest()

    def verify_fixture(self, root, blobs, algorithm, expected):
        def git_blob(_root, _commit, name):
            return algorithm if name == 'tools/long_signal_cache.py' else blobs[name]
        with patch.object(cache, '_tracked_source_names', return_value=list(blobs)), \
                patch.object(cache, '_git_blob', side_effect=git_blob):
            return cache.verify_archive_source(expected, repo_root=root, commit='SYNTHETIC')

    def test_reconstructed_old_source_hash_and_only_declared_context_changes_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blobs, algorithm, digest = self.source_fixture(root)
            self.assertEqual(digest, cache._fingerprint_blobs(blobs, algorithm))
            (root / 'src/nexus/engine.py').write_bytes(b'# Context veto integration only\n')
            (root / 'src/nexus/execution.py').write_bytes(b'# Context veto integration only\n')
            for name in cache.ALLOWED_NEW:
                (root / name).write_bytes(b'# Context source fixture\n')
            proof = self.verify_fixture(root, blobs, algorithm, digest)
            self.assertEqual(digest, proof['reconstructed_source_sha256'])
            self.assertEqual(2, proof['protected_files_verified'])
            self.assertEqual(sorted(cache.ALLOWED_MODIFIED), proof['changed_context_integration_paths'])
            self.assertEqual(sorted(cache.ALLOWED_NEW), proof['new_context_paths'])

    def test_archived_hash_mismatch_is_rejected_before_card_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blobs, algorithm, _ = self.source_fixture(root)
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                self.verify_fixture(root, blobs, algorithm, '0' * 64)

    def test_any_model_helper_inventory_or_cache_algorithm_change_refuses_reuse(self):
        for mutation in ('model', 'new_helper', 'missing_helper', 'algorithm'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                blobs, algorithm, digest = self.source_fixture(root)
                if mutation == 'model':
                    (root / 'src/nexus/strategies.py').write_bytes(b'# CHANGED MODEL\n')
                elif mutation == 'new_helper':
                    (root / 'src/nexus/unapproved_helper.py').write_bytes(b'# UNAPPROVED\n')
                elif mutation == 'missing_helper':
                    (root / 'src/nexus/strategies.py').unlink()
                else:
                    (root / 'tools/long_signal_cache.py').write_bytes(b'# CHANGED CACHE\n')
                with self.assertRaises(ValueError):
                    self.verify_fixture(root, blobs, algorithm, digest)

    def native_csv_fixture(self, path):
        header = b'\xef\xbb\xbf<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\r\n'
        rows = [f'2020.01.06\t{hour:02d}:00:00\t1.1\t1.2\t1.0\t1.15\t100\t0\t12\r\n'.encode()
                for hour in range(10)]
        path.write_bytes(header + b''.join(rows))
        bars, _ = cache.signals.load_csv(path, 'H1')
        return path.read_bytes(), bars

    def test_training_prefix_preserves_header_row_bytes_and_exact_parsed_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native, prefix = root / 'native.csv', root / 'prefix.csv'
            blob, bars = self.native_csv_fixture(native)
            proof = cache.write_training_prefix(native, bars, 6, 'H1', prefix)
            self.assertEqual(blob, native.read_bytes())
            self.assertEqual(b''.join(blob.splitlines(keepends=True)[:7]), prefix.read_bytes())
            self.assertEqual(bars[:6], cache.signals.load_csv(prefix, 'H1')[0])
            self.assertTrue(proof['byte_preserving'])
            self.assertTrue(proof['parsed_rows_equal_full_prefix'])
            self.assertEqual(0, proof['synthetic_candles'])
            self.assertEqual(proof, cache.write_training_prefix(native, bars, 6, 'H1', prefix))

    def test_training_prefix_rejects_non_native_counts_source_overwrite_and_line_mismatch(self):
        for mutation in ('zero', 'too_large', 'boolean', 'same_path', 'bad_rows'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                native, prefix = root / 'native.csv', root / 'prefix.csv'
                _, bars = self.native_csv_fixture(native)
                count = {'zero': 0, 'too_large': 11, 'boolean': True}.get(mutation, 6)
                if mutation == 'same_path':
                    prefix = native
                if mutation == 'bad_rows':
                    bars = bars[:-1]
                with self.assertRaises(ValueError):
                    cache.write_training_prefix(native, bars, count, 'H1', prefix)

    def archive_fixture(self, root):
        models = sorted(REGISTRY)
        spec = {
            'cache_version': cache.signals.CACHE_VERSION, 'csv_sha256': '1' * 64,
            'source_sha256': '2' * 64, 'symbol': 'SYNTHETIC', 'timeframe': 'H1',
            'point': .00001, 'profile': 'CONTINUOUS', 'model_ids': models,
            'start_index': 1, 'lookback_bars': 300, 'python_version': [3, 12, 14],
        }
        key = hashlib.sha256(cache.signals._encoded(spec)).hexdigest()
        folder = root / 'reports/long-study-cache' / key
        folder.mkdir(parents=True)
        provenance = {**spec, 'cache_key': key, 'cache_directory': str(folder.resolve()),
                      'bar_count': 3, 'chunks': 1}
        payload = {'cache_key': key, 'start': 1, 'end': 3,
                   'cards': {model: [] for model in models},
                   'status_counts': {model: {'NO_SETUP': 2} for model in models}}
        chunk = folder / '000000001-000000003.json.gz'
        cache.signals._atomic_gzip(chunk, {'payload': payload,
                                         'sha256': hashlib.sha256(cache.signals._encoded(payload)).hexdigest()})
        return provenance, chunk

    def test_archived_chunks_require_every_58_model_and_independent_gzip_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provenance, chunk = self.archive_fixture(root)
            cards, counts, hashes = cache._read_archive(provenance, [{}, {}, {}], repo_root=root)
            self.assertEqual(set(REGISTRY), set(cards))
            self.assertEqual(58, len(cards))
            self.assertTrue(all(value == {'NO_SETUP': 2} for value in counts.values()))
            self.assertEqual(hashlib.sha256(chunk.read_bytes()).hexdigest(), hashes[0]['sha256'])
            broken = copy.deepcopy(provenance)
            broken['model_ids'].pop()
            with self.assertRaisesRegex(ValueError, 'inventory'):
                cache._read_archive(broken, [{}, {}, {}], repo_root=root)
            chunk.write_bytes(b'CORRUPTED SYNTHETIC CHUNK')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                cache._read_archive(provenance, [{}, {}, {}], repo_root=root)

    def test_merge_refuses_duplicate_indices_instead_of_double_counting_a_card(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / 'native.csv'
            _, bars = self.native_csv_fixture(native)
            digest = hashlib.sha256(native.read_bytes()).hexdigest()
            provenance = {'source_sha256': '2' * 64, 'csv_sha256': digest, 'symbol': 'SYNTHETIC',
                          'timeframe': 'H1', 'point': .00001, 'profile': 'CONTINUOUS', 'start_index': 0}
            study = {'cache_provenance': provenance, 'source_data_sha256': digest,
                     'native_csv_sha256': digest, 'symbol': 'SYNTHETIC', 'timeframe': 'H1', 'bars': len(bars)}
            metadata = {'csv_sha256': digest, 'symbol': 'SYNTHETIC', 'timeframe': 'H1',
                        'point': .00001, 'contract_size': 100000, 'profit_currency': 'USD'}
            study_path, metadata_path = root / 'study.json', root / 'metadata.json'
            study_path.write_text(json.dumps(study), encoding='utf-8')
            metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
            cards = {model: [] for model in REGISTRY}
            cards[next(iter(REGISTRY))] = [{'index': 1, 'card': {}}, {'index': 1, 'card': {}}]
            counts = {model: Counter() for model in REGISTRY}
            with patch.object(cache, 'verify_archive_source', return_value={}), \
                    patch.object(cache, '_read_archive', return_value=(cards, counts, [])), \
                    self.assertRaisesRegex(ValueError, 'Overlapping'):
                cache.load_context_cache(study_path, native, metadata_path, with_training_prefix=False)
