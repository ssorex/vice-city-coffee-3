#!/usr/bin/env python3
"""python3 scripts/build_menu.py [папка_с_фото] [menu.csv]
Собирает menu.json из menu.csv (названия, объём, цены, файл картинки) и готовит фото:
у снимков напитков на белом фоне фон вырезается (прозрачный WebP), тёмные кадры еды остаются как есть.
Размеры: 520x416 для карточек и 280x224 для галереи."""
import sys, os, re, csv, json, hashlib, collections, unicodedata
import numpy as np, cv2
from scipy import ndimage as ndi
from PIL import Image, ImageOps
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'menu_images')
CSV = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'menu.csv')
OUT = os.path.join(ROOT, 'assets', 'menu'); os.makedirs(OUT, exist_ok=True)
W, H = 520, 416
nfc = lambda s: unicodedata.normalize('NFC', s)

def cutout(im):
    """Фон на этих снимках чисто белый (255): заливаем его от краёв кадра, всё остальное остаётся предметом."""
    a = np.asarray(im).astype(np.uint8)
    lab, _ = ndi.label(a.min(2) >= 254)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])); edge = edge[edge > 0]
    obj = ndi.binary_fill_holes(~np.isin(lab, edge))
    l2, n = ndi.label(obj)
    if n > 1:
        sz = ndi.sum(obj, l2, range(1, n + 1)); obj = np.isin(l2, [i + 1 for i, s in enumerate(sz) if s >= max(60, .0008 * obj.size)])
    core = ndi.binary_erosion(obj, iterations=1)
    _, (iy, ix) = ndi.distance_transform_edt(~core, return_indices=True)  # цвет кромки берём у ближайшего внутреннего пикселя: без белой каймы
    alpha = np.clip((cv2.GaussianBlur(obj.astype(np.float32), (0, 0), .8) - .3) / .5, 0, 1)
    return Image.fromarray(np.dstack([a[iy, ix], (alpha * 255).astype(np.uint8)]), 'RGBA')

def fit(path):
    im = Image.open(path).convert('RGB')
    if all(c > 240 for c in im.getpixel((4, 4))):
        cut = cutout(im); bb = cut.getchannel('A').point(lambda v: 255 if v > 10 else 0).getbbox()
        w, h = (bb[2] - bb[0]) * 1.14, (bb[3] - bb[1]) * 1.14
        cw = max(w, h * 1.25); ch = cw / 1.25; x, y = (bb[0] + bb[2]) / 2 - cw / 2, (bb[1] + bb[3]) / 2 - ch / 2
        canvas = Image.new('RGBA', (int(cw), int(ch)), (0, 0, 0, 0)); canvas.paste(cut, (int(-x), int(-y)))
        return canvas.resize((W, H), Image.LANCZOS), True
    return ImageOps.fit(im, (W, H), Image.LANCZOS), False

files = {nfc(f): os.path.join(SRC, f) for f in os.listdir(SRC)}
rows = list(csv.DictReader(open(CSV, encoding='utf-8-sig'), delimiter=';'))
digest = {}
def dg(p):
    if p not in digest: digest[p] = hashlib.md5(open(p, 'rb').read()).hexdigest()[:8]
    return digest[p]
items = collections.OrderedDict()
for r in rows:
    name = re.sub(r'\s+', ' ', r['Название']).strip()
    m = re.match(r'^\s*(\d+)\s*(мл|г)\s*$', r['Объём/вес'])
    price = r['Цена, ₽'].strip(); price = price + '\u00a0₽' if price else '— ₽'
    it = items.setdefault(name, {'name': name, 'sizes': [], 'srcs': [], 'unit': m.group(2) if m else 'мл'})
    it['sizes'].append({'v': int(m.group(1)) if m else 0, 'u': m.group(2) if m else '', 'price': price})
    fn = nfc(os.path.basename(r['Файл картинки'].replace('\\', '/'))).strip()
    if fn and fn in files: it['srcs'].append(files[fn])
    elif fn: print('нет файла:', fn)
generic = {h for h, c in collections.Counter(dg(p) for it in items.values() for p in it['srcs']).items() if c >= 10}
nat = lambda s: [int(t) if t.isdigit() else t.casefold() for t in re.split(r'(\d+)', s)]
out = []
for it in sorted(items.values(), key=lambda i: nat(i['name'])):
    src = it['srcs'][0] if it['srcs'] else None
    cat = 'classic' if (not src or dg(src) in generic) else ('food' if it['unit'] == 'г' else 'signature')
    img = th = None
    if cat != 'classic':
        h = dg(src); img, th = f'assets/menu/{h}.webp', f'assets/menu/t_{h}.webp'
        if not os.path.exists(os.path.join(ROOT, img)):
            big, alpha = fit(src)
            big.save(os.path.join(ROOT, img), 'WEBP', quality=80, alpha_quality=90, method=6)
            big.resize((280, 224), Image.LANCZOS).save(os.path.join(ROOT, th), 'WEBP', quality=74, alpha_quality=85, method=6)
    it['sizes'].sort(key=lambda s: s['v'])
    out.append({'id': 'i%03d' % (len(out) + 1), 'name': it['name'], 'category': cat, 'sizes': it['sizes'], 'image': img, 'thumb': th})
data = {'categories': [{'id': 'signature', 'label': 'Авторские'}, {'id': 'food', 'label': 'Еда'}, {'id': 'classic', 'label': 'Классика'}], 'items': out}
json.dump(data, open(os.path.join(ROOT, 'menu.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(collections.Counter(i['category'] for i in out), 'webp:', len(os.listdir(OUT)))
