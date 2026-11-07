#!/usr/bin/env python3
"""Exercise the distributed ZIP on the host OS with an existing local Node."""

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
ZIP = ROOT / 'WD-Obsidian-Vault-OS-0.3.1-alpha.zip'
MANIFEST = ROOT / 'MANIFEST.json'


def run(vault: Path, *args: str) -> dict:
    result = subprocess.run(
        ['node', 'Setup/setup.cjs', *args], cwd=vault,
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert hashlib.sha256(ZIP.read_bytes()).hexdigest() == manifest['zip_sha256']
    with ZipFile(ZIP) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == manifest['entries']
        for name, expected in manifest['entry_sha256'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
        with TemporaryDirectory(prefix='WD Alpha Smoke ') as temporary:
            target = Path(temporary)
            archive.extractall(target)
            vault = target / 'WD Vault OS'
            assert (target / 'START HERE.html').read_bytes() == (vault / 'OPEN START.html').read_bytes()
            assert (vault / '.obsidian' / 'community-plugins.json').read_text().strip() == '[]'
            assert (vault / '.obsidian' / 'themes' / 'Prism' / 'LICENSE').is_file()
            assert (vault / 'HOME.md').is_file() and (vault / 'RECENTS.md').is_file()
            assert (vault / 'System' / 'Recent notes.base').is_file()

            initial = run(vault, 'status', '--rehearsal')
            assert initial['state'] is None and not initial['other_saved_progress']
            progress = initial['progress_location']
            assert Path(progress).is_absolute()
            started = run(vault, 'start', '--allow-progress', progress, '--rehearsal')
            assert started['permission_valid']
            run(vault, 'answer', '1', 'Plan a small paper-star display', '--rehearsal')
            run(vault, 'answer', '2', 'Fold one sample star', '--rehearsal')
            paused = run(vault, 'pause', '--rehearsal')
            assert paused['state']['status'] == 'paused'
            resumed = run(vault, 'status', '--rehearsal')
            assert resumed['next_question'] == 3
            for number, answer in (
                (3, 'a small step'),
                (4, 'One star stands without support'),
                (5, 'Open the sample sketch'),
                (6, 'projects,writing'),
            ):
                run(vault, 'answer', str(number), answer, '--rehearsal')
            preview = run(vault, 'preview', '--rehearsal')
            assert preview['status'] == 'awaiting-confirmation'
            assert len(preview['plans']) == 4
            run(vault, 'confirm', 'Yes, save these starter notes.', '--rehearsal')
            created = run(vault, 'create', '--rehearsal')
            assert created['status'] == 'saved' and len(created['checks']) == 4
            for output in created['checks']:
                assert (vault / output['path']).is_file(), output['path']
            starting = (vault / 'Demonstration/Onboarding rehearsal/MY STARTING POINT.md').read_text()
            workflows = (vault / 'Demonstration/Onboarding rehearsal/MY WORKFLOWS.md').read_text()
            assert 'FICTIONAL REHEARSAL' in starting
            assert 'My chosen workflows' in starting
            assert 'Keep a project moving' in workflows and 'Turn a seed into an article' in workflows
            assert not (vault / 'MY STARTING POINT.md').exists()
    print(json.dumps({'result': 'passed', 'platform': sys.platform, 'zip_sha256': manifest['zip_sha256'], 'created_notes': 4}))


if __name__ == '__main__':
    main()
