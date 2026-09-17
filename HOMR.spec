# Build this spec with the isolated HOMR environment, not the GUI Python.
from pathlib import Path
import hashlib
import json
import importlib.metadata
import homr
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

project = Path(SPECPATH)
package = Path(homr.__file__).parent
models = list(package.rglob('*.onnx'))
required = [p for p in models if not p.stem.endswith('_fp16')]
if len(required) != 3:
    raise RuntimeError('Initialize the three CPU HOMR models before packaging: python -m homr.main --init')
manifest = project / 'build' / 'engine-models.json'
manifest.parent.mkdir(exist_ok=True)
manifest.write_text(json.dumps({str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest() for p in required}, indent=2), encoding='utf-8')
datas = collect_data_files('homr') + collect_data_files('rapidocr') + collect_data_files('pypdfium2_raw') + collect_data_files('onnxruntime')
datas.append((str(manifest), '.'))
datas.append((str(project / 'packaging' / 'HOMR-LICENSE.txt'), 'licenses/HOMR'))
# Include package license metadata in the binary distribution.
for distribution in importlib.metadata.distributions():
    for file in distribution.files or []:
        if any(part.lower().startswith(('license', 'copying', 'notice')) for part in file.parts):
            path = Path(distribution.locate_file(file))
            if path.is_file():
                datas.append((str(path), str(Path('licenses') / distribution.metadata['Name'] / Path(file).parent)))
a = Analysis([str(project / 'pdf2muse' / 'homr_runner.py')], pathex=[str(project)],
    datas=datas, binaries=collect_dynamic_libs('onnxruntime') + collect_dynamic_libs('pypdfium2_raw'),
    hiddenimports=collect_submodules('homr') + collect_submodules('numpy._core') + ['onnxruntime.capi.onnxruntime_pybind11_state'],
    excludes=['torch', 'tensorflow', 'PyQt6', 'PyQt5', 'PySide6', 'tkinter', 'matplotlib', 'pytest', 'IPython'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='HOMR', console=True, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='HOMR', strip=False, upx=False)
