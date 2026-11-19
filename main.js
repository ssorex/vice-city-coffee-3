const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const root = document.documentElement;
const rm = matchMedia('(prefers-reduced-motion:reduce)').matches;
const fine = matchMedia('(pointer:fine)').matches;
const lite = () => root.classList.contains('lite');

/* ---------- режим «лайт»: слабое устройство или медленные кадры → эффекты упрощаются ---------- */
const fx = new URLSearchParams(location.search).get('fx'); // ?fx=full или ?fx=lite — ручное переключение
if (fx === 'lite' || (fx !== 'full' && (rm || (navigator.hardwareConcurrency || 8) <= 2 || (navigator.deviceMemory || 8) <= 2))) root.classList.add('lite');
else if (fx !== 'full') setTimeout(() => {
  let n = 0, last = 0, sum = 0;
  (function f(t) {
    if (last) { sum += t - last; n++; } last = t;
    if (n < 60) requestAnimationFrame(f); else if (sum / n > 30) root.classList.add('lite');
  })(performance.now());
}, 5000);

/* ---------- меню ---------- */
fetch('menu.json').then(r => r.json()).then(init).catch(() => {
  $('#ribbon').textContent = 'Меню не загрузилось. Откройте сайт через локальный сервер (см. README).';
});

function init(m) {
  const rib = $('#ribbon'), chips = $('.chips');
  const by = c => m.items.filter(i => i.category === c);
  const price = it => it.sizes.map(z => `<span><strong>${z.price}</strong>${z.v ? z.v + '\u00a0' + z.u : ''}</span>`).join('<br>');
  const card = (it, i) => `<li class="card" style="--r:${(((i * 37) % 7) - 3) * 0.9}deg"><div class="ph"><img src="${it.image}" width="520" height="416" alt="${it.name}" loading="lazy" decoding="async"></div><h3>${it.name}</h3><p>${price(it)}</p></li>`;
  const board = items => `<ul class="board">${items.map(it => `<li><span>${it.name}</span><span>${it.sizes.map(z => `<b>${z.v} <small>${z.u}</small> · ${z.price}</b>`).join('')}</span></li>`).join('')}</ul>`;

  function show(id) {
    const items = by(id);
    $$('button', chips).forEach(b => b.setAttribute('aria-pressed', b.dataset.id === id));
    rib.scrollLeft = 0;
    rib.innerHTML = id === 'classic' ? board(items) : `<ul class="rail">${items.map(card).join('')}</ul>`;
  }
  m.categories.forEach(c => {
    const b = document.createElement('button');
    b.type = 'button'; b.dataset.id = c.id; b.textContent = c.label;
    b.onclick = () => show(c.id); chips.append(b);
  });
  show(m.categories[0].id);

  /* перетаскивание с инерцией (на таче работает нативный скролл) */
  let down = false, sx = 0, sl = 0, v = 0, raf = 0;
  rib.addEventListener('pointerdown', e => { if (e.pointerType === 'touch') return; down = true; sx = e.clientX; sl = rib.scrollLeft; v = 0; cancelAnimationFrame(raf); });
  addEventListener('pointermove', e => { if (!down) return; const n = sl - (e.clientX - sx); v = n - rib.scrollLeft; rib.scrollLeft = n; }, { passive: true });
  addEventListener('pointerup', () => {
    if (!down) return; down = false;
    if (rm) return;
    (function f() { rib.scrollLeft += v; v *= 0.94; if (Math.abs(v) > 0.3) raf = requestAnimationFrame(f); })();
  });
  rib.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight') rib.scrollBy({ left: 300, behavior: 'smooth' });
    if (e.key === 'ArrowLeft') rib.scrollBy({ left: -300, behavior: 'smooth' });
  });

  /* «О нас» и галерея берут фото из меню (лёгкие миниатюры для ленты) */
  const find = n => m.items.find(i => i.name === n && i.image);
  $$('[data-pick]').forEach(f => { const it = find(f.dataset.pick); if (it) f.innerHTML = `<img src="${it.image}" width="520" height="416" alt="${it.name}" loading="lazy" decoding="async">`; });
  const pics = m.items.filter(i => i.thumb), pick = k => pics.filter((_, i) => i % 5 === k).slice(0, 12);
  [['#r1', pick(0)], ['#r2', pick(2)]].forEach(([s, a]) => {
    const html = a.map(it => `<img src="${it.thumb}" width="280" height="224" alt="${it.name}" loading="lazy" decoding="async">`).join('');
    $(s).innerHTML = html + html.replace(/alt="[^"]*"/g, 'alt="" aria-hidden="true"');
  });
}

/* ---------- появление: у каждого типа свой приём (clip / pop / draw) ---------- */
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: 0, rootMargin: '0px 0px -12% 0px' });
$$('[data-r]').forEach(el => rm ? el.classList.add('in') : io.observe(el));

/* ---------- цвет фона по секциям + пауза анимаций вне экрана ---------- */
const so = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) document.body.dataset.s = e.target.dataset.sec; }), { threshold: 0.45 });
$$('[data-sec]').forEach(s => so.observe(s));
const vo = new IntersectionObserver(es => es.forEach(e => e.target.classList.toggle('is-on', e.isIntersecting)), { rootMargin: '80px' });
$$('[data-v]').forEach(s => vo.observe(s));

/* ---------- параллакс героя (только пока он на экране) и лёгкий сдвиг фона от курсора ---------- */
if (!rm) {
  const sun = $('.sun'), pal = $('.palms'), sign = $('.sign'), bg = $('.bg');
  let y = 0, px = 0, py = 0, t1 = 0, t2 = 0;
  const upY = () => { t1 = 0; if (y < innerHeight * 1.2) { sun.style.transform = `translate3d(0,${y * 0.22}px,0)`; pal.style.transform = `translate3d(0,${y * 0.1}px,0)`; sign.style.transform = `translate3d(0,${y * -0.08}px,0)`; } };
  addEventListener('scroll', () => { if (lite() || t1) return; y = scrollY; t1 = requestAnimationFrame(upY); }, { passive: true });
  const upP = () => { t2 = 0; bg.style.transform = `translate3d(${px * -24}px,${py * -24}px,0)`; };
  addEventListener('pointermove', e => { if (lite() || t2) return; px = e.clientX / innerWidth - 0.5; py = e.clientY / innerHeight - 0.5; t2 = requestAnimationFrame(upP); }, { passive: true });
}

/* ---------- курсор-неон со шлейфом: DOM-точки, цикл работает только пока курсор движется ---------- */
if (fine && !rm && !lite()) {
  const box = $('#cur'), N = 9, d = [], P = [];
  for (let i = 0; i < N; i++) { const e = document.createElement('i'); e.style.transform = 'translate3d(-99px,-99px,0)'; box.append(e); d.push(e); P.push({ x: -99, y: -99 }); }
  document.body.classList.add('fine');
  let tx = -99, ty = -99, run = false;
  const step = () => {
    let moving = false, px = tx, py = ty;
    for (let i = N - 1; i >= 0; i--) {
      const p = P[i], k = i === N - 1 ? 0.6 : 0.34;
      const nx = p.x + (px - p.x) * k, ny = p.y + (py - p.y) * k;
      if (Math.abs(nx - p.x) + Math.abs(ny - p.y) > 0.15) moving = true;
      p.x = nx; p.y = ny; d[i].style.transform = `translate3d(${nx}px,${ny}px,0) scale(${0.4 + 0.6 * (i + 1) / N})`;
      px = nx; py = ny;
    }
    if (moving && !lite()) requestAnimationFrame(step); else run = false;
  };
  addEventListener('pointermove', e => { tx = e.clientX; ty = e.clientY; if (!run) { run = true; requestAnimationFrame(step); } }, { passive: true });
}
