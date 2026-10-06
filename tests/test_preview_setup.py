"""Exercise preview bootstrapping without downloading packages in unit tests."""
import os
from pathlib import Path
import shutil
import subprocess


def fixture_project(tmp_path, fail_install=False):
    root = Path(__file__).resolve().parent.parent
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    for name in ['prepare-codespace.sh', 'start-codespace.sh']:
        shutil.copyfile(root / 'scripts' / name, scripts / name)
    for name in ['server/requirements.txt', 'src/App.jsx', 'package-lock.json', 'index.html',
                 'vite.config.js', 'postcss.config.js', 'tailwind.config.js']:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fixture\n')
    setup = 'exit 17\n' if fail_install else '''
echo setup >>calls.log
mkdir -p .venv/bin node_modules/.bin
printf '#!/bin/sh\nexit 0\n' >.venv/bin/python
printf '#!/bin/sh\nexit 0\n' >node_modules/.bin/vite
chmod +x .venv/bin/python node_modules/.bin/vite
'''
    (scripts / 'setup.sh').write_text('#!/usr/bin/env bash\nset -e\n' + setup)
    tools = tmp_path / 'tools'
    tools.mkdir()
    for name in ['node','ffmpeg','ffprobe']:
        (tools / name).write_text('#!/bin/sh\nexit 0\n')
        (tools / name).chmod(0o755)
    (tools / 'npm').write_text('''#!/bin/sh
echo build >>calls.log
mkdir -p dist
echo '<title>BayanFlow</title>' >dist/index.html
''')
    (tools / 'npm').chmod(0o755)
    return dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'])


def prepare(tmp_path, environment):
    return subprocess.run(['bash','scripts/prepare-codespace.sh'],cwd=tmp_path,env=environment,
                          capture_output=True,text=True,timeout=15)


def test_missing_environment_is_installed_and_player_built(tmp_path):
    environment = fixture_project(tmp_path)
    assert not (tmp_path / '.venv').exists()
    result = prepare(tmp_path, environment)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / '.venv/bin/python').exists()
    assert (tmp_path / 'dist/index.html').exists()
    assert (tmp_path / 'calls.log').read_text().splitlines() == ['setup','build']


def test_repeated_startup_reuses_dependencies_and_build(tmp_path):
    environment = fixture_project(tmp_path)
    assert prepare(tmp_path, environment).returncode == 0
    assert prepare(tmp_path, environment).returncode == 0
    assert (tmp_path / 'calls.log').read_text().splitlines() == ['setup','build']


def test_missing_frontend_rebuilds_without_reinstalling_dependencies(tmp_path):
    environment = fixture_project(tmp_path)
    assert prepare(tmp_path, environment).returncode == 0
    (tmp_path / 'dist/index.html').unlink()
    assert prepare(tmp_path, environment).returncode == 0
    assert (tmp_path / 'calls.log').read_text().splitlines() == ['setup','build','build']


def test_installer_failure_stops_startup_and_does_not_mark_setup_ready(tmp_path):
    environment = fixture_project(tmp_path, fail_install=True)
    result = subprocess.run(['bash','scripts/start-codespace.sh'],cwd=tmp_path,env=environment,
                            capture_output=True,text=True,timeout=15)
    assert result.returncode == 17
    assert not (tmp_path / '.cache/codespace-setup.sha256').exists()
    assert not (tmp_path / '.cache/codespace-server.pid').exists()
    assert not (tmp_path / 'dist').exists()
