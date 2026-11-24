# Third-party notices — PDF2Muse 0.3.0

PDF2Muse application: GNU GPL version 3 only; see LICENSE.
Copyright (C) 2026 PDF2Muse contributors.
No trademark or score-copyright license is granted by these code licenses.

HOMR: unmodified engine, commit 5e51b434b3149286dae1448603527923b62ef9f2.
Code and model weights: upstream AGPLv3. The PDF2Muse bridge is a separate process.
https://github.com/liebharc/homr/tree/5e51b434b3149286dae1448603527923b62ef9f2
https://github.com/liebharc/homr/releases/tag/onnx_checkpoints
https://github.com/liebharc/homr/blob/main/LICENSE_FAQ.md

Upstream notes that model-training-data rights can differ from code/weight licensing.
DeepScoresV2: CC BY 4.0; OpenScore Lieder/StringQuartets: CC0;
PDMX no_license_conflict subset: CC BY 4.0 dataset; underlying score rights may differ.
GrandStaff: no license stated at the original download source; MIT in the linked Hugging Face copy.
These are upstream disclosures, not a warranty of commercial model-rights clearance.
Dataset attributions and upstream source descriptions:
https://zenodo.org/records/4012193
https://github.com/OpenScore/Lieder
https://github.com/OpenScore/StringQuartets
https://zenodo.org/records/15571083
https://sites.google.com/view/multiscore-project/datasets
https://huggingface.co/datasets/PRAIG/grandstaff

GUI runtime: PyQt6 (GPLv3), PyQt6-sip (its bundled notices), Qt6 (its bundled licenses).
Cryptography: Apache-2.0 OR BSD-3-Clause; included notices also cover its binary dependencies.
Python retains the PSF license; PyInstaller retains its license and bootloader exception.
Engine dependencies include ONNX Runtime, NumPy, OpenCV, PDFium/pypdfium2 and their notices.
Authoritative dependency notices are shipped in _internal/licenses and engine/_internal/licenses.
MuseScore Studio is not bundled; PDF2Muse is not affiliated with or endorsed by MuseScore.

Corresponding source is offered next to the installer without an extra access fee:
https://pub-e428980b60994e0cae95ecf224953755.r2.dev/PDF2Muse-0.3.0-corresponding-source.zip
Versioned application repository:
https://github.com/catanddogmiaomiao/pdf2MuseScore/tree/release/windows-installer-legal
The source archive includes application/build/installer sources and complete pinned HOMR upstream source.
Dependency source versions and upstream source download links are in SOURCE-DEPENDENCIES.json.
