"""Executed only by the separate HOMR Python, never imported by the GUI."""
import json
import os
import sys

import pypdfium2 as pdfium


def main():
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
    sys.argv = ['homr', '--no-title', '--', 'score.pdf']
    recognize()


if __name__ == '__main__':
    main()
