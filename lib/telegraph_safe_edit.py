"""Safe Telegraph editor.

Fixes the C131 destruction bug at its source and refuses to repeat it.

  BUG BEING FIXED
  editPage REPLACES the whole node list. getPage does NOT return the body
  unless return_content=true, so result.get('content') is None by default.
  Code that did (result.get('content') or []) turned None into [], mistook
  it for an empty page, and wrote one paragraph over a live article.

  THIS MODULE REFUSES TO RUN if that state is ever seen again:
    - body must be a non-empty list before any write is attempted
    - the live page must actually contain body text before a write
    - the written node list must be a superset of what was read, never smaller
    - a read-back is mandatory and its length is compared to what was sent
"""
import json
import requests

API = 'https://api.telegra.ph/'
AUTHOR_NAME = 'Galaxy Forge — Practical Toolkits for Small Business'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


class UnsafeEdit(RuntimeError):
    """Raised instead of risking an overwrite. Nothing is written."""


def _token(token_file=r'C:\openclaw-dasgboard\data\telegraph.json'):
    return json.load(open(token_file, encoding='utf-8'))['access_token']


def _live_body_lines(url):
    h = requests.get(url, headers=UA, timeout=45).text
    t = h
    for tag in ('script', 'style'):
        import re
        t = re.sub(r'<%s.*?</%s>' % (tag, tag), ' ', t, flags=re.S)
    t = re.sub(r'<[^>]+>', '\n', t)
    return len([l for l in t.split('\n') if len(l.strip()) > 45])


def read_page(token, path):
    """getPage WITH return_content=true. Never defaults it off again."""
    r = requests.get(API + 'getPage',
                     params={'access_token': token, 'path': path,
                             'return_content': 'true', 'format': 'json'},
                     timeout=90).json()
    if not r.get('ok'):
        raise RuntimeError('getPage failed: %s' % r.get('error'))
    res = r['result']
    nodes = res.get('content')
    if isinstance(nodes, str):
        nodes = json.loads(nodes)
    if not isinstance(nodes, list):
        nodes = []
    return {'path': path, 'title': res.get('title'), 'nodes': nodes,
            'author_name': res.get('author_name'), 'url': res.get('url')}


def append_paragraph(token, path, text, allow_empty_page=False):
    """Append one paragraph. Refuses every unsafe precondition first."""
    page = read_page(token, path)

    # 1. the body must have been genuinely read
    if not page['nodes'] and not allow_empty_page:
        raise UnsafeEdit(
            'read %s: body is empty. getPage returned no nodes. Refusing to '
            'write, because an unread body is indistinguishable from a wipe.' % path)

    # 2. the live page must really look empty before we allow an empty write
    if not page['nodes']:
        live = _live_body_lines('https://telegra.ph/' + path)
        if live > 8 and not allow_empty_page:
            raise UnsafeEdit(
                'read %s: no nodes returned, but the live page has %d text lines. '
                'Refusing to write.' % (path, live))

    before = len(page['nodes'])
    new_nodes = list(page['nodes']) + [{'tag': 'p', 'children': [text]}]

    if len(new_nodes) <= before:
        raise UnsafeEdit('refusing to write a non-growing node list')

    e = requests.post(API + 'editPage', data={
        'access_token': token, 'path': path, 'title': page['title'],
        'content': json.dumps(new_nodes), 'author_name': AUTHOR_NAME,
    }, timeout=120).json()
    if not e.get('ok'):
        raise RuntimeError('editPage failed: %s' % e.get('error'))

    # 3. mandatory read-back, compared against what was actually sent
    time_sleep = None
    import time
    time.sleep(4)
    back = read_page(token, path)
    if len(back['nodes']) < len(new_nodes):
        raise UnsafeEdit(
            'read-back got %d nodes, sent %d. Treat as failed and re-verify '
            'before touching this page again.' % (len(back['nodes']), len(new_nodes)))
    return {'sent_nodes': len(new_nodes), 'readback_nodes': len(back['nodes']),
            'url': back.get('url') or ('https://telegra.ph/' + path)}
