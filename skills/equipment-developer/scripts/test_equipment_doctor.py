#!/usr/bin/env python3
"""Self-tests for equipment_doctor.py.

Run from anywhere:
    python skills/equipment-developer/scripts/test_equipment_doctor.py
"""

from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import equipment_doctor  # noqa: E402  (path set above)

CLEAN_FILES = {
    "app/__init__.py": """
        from dependency_injector.providers import ThreadSafeSingleton as Singleton
        from equipment import Equipment
        from app.Scheduler import Scheduler


        class App(Equipment):
            scheduler = Singleton(Scheduler, Equipment.log, Equipment.queue, Equipment.config.app.env)


        def app(base_path=None):
            return App.make(base_path)
    """,
    "app/Scheduler.py": """
        from equipment.Scheduler.Scheduler import Scheduler as Equipment


        class Scheduler(Equipment):
            def __init__(self, log, queue, env):
                super().__init__(log)
                self.queue = queue
                self.env = env

            def run(self):
                super().run()
    """,
    "app/jobs.py": """
        from app import app


        def rebuild(report_id):
            app().log().info("rebuild", extra={"report_id": report_id})
    """,
    "config/app.yaml": """
        app:
          name: ${APP_NAME:Demo}
          env: ${APP_ENV:local}
    """,
    "config/database.yaml": """
        database:
          connection: ${DB_CONNECTION:sqlite}
          connections:
            sqlite:
              schema: sqlite
              database: "${DB_DATABASE:database/database.sqlite}"
            mysql:
              schema: "mysql+mysqlconnector"
    """,
    "config/storage.yaml": """
        storage:
          disk: ${FILESYSTEM_DISK:local}
          disks:
            local:
              path: storage/app
    """,
    "config/log.yaml": """
        log:
          level: ${LOG_LEVEL:debug}
          channel: ${LOG_CHANNEL:stack}
          channels:
            single:
              filename: 'storage/logs/app.log'
    """,
    "storage/logs/.gitignore": "*\n",
    "queues.py": """
        from redis import Redis
        from rq import Worker

        redis = Redis(host="127.0.0.1", port=6379, db=0, username=None, password=None)
        Worker(["default"], connection=redis).work(with_scheduler=True)
    """,
    "tests/__init__.py": "",
    "tests/test_jobs.py": """
        import unittest


        class JobsTest(unittest.TestCase):
            def test_sync_lambda_is_fine_in_tests(self) -> None:
                queue = None
                if queue:
                    queue.push(lambda: None)
    """,
    ".coveragerc": """
        [run]
        omit =
            */tests/*
            *.pyx
    """,
    ".env": """
        APP_ENV=local
        DB_CONNECTION=sqlite
        DB_DATABASE=database/database.sqlite
        REDIS_PASSWORD=
    """,
    "database/migrations/env.py": """
        from app.models import Base

        target_metadata = Base.metadata
    """,
    "pyproject.toml": """
        [project]
        name = "demo"
        dependencies = [
            "equipment>=1.0.0",
            # "mysql-connector-python>=9.1,<10",
        ]
    """,
    "README.md": "Run tests with `python -m unittest`.\n",
}


class DoctorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.write_files(CLEAN_FILES)

    def write_files(self, files: dict[str, str]) -> None:
        for relative, content in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")

    def codes(self) -> set[str]:
        return {finding.code for finding in equipment_doctor.run_checks(self.root)}

    def run_main(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = equipment_doctor.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()


class CleanProjectTest(DoctorTestCase):
    def test_clean_project_has_no_findings(self) -> None:
        self.assertEqual(set(), self.codes())

    def test_main_exit_code_zero_when_clean(self) -> None:
        code, stdout, _ = self.run_main(str(self.root))
        self.assertEqual(0, code)
        self.assertIn("No known pitfalls found.", stdout)

    def test_main_rejects_non_equipment_directory(self) -> None:
        empty = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty, True)
        code, _, stderr = self.run_main(str(empty))
        self.assertEqual(2, code)
        self.assertIn("does not look like an Equipment project", stderr)

    def test_main_exit_code_zero_with_info_only(self) -> None:
        self.write_files({"tests/app/__init__.py": ""})
        code, stdout, _ = self.run_main(str(self.root))
        self.assertEqual(0, code)
        self.assertIn("[INFO] EQ001", stdout)

    def test_main_exit_code_one_with_warnings(self) -> None:
        self.write_files({
            "tests/app/__init__.py": "",
            "README.md": "python -m unittest discover -s tests\n",
        })
        code, stdout, _ = self.run_main(str(self.root))
        self.assertEqual(1, code)
        self.assertIn("[WARNING] EQ002", stdout)


class TestingChecksTest(DoctorTestCase):
    def test_eq001_and_eq002_shadowing_test_package_and_failing_command(self) -> None:
        self.write_files({
            "tests/app/__init__.py": "",
            "README.md": "python -m unittest discover -s tests\npython -m unittest discover -s tests -t .\n",
            ".github/workflows/test.yml": "run: python -m coverage run -m unittest discover -s tests\n",
        })
        findings = equipment_doctor.run_checks(self.root)
        paths = {(f.code, f.path) for f in findings}
        self.assertIn(("EQ001", "tests/app/__init__.py"), paths)
        self.assertIn(("EQ002", "README.md:1"), paths)
        self.assertNotIn(("EQ002", "README.md:2"), paths)
        self.assertIn(("EQ002", ".github/workflows/test.yml:1"), paths)

    def test_eq002_requires_a_shadowing_package(self) -> None:
        self.write_files({"README.md": "python -m unittest discover -s tests\n"})
        self.assertNotIn("EQ002", self.codes())

    def test_eq003_coveragerc_pattern(self) -> None:
        self.write_files({".coveragerc": "[run]\nomit = *tests*\n"})
        self.assertIn("EQ003", self.codes())


class ConfigChecksTest(DoctorTestCase):
    def test_eq010_production_env(self) -> None:
        self.write_files({".env": "APP_ENV=production\n"})
        self.assertIn("EQ010", self.codes())

    def test_eq011_sqlite_bare_database_name(self) -> None:
        self.write_files({".env": "DB_CONNECTION=sqlite\nDB_DATABASE=equipment\n"})
        self.assertIn("EQ011", self.codes())

    def test_eq011_uses_yaml_default_when_connection_unset(self) -> None:
        self.write_files({".env": "DB_DATABASE=equipment\n"})
        self.assertIn("EQ011", self.codes())

    def test_eq011_ignores_unset_connection_with_non_sqlite_default(self) -> None:
        self.write_files({
            ".env": "DB_DATABASE=equipment\n",
            "config/database.yaml": "database:\n  connection: ${DB_CONNECTION:postgresql}\n",
        })
        self.assertNotIn("EQ011", self.codes())

    def test_eq011_ignores_paths_and_memory(self) -> None:
        for value in ("database/database.sqlite", ":memory:", "data.db"):
            with self.subTest(value=value):
                self.write_files({".env": f"DB_CONNECTION=sqlite\nDB_DATABASE={value}\n"})
                self.assertNotIn("EQ011", self.codes())

    def test_eq012_mysql_without_driver(self) -> None:
        self.write_files({".env": "DB_CONNECTION=mysql\n"})
        self.assertIn("EQ012", self.codes())

    def test_eq012_mysql_with_driver(self) -> None:
        self.write_files({
            ".env": "DB_CONNECTION=mysql\n",
            "pyproject.toml": '[project]\ndependencies = ["mysql-connector-python>=9.1,<10"]\n',
        })
        self.assertNotIn("EQ012", self.codes())

    def test_eq020_alembic_metadata_none(self) -> None:
        self.write_files({"database/migrations/env.py": "target_metadata = None\n"})
        self.assertIn("EQ020", self.codes())

    def test_eq060_storage_root_key(self) -> None:
        self.write_files({
            "config/storage.yaml": "storage:\n  disk: local\n  disks:\n    local:\n      root: storage/app\n",
        })
        self.assertIn("EQ060", self.codes())

    def test_eq080_missing_log_directory(self) -> None:
        shutil.rmtree(self.root / "storage" / "logs")
        self.assertIn("EQ080", self.codes())


class SourceChecksTest(DoctorTestCase):
    def test_eq030_push_at_without_scheduler(self) -> None:
        self.write_files({
            "app/jobs.py": "def later(queue, when, job):\n    queue.push_at(when, job, 1)\n",
            "queues.py": "from rq import Worker\nWorker(['default']).work()\n",
        })
        self.assertIn("EQ030", self.codes())

    def test_eq031_redis_credentials_ignored(self) -> None:
        self.write_files({
            ".env": "REDIS_PASSWORD=s3cret\n",
            "queues.py": "from redis import Redis\nredis = Redis(host='h', port=1, db=0)\n",
        })
        findings = [f for f in equipment_doctor.run_checks(self.root) if f.code == "EQ031"]
        self.assertEqual(1, len(findings))
        self.assertIn("queues.py", findings[0].message)
        self.assertIn("RedisQueue", findings[0].message)

    def test_eq031_satisfied_by_override_and_worker_credentials(self) -> None:
        self.write_files({
            ".env": "REDIS_PASSWORD=s3cret\n",
            "app/__init__.py": textwrap.dedent(CLEAN_FILES["app/__init__.py"]).replace(
                "class App(Equipment):\n",
                "class App(Equipment):\n    queue = Singleton(AppQueueFactory, Equipment.config.queue, Equipment.log)\n",
            ),
        })
        self.assertNotIn("EQ031", self.codes())

    def test_eq032_queued_lambda_outside_tests(self) -> None:
        self.write_files({"app/jobs.py": "def go(queue):\n    queue.push(lambda: None)\n"})
        self.assertIn("EQ032", self.codes())

    def test_eq040_stale_framework_provider_reference(self) -> None:
        self.write_files({
            "app/__init__.py": textwrap.dedent("""
                from equipment import Equipment


                class App(Equipment):
                    queue = Singleton(AppQueueFactory, Equipment.config.queue, Equipment.log)
                    scheduler = Singleton(Scheduler, Equipment.log, Equipment.queue)
            """),
        })
        self.assertIn("EQ040", self.codes())

    def test_eq041_scheduler_reads_self_config(self) -> None:
        self.write_files({
            "app/Scheduler.py": textwrap.dedent("""
                from equipment.Scheduler.Scheduler import Scheduler as Equipment


                class Scheduler(Equipment):
                    def run(self):
                        if self.config.app.env() == "production":
                            pass
                        super().run()
            """),
        })
        self.assertIn("EQ041", self.codes())

    def test_unparsable_python_is_skipped(self) -> None:
        self.write_files({"app/broken.py": "def broken(:\n"})
        self.assertEqual(set(), self.codes())


class CompileChecksTest(DoctorTestCase):
    def test_eq050_virtualenv_and_build_inside_project(self) -> None:
        self.write_files({".venv/pyvenv.cfg": "home = /usr/bin\n", "build/lib/app/x.py": ""})
        findings = {(f.code, f.path) for f in equipment_doctor.run_checks(self.root)}
        self.assertIn(("EQ050", ".venv/"), findings)
        self.assertIn(("EQ050", "build/"), findings)

    def test_virtualenv_sources_are_not_parsed(self) -> None:
        self.write_files({
            ".venv/pyvenv.cfg": "home = /usr/bin\n",
            ".venv/lib/site.py": "queue.push(lambda: None)\n",
        })
        self.assertNotIn("EQ032", self.codes())


if __name__ == "__main__":
    unittest.main()
