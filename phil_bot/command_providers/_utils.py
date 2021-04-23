import contextlib
import json
import os

from atools import memoize
import memcache
import urllib3


SETTINGS = {}
with open(os.path.normpath(os.path.join(os.path.split(str(__file__))[0], '..', 'secrets', 'ysk.json')), 'r') as f:
    SETTINGS.update(json.load(f))

OAUTH_TOKEN = SETTINGS.get('OAUTH_TOKEN', None)
FOLDER_ID = SETTINGS.get('FOLDER_ID', None)


mc = memcache.Client(['127.0.0.1:11211'], debug=0)


@memoize(duration=3600 * 11)
def get_iam_token():

    iam_token = mc.get(f'get_iam_token')

    if not iam_token:

        url = f'https://iam.api.cloud.yandex.net/iam/v1/tokens?yandexPassportOauthToken={OAUTH_TOKEN}'

        http = urllib3.PoolManager()
        resp = http.request('POST', url)

        decode_response = resp.data.decode('utf-8')
        text = json.loads(decode_response)
        iam_token = text.get('iamToken')
        expires_iam_token = text.get('expiresAt')

        mc.set(f'get_iam_token', iam_token, time=3600 * 2)

    return iam_token


@contextlib.contextmanager
def temporary_filename(suffix=None):
    """Context that introduces a temporary file.

    Creates a temporary file, yields its name, and upon context exit, deletes it.
    (In contrast, tempfile.NamedTemporaryFile() provides a 'file' object and
    deletes the file as soon as that file object is closed, so the temporary file
    cannot be safely re-opened by another library or process.)

    Args:
      suffix: desired filename extension (e.g. '.mp4').

    Yields:
      The name of the temporary file.
    """
    import tempfile
    try:
        f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp_name = f.name
        f.close()
        yield tmp_name
    finally:
        os.unlink(tmp_name)
