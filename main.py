from pdf2muse.app import run


if __name__ == "__main__":
    # A reproducible check of the actual frozen GUI -> frozen engine bridge.
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == '--verify-portable':
        import json
        from pathlib import Path
        from pdf2muse.converter import convert_with_homr
        from pdf2muse.tools import find_homr_python
        destination = Path(sys.argv[3])
        destination.mkdir(parents=True, exist_ok=True)
        try:
            engine = find_homr_python()
            if not engine or engine.name.lower() != 'homr.exe':
                raise RuntimeError('Bundled engine not found')
            result = convert_with_homr(Path(sys.argv[2]), destination, engine)
            payload = dict(output=str(result.output), log=str(result.log_file), seconds=result.elapsed_seconds)
            status = 0
        except Exception as exc:
            payload, status = dict(error=str(exc)), 1
        (destination / 'portable-check.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        raise SystemExit(status)
    raise SystemExit(run())
