#!/usr/bin/env python3
"""Update bounded blocks of README with public GitHub releases and upstream pull requests. Standard library only."""
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / 'README.md'
START = '<!-- START:ACTIVITY -->'
END = '<!-- END:ACTIVITY -->'
OSS_START = '<!-- START:OSS -->'
OSS_END = '<!-- END:OSS -->'
REPOS = {
    'xiv-vault': 'XIV Vault',
    'gil-sweep': 'Gil Sweep',
    'pr-sweep': 'PR Sweep',
    'prompuff': 'Prompuff',
    'sweepling': 'Sweepling',
    'conatlas-tx': 'ConAtlas TX',
    'sdl3-porter': 'sdl3-porter',
}
# Only these upstream projects appear, so work orgs and PRs that list my own apps never do.
OSS = {
    'BCUninstaller/Bulk-Crap-Uninstaller': ('🗑️', 'Bulk Crap Uninstaller', 'made BCU-console scriptable with JSON output and a dry-run mode, and I help triage'),
    'storytold/pdfcraft': ('📄', 'PdfCraft', 'rendering and UI fixes in a PDF reader written from scratch in Rust'),
    'goatcorp/FFXIVQuickLauncher': ('🚀', 'XIVLauncher', 'a fix for a login crash on unreadable game files'),
    'goatcorp/XIVLauncher.Core': ('🐧', 'XIVLauncher.Core', 'creates a missing game folder before patching'),
}
FETCH_ERRORS = (urllib.error.URLError, TimeoutError, ValueError, KeyError)

def api(path):
    req = urllib.request.Request('https://api.github.com/' + path, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'hazel-profile-activity',
        **({'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']} if os.getenv('GITHUB_TOKEN') else {}),
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)

def plural(count, word):
    return f'{count} {word}' + ('' if count == 1 else 's')

def stars(count):
    return str(count) if count < 1000 else f'{count / 1000:.1f}'.removesuffix('.0') + 'k'

def release_block():
    found = []
    for repo in REPOS:
        try:
            for release in api(f'repos/hazeliscoding/{repo}/releases?per_page=5'):
                if not release.get('draft') and not release.get('prerelease'):
                    found.append((release.get('published_at') or '', repo, release['tag_name'], release['html_url']))
                    break
        except FETCH_ERRORS as exc:
            print(f'Warning: {repo}: {exc}')
    if not found:
        return None
    _, repo, tag, url = max(found)
    if not url.startswith(f'https://github.com/hazeliscoding/{repo}/releases/'):
        raise ValueError('Unexpected release URL')
    return f'- 📦 Latest featured release: [{REPOS[repo]} {tag}]({url})\n- ✍️ Featured writing: [Every trap is proven](https://www.hazeliscoding.dev/blog/every-trap-is-proven)\n'

def oss_block():
    query = urllib.parse.quote(' '.join(['is:pr', 'author:hazeliscoding', *(f'repo:{repo}' for repo in OSS)]))
    result = api(f'search/issues?q={query}&per_page=100')
    # shortcut: reads one page of 100 PRs and refuses to undercount, page through once there are more
    if result['incomplete_results'] or result['total_count'] > len(result['items']):
        raise ValueError('Partial search results')
    lines, projects, merged_total, open_total = [], 0, 0, 0
    for repo, (emoji, name, blurb) in OSS.items():
        prs = [pr for pr in result['items'] if pr['repository_url'].lower().endswith('/repos/' + repo.lower())]
        merged = sum(1 for pr in prs if pr['pull_request'].get('merged_at'))
        waiting = sum(1 for pr in prs if pr['state'] == 'open')
        counts = []
        if merged:
            counts.append(f'{merged} merged')
        if waiting:
            counts.append(f'{waiting} in review')
        if not counts:
            continue
        projects += bool(merged)
        merged_total += merged
        open_total += waiting
        star_count = stars(api(f'repos/{repo}')['stargazers_count'])
        lines.append(f'- {emoji} **[{name}](https://github.com/{repo})** ({star_count} ★) · '
                     f'[{", ".join(counts)}](https://github.com/{repo}/pulls?q=is%3Apr+author%3Ahazeliscoding): {blurb}.')
    if not lines:
        return None
    summary = f'✿ **{plural(merged_total, "merged PR")}** across {plural(projects, "project")}'
    if open_total:
        summary += f', and {open_total} more in review'
    return summary + '.\n\n' + '\n'.join(lines) + '\n'

def replace(text, start, end, block):
    before, tail = text.split(start, 1)
    _, after = tail.split(end, 1)
    return before + start + '\n' + block + end + after

def main():
    current = README.read_text(encoding='utf-8')
    for start, end in ((START, END), (OSS_START, OSS_END)):
        if current.count(start) != 1 or current.count(end) != 1 or current.index(start) > current.index(end):
            raise ValueError(f'Expected exactly one correctly ordered {start} block')
    updated = current
    release = release_block()
    if release:
        updated = replace(updated, START, END, release)
    else:
        print('No GitHub release data available; release line untouched')
    try:
        oss = oss_block()
    except FETCH_ERRORS as exc:
        oss = None
        print(f'Warning: open source: {exc}')
    if oss:
        updated = replace(updated, OSS_START, OSS_END, oss)
    else:
        print('No open source data available; open source block untouched')
    if current != updated:
        README.write_text(updated, encoding='utf-8')
        print('Updated README')
    else:
        print('No README changes')

if __name__ == '__main__':
    main()
