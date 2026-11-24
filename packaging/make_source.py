"""Package the exact application tree and complete pinned HOMR source separately from binaries."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile
parser=argparse.ArgumentParser()
parser.add_argument('--homr-source',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','-c','safe.directory='+root.as_posix(),'-C',str(root),'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
args.output.parent.mkdir(parents=True,exist_ok=True)
manifest={}
with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as target:
    for name in sorted(set(filter(None,files))):
        file=root/name
        if not file.is_file():continue
        data=file.read_bytes()
        target.writestr('PDF2Muse-source/'+name,data)
        manifest[name]=hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(args.homr_source) as upstream:
        for item in upstream.infolist():
            if not item.is_dir():target.writestr('upstream/'+item.filename,upstream.read(item))
    target.writestr('PDF2Muse-source/SOURCE-FILES-SHA256.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(args.output) as target:
    error=target.testzip()
    if error:raise RuntimeError('Source archive CRC error: '+error)
print('Source archive:',args.output,'application files:',len(manifest))
