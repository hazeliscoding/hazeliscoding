#!/usr/bin/env python3
"""Update a bounded block of README with public GitHub releases. Standard library only."""
import json
import os
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / 'README.md'
START = '<!-- START:ACTIVITY -->'
END = '<!-- END:ACTIVITY -->'
REPOS = ['xiv-vault', 'gil-sweep', 'pr-sweep', 'prompuff', 'sdl3-porter']

def releases(repo):
    url = f'https://api.github.com/repos/hazeliscoding/{repo}/releases?per_page=5'
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'hazel-profile-activity',
        **({'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']} if os.getenv('GITHUB_TOKEN') else {}),
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)

def main():
    current = README.read_text(encoding='utf-8')
    if current.count(START) != 1 or current.count(END) != 1 or current.index(START) > current.index(END):
        raise ValueError('Expected exactly one correctly ordered activity block')
    found = []
    for repo in REPOS:
        try:
            for release in releases(repo):
                if not release.get('draft') and not release.get('prerelease'):
                    found.append((release.get('published_at') or '', repo, release['tag_name'], release['html_url']))
                    break
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
            print(f'Warning: {repo}: {exc}')
    if not found:
        print('No GitHub release data available; existing README untouched')
        return
    _, repo, tag, url = max(found)
    if not url.startswith(f'https://github.com/hazeliscoding/{repo}/releases/'):
        raise ValueError('Unexpected release URL')
    block = f'- 📦 Latest featured release: [{repo} {tag}]({url})\n- ✍️ Featured writing: [Every trap is proven](https://www.hazeliscoding.dev/blog/every-trap-is-proven)\n'
    before, tail = current.split(START, 1)
    _, after = tail.split(END, 1)
    updated = before + START + '\n' + block + END + after
    if current != updated:
        README.write_text(updated, encoding='utf-8')
        print(f'Updated latest release: {repo} {tag}')
    else:
        print('No README changes')

if __name__ == '__main__':
    main()
