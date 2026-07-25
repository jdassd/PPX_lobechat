import glob
import os
import tempfile
import unittest
from unittest import mock

from cryptography.fernet import Fernet

from pyapp.db.json.db import SessionDB


class JsonDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.key = Fernet.generate_key()

    def _session(self, path):
        key_patch = mock.patch('pyapp.db.json.db.getDBKey', return_value=self.key)
        key_patch.start()
        self.addCleanup(key_patch.stop)
        return SessionDB(path)

    def test_session_persists_encrypted_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'base.json')
            with self._session(path) as database:
                database.table('items').insert({'value': 42})

            with self._session(path) as database:
                self.assertEqual(database.table('items').all(), [{'value': 42}])

    def test_failed_replace_preserves_previous_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'base.json')
            with self._session(path) as database:
                database.table('items').insert({'value': 'original'})
            with open(path, 'rb') as handler:
                original = handler.read()

            with self.assertRaises(OSError):
                with mock.patch('pyapp.db.json.db.os.replace', side_effect=OSError('replace failed')):
                    with self._session(path) as database:
                        database.table('items').insert({'value': 'new'})

            with open(path, 'rb') as handler:
                self.assertEqual(handler.read(), original)
            self.assertEqual(glob.glob(path + '.*.tmp'), [])


if __name__ == '__main__':
    unittest.main()
