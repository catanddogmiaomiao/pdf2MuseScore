"""Executed only by the separate HOMR Python, never imported by the GUI."""
import json
import os
import sys
from pathlib import Path
import hashlib
import multiprocessing

import pypdfium2 as pdfium


def check_bundle():
    import homr
    import homr.main as engine
    root = Path(homr.__file__).parent
    manifest = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'engine-models.json'
    if not manifest.is_file():
        raise FileNotFoundError('Bundled model manifest is missing. Extract the complete portable package again.')
    for relative, digest in json.loads(manifest.read_text(encoding='utf-8')).items():
        path = root / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Bundled model missing or damaged: ' + relative)
    # Offline distribution must never silently download replacement models.
    engine.download_weights = lambda *args, **kwargs: None
    return engine


def main():
    engine = check_bundle() if getattr(sys, 'frozen', False) else None
    if '--self-test' in sys.argv:
        import onnxruntime as ort
        from homr.segmentation.config import segnet_path_onnx
        from homr.transformer.configs import default_config
        for model in (segnet_path_onnx, default_config.filepaths.encoder_path, default_config.filepaths.decoder_path):
            session = ort.InferenceSession(model, providers=['CPUExecutionProvider'])
            print('Model loaded:', Path(model).name, flush=True)
            del session
        print('HOMR engine self-test passed', flush=True)
        return
    # Omit only completely white pages; never infer missing notes or fix pitches.
    source = pdfium.PdfDocument('score.pdf')
    retained, skipped = [], []
    try:
        for index in range(len(source)):
            page = source[index]
            bitmap = page.render(scale=1)
            image = bitmap.to_pil().convert('L')
            white = image.getextrema() == (255, 255)
            bitmap.close()
            page.close()
            (skipped if white else retained).append(index)
        if not retained:
            raise ValueError('PDF contains only blank pages')
        if skipped:
            result = pdfium.PdfDocument.new()
            try:
                result.import_pages(source, retained)
                result.save('nonblank.pdf')
            finally:
                result.close()
    finally:
        source.close()
    if skipped:
        os.replace('score.pdf', 'original.pdf')
        os.replace('nonblank.pdf', 'score.pdf')
        print('Blank pages omitted:', [i + 1 for i in skipped], flush=True)
    with open('pages.json', 'w', encoding='utf-8') as file:
        json.dump({'retained': [i + 1 for i in retained], 'skipped': [i + 1 for i in skipped]}, file)
    from homr.main import main as recognize
    sys.argv = ['homr', '--no-title', '--gpu', 'no', '--', 'score.pdf']
    recognize()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
