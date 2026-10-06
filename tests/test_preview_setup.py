"""Exercise preview bootstrapping without downloading packages in unit tests."""
import os
from pathlib import Path
import shutil
import subprocess


def fixture_project(tmp_path, fail_install=False):
    root = Path(__file__).resolve().parent.parent
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    for name in ['prepare-codespace.sh', 'start-codespace.sh', 'install-codespace-prerequisites.sh']:
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


def test_prerequisite_install_uses_signed_debian_sources_for_both_commands(tmp_path):
    environment = fixture_project(tmp_path)
    sudo = tmp_path / 'tools/sudo'
    sudo.write_text('''#!/usr/bin/env python3
from pathlib import Path
import json, sys
args = sys.argv[1:]
source_arg = next(arg for arg in args if arg.startswith('Dir::Etc::sourcelist='))
source = Path(source_arg.split('=', 1)[1])
with open('apt-calls.jsonl', 'a') as output:
    output.write(json.dumps({'args': args, 'sources': source.read_text()}) + '\\n')
''')
    sudo.chmod(0o755)
    result = subprocess.run(['bash', 'scripts/install-codespace-prerequisites.sh'],
                            cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    import json
    calls = [json.loads(line) for line in (tmp_path / 'apt-calls.jsonl').read_text().splitlines()]
    assert len(calls) == 2
    assert calls[0]['args'][-1] == 'update'
    assert calls[1]['args'][-4:] == ['install', '-y', 'ffmpeg', 'python3-venv']
    for call in calls:
        assert 'Dir::Etc::sourceparts=-' in call['args']
        assert 'APT::Update::Error-Mode=any' in call['args']
        assert 'deb.debian.org/debian' in call['sources']
        assert 'deb.debian.org/debian-security' in call['sources']
        assert call['sources'].count('Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg') == 2
        assert 'yarn' not in call['sources']
        assert not any('AllowUnauthenticated' in arg or 'AllowInsecure' in arg for arg in call['args'])
        sources_path = next(arg.split('=', 1)[1] for arg in call['args'] if arg.startswith('Dir::Etc::sourcelist='))
        assert not Path(sources_path).exists()
