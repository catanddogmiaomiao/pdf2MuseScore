"""Experimental image coordinates; never uses Audiveris output as ground truth."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def runs(values):
    indices = np.flatnonzero(values)
    if not len(indices):
        return []
    return np.split(indices, np.where(np.diff(indices) > 1)[0] + 1)


def detect_page(image: Image.Image, page: int = 1) -> dict:
    ink = np.asarray(image.convert('L')) < 160
    height, width = ink.shape
    staves = []
    for threshold in (.45,.2):
        peaks = [int(np.median(r)) for r in runs(ink.sum(axis=1) > width * threshold)]
        for top in peaks:
            if any(s['lines'][0]-3 <= top <= s['lines'][-1]+3 for s in staves):
                continue
            for second in peaks:
                spacing = second-top
                if not 4 <= spacing <= height*.025:
                    continue
                lines = [top,second]
                for k in (2,3,4):
                    closest = min(peaks,key=lambda p:abs(p-(top+k*spacing)))
                    if abs(closest-(top+k*spacing)) > max(4,spacing*.25):
                        break
                    lines.append(closest)
                if len(lines) != 5:
                    continue
                gaps = np.diff(lines)
                if np.min(gaps) < 4 or np.max(np.abs(gaps-np.median(gaps))) > 2:
                    continue
                coverage = ink[lines].sum(axis=0) >= 3
                coverage = np.convolve(coverage.astype(int),np.ones(21,dtype=int),mode='same') >= 11
                spans = runs(coverage)
                if not spans:
                    continue
                span = max(spans,key=len)
                if len(span) < width*.2:
                    continue
                staves.append(dict(lines=lines,spacing=float(np.median(np.diff(lines))),left=int(span[0]),right=int(span[-1])))
                break
    staves.sort(key=lambda s:s['lines'][0])
    rows = []
    for staff in staves:
        top, bottom = staff['lines'][0], staff['lines'][-1]
        spacing = staff['spacing']
        left, right = staff['left'], staff['right']
        # All five lines must be crossed; stems extending past the staff are excluded.
        candidates = []
        for group in runs(ink[top:bottom + 1].mean(axis=0) >= .92):
            x = int(np.median(group))
            if x < left + 7 * spacing or x > right - spacing:
                continue
            extension = max(2, int(spacing * .7))
            above = ink[max(0, top-extension):top, group].any(axis=1).sum()
            below = ink[bottom+1:bottom+1+extension, group].any(axis=1).sum()
            if above >= extension or below >= extension:
                continue
            # A stem often crosses the entire staff too. Look for attached
            # noteheads/beams away from the five horizontal lines.
            radius = max(3, int(spacing * .8))
            neighborhood = ink[top:bottom+1,max(0,x-radius):x+radius+1].copy()
            for line in staff['lines']:
                offset = line-top
                neighborhood[max(0,offset-1):offset+2] = False
            center = x-max(0,x-radius)
            neighborhood[:,max(0,center-2):center+3] = False
            if neighborhood.sum() > spacing*spacing*.2:
                continue
            if not candidates or x - candidates[-1] > spacing * 3:
                candidates.append(x)
        boundaries = [left, *candidates, right]
        margin = int(spacing * 3)
        rows.append(dict(row=len(rows)+1, staff_lines=staff['lines'],
                         spacing=spacing, boundaries=boundaries,
                         box=[left, max(0,top-margin), right, min(height,bottom+margin)],
                         measures=[dict(column=j+1, box=[a,max(0,top-margin),b,min(height,bottom+margin)])
                                   for j,(a,b) in enumerate(zip(boundaries,boundaries[1:]))]))
    return dict(page=page, width=width, height=height, rows=rows,
                warnings=['当前按单谱表分行；多声部总谱尚未合并为系统。'] if rows else ['未检测到谱行；空白页或图像需要检查。'])


def annotate(image: Image.Image, result: dict) -> Image.Image:
    preview = image.convert('RGB').copy()
    draw = ImageDraw.Draw(preview)
    for row in result['rows']:
        for measure in row['measures']:
            draw.rectangle(measure['box'], outline='#9255BB', width=2)
            x,y,_,_ = measure['box']
            label = f"R{row['row']} M{measure['column']}"
            draw.rectangle((x,y,x+70,y+16),fill='#EEE3F6')
            draw.text((x+2,y+2),label,fill='#402451')
    return preview


def save_report(source: Path, pages: list[dict], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    report = directory / 'coordinates.json'
    report.write_text(json.dumps(dict(schema_version=1, source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        stage='coordinates-only', pages=pages), ensure_ascii=False, indent=2),encoding='utf-8')
    return report
