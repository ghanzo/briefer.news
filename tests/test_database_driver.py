import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from db.models import get_engine


class DatabaseDriverTests(unittest.TestCase):
    def test_bare_postgres_url_loads_installed_driver_without_connecting(self):
        url = "postgresql://user:p%40ss@localhost/example?sslmode=require"
        with patch.dict(os.environ, {"DATABASE_URL": url}):
            engine = get_engine()
        try:
            self.assertEqual(engine.dialect.driver, "psycopg2")
            self.assertEqual(engine.url.password, "p@ss")
            self.assertEqual(engine.url.query["sslmode"], "require")
        finally:
            engine.dispose()

    def test_explicit_driver_is_preserved(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://user@localhost/example"}):
            engine = get_engine()
        try:
            self.assertEqual(engine.dialect.driver, "psycopg2")
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
