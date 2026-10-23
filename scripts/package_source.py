"""Create a source-only GitHub upload ZIP, without local credentials or media."""
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.claude', '.codex', '.agents', '.aws', '.venv',
            'node_modules', '__pycache__', '.pytest_cache', '.vite', '.brainrot'}

def allowed(name):
    path = Path(name)
    parts = path.parts
    return bool(parts) and not path.is_absolute() and '..' not in parts and not (
        any(p in EXCLUDED for p in parts)
        or parts[0] in {'out', 'media'}
        or (path.name.startswith('.env') and path.name != '.env.example')
        or path.suffix.lower() in {'.pyc', '.log', '.mp4', '.webm', '.mp3', '.mov', '.zip'}
    )

def main():
    result = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        cwd=ROOT,
    ).decode('utf-8')
    paths = sorted({name for name in result.split('\0') if name and allowed(name)})
    # Compare values without exposing them in logs. Environment templates remain
    # shareable; real local values may never enter a distribution archive.
    secrets = []
    for envfile in ROOT.glob('.env*'):
        if envfile.name == '.env.example' or not envfile.is_file():
            continue
        for line in envfile.read_text(encoding='utf-8').splitlines():
            if '=' not in line or line.lstrip().startswith('#'):
                continue
            key, value = line.split('=', 1)
            value = value.strip().strip('\"\'')
            if any(word in key.upper() for word in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'DATABASE_URL')) and len(value) >= 16:
                secrets.append(value.encode())
    files = []
    for name in paths:
        path = ROOT / name
        if path.is_symlink():
            raise SystemExit('Refusing source symlink: ' + name)
        if not path.is_file():
            continue
        data = path.read_bytes()
        normalized = data.replace(b'\r\n', b'\n')
        if any(value in data for value in secrets) or b'-----BEGIN PRIVATE KEY-----\n' in normalized or b'-----BEGIN RSA PRIVATE KEY-----\n' in normalized:
            raise SystemExit('Private configuration detected in: ' + name)
        files.append((name, data))
    names = {name for name, _ in files}
    for required in ('LICENSE', 'LICENSE-MIT', 'LICENSE-APACHE', 'NOTICE', 'README.md', 'THIRD_PARTY_NOTICES.md', 'GITHUB_UPLOAD.md', '.gitignore'):
        if required not in names:
            raise SystemExit('Missing distribution file: ' + required)
    target = ROOT / 'out/releases/brainrot-github-source.zip'
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files:
            archive.writestr(name.replace('\\', '/'), data)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise SystemExit('Archive integrity check failed')
        assert all(allowed(name) for name in archive.namelist())
    temporary.replace(target)
    print(f'Created {target.relative_to(ROOT)} ({len(files)} source files).')
    print('Configured-secret scan and archive integrity check passed.')

if __name__ == '__main__':
    main()
