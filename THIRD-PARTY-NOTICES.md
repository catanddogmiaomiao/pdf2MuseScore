# Included software

This distribution includes HOMR, pinned to source commit
`5e51b434b3149286dae1448603527923b62ef9f2`:
https://github.com/liebharc/homr/tree/5e51b434b3149286dae1448603527923b62ef9f2

HOMR is licensed under GNU Affero General Public License version 3.
The bundled HOMR code is unmodified; PDF2Muse provides a separate process bridge.
Corresponding application and engine Python source and build scripts are included
in `source/`. Upstream complete source is available from the commit above.
HOMR inference model files are distributed from the upstream ONNX checkpoint release:
https://github.com/liebharc/homr/releases/tag/onnx_checkpoints

Third-party package license texts are collected under `engine/_internal/licenses/`.
The GUI includes PyQt6 and Qt; their license texts are distributed in `_internal/`.
MuseScore is not included.
