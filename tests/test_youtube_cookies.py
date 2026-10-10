import importlib.util
from pathlib import Path
import stat

from dotenv import dotenv_values
import pytest

spec = importlib.util.spec_from_file_location('cookie_setup', Path(__file__).parents[1] / 'scripts/configure-youtube-cookies.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def export(project, lines):
    folder = project / 'private'
    folder.mkdir()
    path = folder / 'youtube-cookies.txt'
    path.write_text('# Netscape HTTP Cookie File\n' + lines)
    return path


def test_cookie_setup_filters_other_sites_and_preserves_existing_configuration(tmp_path):
    path = export(tmp_path, '.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tsynthetic-session\n'
                           '.example.com\tTRUE\t/\tTRUE\t0\tSID\tunrelated-session\n')
    (tmp_path / '.env').write_text('HF_TOKEN=synthetic-token\nMUSCRIPTOR_MODEL=small\n')
    setup.configure(tmp_path)
    assert 'unrelated-session' not in path.read_text()
    values = dotenv_values(tmp_path / '.env')
    assert values['HF_TOKEN'] == 'synthetic-token'
    assert values['YOUTUBE_COOKIES_FILE'] == str(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / 'private').stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / '.env').stat().st_mode) == 0o600
    setup.configure(tmp_path)
    assert (tmp_path / '.env').read_text().count('YOUTUBE_COOKIES_FILE') == 1


@pytest.mark.parametrize('contents', [
    '{}',
    '.youtube.com\tTRUE\t/\tTRUE\t1\tSID\texpired\n',
    '.example.com\tTRUE\t/\tTRUE\t0\tSID\tother-site\n',
])
def test_cookie_setup_rejects_invalid_expired_or_unrelated_sessions(tmp_path, contents):
    path = export(tmp_path, contents)
    previous = path.read_bytes()
    with pytest.raises(ValueError):
        setup.configure(tmp_path)
    assert path.read_bytes() == previous
    assert not (tmp_path / '.env').exists()


def test_cookie_setup_does_not_follow_a_cookie_symlink(tmp_path):
    (tmp_path / 'private').mkdir()
    target = tmp_path / 'unrelated.txt'
    target.write_text('leave unchanged')
    (tmp_path / 'private/youtube-cookies.txt').symlink_to(target)
    with pytest.raises(ValueError):
        setup.configure(tmp_path)
    assert target.read_text() == 'leave unchanged'
