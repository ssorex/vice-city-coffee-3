#!/usr/bin/env python3
"""Достаёт фирменный логотип со стакана (белая надпись с розовым контуром) и рисует две готовые
неоновые картинки: assets/logo-dim.webp (погашенная вывеска) и assets/logo-lit.webp (включённая, свечение уже внутри).
Так в браузере не нужны тяжёлые CSS-фильтры: анимируется только opacity.
python3 scripts/build_logo.py "путь/к/Пальмовый бриз (500 мл).jpg" """
import sys, os, unicodedata, numpy as np, cv2
from scipy import ndimage as ndi
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
src = sys.argv[1]
if not os.path.exists(src):  # имена файлов с macOS бывают в разной Unicode-нормализации
    d = os.path.dirname(src); nm = unicodedata.normalize('NFC', os.path.basename(src))
    src = next(os.path.join(d, f) for f in os.listdir(d) if unicodedata.normalize('NFC', f) == nm)
S, PAD = 4, 130
im = Image.open(src).convert('RGB').crop((440, 372, 790, 560))
a = np.asarray(im).astype(np.float32)
R, G, B = a[..., 0], a[..., 1], a[..., 2]
# плавные (не бинарные) маски на исходном разрешении: розовый контур и белая заливка
pink = np.clip(((R - G) - 28) / 40, 0, 1) * (R > 150)
white = np.clip((np.minimum(np.minimum(R, G), B) - 228) / 16, 0, 1)
up = lambda x: np.clip(cv2.resize(np.maximum(x, 0), None, fx=S, fy=S, interpolation=cv2.INTER_CUBIC), 0, 1)
m_soft, w_soft = up(np.maximum(pink, white)), up(white)
m0 = ndi.binary_fill_holes(m_soft > .5)
lab, n = ndi.label(m0); sizes = ndi.sum(m0, lab, range(1, n + 1))
m0 = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 600])
w0 = (w_soft > .5) & m0
def soft(x, s=2.6):
    v = cv2.GaussianBlur(x.astype(np.float32), (0, 0), s)
    return np.clip((v - .38) / .24, 0, 1)
M, W = soft(m0), soft(w0, 2.2)
ys, xs = np.where(M > .5); M = M[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; W = W[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
M, W = [np.pad(x, PAD) for x in (M, W)]
h, w = M.shape
def blur(x, s): return cv2.GaussianBlur(x, (0, 0), s)
col = lambda hexc: np.array([int(hexc[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
def compose(core_rgb, glow, glow_rgb):
    ca = M[..., None]; ga = np.clip(glow, 0, 1)[..., None]
    a_t = ca + ga * (1 - ca)
    rgb = (core_rgb * ca + glow_rgb * ga * (1 - ca)) / np.maximum(a_t, 1e-4)
    return np.dstack([np.clip(rgb, 0, 255), a_t * 255]).astype(np.uint8)
pinkc, hot, whitec = col('#ff3fa4'), col('#ff8cc8'), col('#fff3fa')
core = pinkc * (1 - W[..., None]) + whitec * W[..., None]
core = core * .8 + (hot * (1 - W[..., None]) + whitec * W[..., None]) * .2
glow = .75 * blur(M, 7) + .55 * blur(M, 20) + .4 * blur(M, 46)
lit = compose(core, glow, col('#ff2e93'))
dimcore = col('#5b2a52') * (1 - W[..., None]) + col('#9a8195') * W[..., None]
dim = compose(dimcore, .06 * blur(M, 10), col('#ff2e93'))
dim[..., 3] = (dim[..., 3] * .8).astype(np.uint8)
for name, arr in (('logo-lit', lit), ('logo-dim', dim)):
    Image.fromarray(arr, 'RGBA').save(os.path.join(ROOT, 'assets', name + '.webp'), 'WEBP', quality=82, alpha_quality=90, method=6)
print('logo', w, 'x', h)
