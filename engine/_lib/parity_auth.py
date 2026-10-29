"""Direct two-session HTTP authorization proof; never accepts a candidate command's claims."""
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from .common import CgspecError


def prove(config, origin, revision):
    if not isinstance(config, dict) or not isinstance(config.get('accounts'), list) or len(config['accounts']) != 2:
        raise CgspecError('authorization requires two independently authenticated accounts')
    accounts = config['accounts']
    records = []
    identities = []
    def request(path, _token=None):
        if not isinstance(path, str) or not path.startswith('/') or path.startswith('//') or '?' in path:
            raise CgspecError('authorization endpoint must be an absolute app path without mock parameters')
        url = urllib.parse.urljoin(origin, path)
        headers = {}
        if _token:
            scheme = 'Bearer'
            headers['Authorization'] = f'{scheme} {_token}'
        req = urllib.request.Request(url, headers=headers)
        try:
            response = urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as exc:
            response = exc
        if urllib.parse.urlsplit(response.url).netloc != urllib.parse.urlsplit(origin).netloc:
            raise CgspecError('authorization request redirected outside app')
        with response:
            body = response.read()
            records.append({'path': path, 'status': response.code, 'body_sha256': hashlib.sha256(body).hexdigest()})
            return response.code, body
    tokens = []
    for account in accounts:
        key = account.get('token_env', '')
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*', key) or not os.environ.get(key):
            raise CgspecError('authorization account requires a populated token_env')
        tokens.append(os.environ[key])
    if tokens[0] == tokens[1]:
        raise CgspecError('authorization sessions must use distinct credentials')
    for index, account in enumerate(accounts):
        status, body = request(config.get('identity_path'), tokens[index])
        try:
            identity = json.loads(body).get('id')
        except ValueError:
            identity = None
        if status != 200 or not isinstance(identity, str) or not identity:
            raise CgspecError('authenticated identity request did not establish account identity')
        identities.append(identity)
        if request(account.get('resource_path'), tokens[index])[0] != 200:
            raise CgspecError('account cannot read its own resource')
        if request(accounts[1-index].get('resource_path'), tokens[index])[0] not in (401, 403, 404):
            raise CgspecError('cross-account resource access was not denied')
        if request(account.get('resource_path'))[0] not in (401, 403, 404):
            raise CgspecError('anonymous resource access was not denied')
    if len(set(identities)) != 2:
        raise CgspecError('identity endpoint did not establish two distinct accounts')
    return {'revision': revision, 'authenticated_accounts': identities, 'requests': records,
            'scope': 'executed HTTP identity, own-resource, cross-account and anonymous authorization assertions'}
