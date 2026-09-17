"""Fail reliably on a full disk and verify every member before publishing ZIP."""
import sys
import zipfile
from pathlib import Path

source, destination = map(Path, sys.argv[1:])
temporary = destination.with_suffix('.zip.partial')
try:
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in sorted(source.rglob('*')):
            if file.is_file() and '__pycache__' not in file.parts:
                archive.write(file, file.relative_to(source.parent))
    with zipfile.ZipFile(temporary) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError('Archive verification failed: ' + bad)
    temporary.replace(destination)
except BaseException:
    temporary.unlink(missing_ok=True)
    raise
print('Verified portable ZIP:', destination)
