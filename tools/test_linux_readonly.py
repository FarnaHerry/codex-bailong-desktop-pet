"""The CLI may live inside CODEX_HOME, which the sandbox deliberately hides."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class ReadonlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('bwrap'):
            raise unittest.SkipTest('bubblewrap is not installed')
        probe = subprocess.run(['bwrap', '--ro-bind', '/', '/', '/bin/true'], capture_output=True, timeout=5)
        if probe.returncode:
            raise unittest.SkipTest('host does not permit bubblewrap user namespaces')

    def test_binary_inside_hidden_home_remains_executable_and_config_readonly(self):
        # Outside /tmp: the wrapper replaces /tmp with a private writable mount.
        with tempfile.TemporaryDirectory(prefix='bailong-sandbox-test-', dir=Path.home()) as folder:
            home = Path(folder)
            config = home / 'config.toml'
            config.write_text('synthetic-test-config\n')
            binary = home / 'bin/codex'
            binary.parent.mkdir()
            binary.write_text('''#!/bin/sh
set -eu
test "$1" = -c
test "$3" = app-server
test "$(cat "$CODEX_HOME/config.toml")" = synthetic-test-config
if (echo changed > "$CODEX_HOME/config.toml") 2>/dev/null; then exit 23; fi
echo runtime > "$CODEX_HOME/runtime-test"
echo sandbox-ok
''')
            binary.chmod(0o755)
            wrapper = Path(__file__).resolve().parents[1] / 'linux_app/codex_readonly'
            env = dict(os.environ, CODEX_HOME=str(home), BAILONG_NATIVE_CODEX=str(binary), BAILONG_FROZEN='0')
            result = subprocess.run([str(wrapper), 'app-server'], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'sandbox-ok')
            self.assertEqual(config.read_text(), 'synthetic-test-config\n')
            self.assertFalse((home / 'runtime-test').exists())
