"""Install a browser-exported YouTube cookie file without displaying credentials."""
from http.cookiejar import LoadError, MozillaCookieJar
from pathlib import Path
import os
import sys
import warnings

from dotenv import set_key


def configure(project):
    private = project / 'private'
    source = private / 'youtube-cookies.txt'
    env_file = project / '.env'
    if private.is_symlink() or source.is_symlink() or env_file.is_symlink():
        raise ValueError('Use regular files and a regular private folder, not symbolic links.')
    if not source.is_file():
        raise ValueError('Upload youtube-cookies.txt into the private folder first.')
    os.chmod(private, 0o700)
    os.chmod(source, 0o600)
    if source.stat().st_size > 1024 * 1024:
        raise ValueError('Cookie export is too large. Export only youtube.com cookies.')
    jar = MozillaCookieJar(str(source))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            jar.load(ignore_discard=True, ignore_expires=True)
    except (LoadError, UnicodeError, ValueError):
        raise ValueError('Export in Netscape cookies.txt format, not JSON.') from None
    # Browser exports use expiry 0 for session cookies; match yt-dlp's handling.
    for cookie in jar:
        if cookie.expires == 0:
            cookie.expires = None
            cookie.discard = True
    youtube = [cookie for cookie in jar if cookie.domain.lstrip('.') == 'youtube.com' and not cookie.is_expired()]
    auth_names = {'SID', '__Secure-1PSID', '__Secure-3PSID'}
    if not any(cookie.name in auth_names and cookie.value for cookie in youtube):
        raise ValueError('No current YouTube login found. Sign in and export a fresh YouTube session.')
    # Keep only YouTube cookies, even if an extension exported other sites.
    jar.clear()
    for cookie in youtube:
        jar.set_cookie(cookie)
    temporary = private / '.youtube-cookies.tmp'
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        jar.save(str(temporary), ignore_discard=True, ignore_expires=False)
        temporary.replace(source)
    finally:
        temporary.unlink(missing_ok=True)
    if not env_file.exists():
        descriptor = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
    os.chmod(env_file, 0o600)
    set_key(str(env_file), 'YOUTUBE_COOKIES_FILE', str(source.resolve()))


if __name__ == '__main__':
    try:
        configure(Path(__file__).resolve().parent.parent)
    except (OSError, ValueError):
        # Do not print exception contents: cookie parser errors may include values.
        print('Cookie setup failed. Check that private/youtube-cookies.txt is a fresh Netscape-format export from a signed-in YouTube session. No cookie values were printed.', file=sys.stderr)
        raise SystemExit(1)
    print('YouTube login cookies configured privately. Restart BayanFlow, then retry the video. This does not yet verify YouTube access.')
