// product-page-cloner runtime: interactive script of the rebuilt page (runs in the section, after <template id="ppc-tpl">).
// Attaches the content to a Shadow DOM -> theme CSS cannot leak in, the rebuilt page's CSS cannot leak out.
// ADD TO CART / Buy N / BUY IT NOW handlers here are only a FALLBACK: the ppc-cart-drawer section intercepts
// those buttons in the capture phase on the shadow root.
(function () {
  var host = document.getElementById('ppc-root');
  if (!host || host.shadowRoot) return;
  var root = host.attachShadow({ mode: 'open' });
  var tpl = document.getElementById('ppc-tpl');
  root.appendChild(tpl.content.cloneNode(true));
  var variant = host.getAttribute('data-variant');
  var $ = function (s) { return root.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(root.querySelectorAll(s)); };

  // Text-style emoji (picture frame, heart, check, sun, plane ...) without U+FE0F render on many phones as a box
  // that looks like a CJK glyph. Append FE0F to every visible occurrence. (Real CJK scan: acceptance checks.)
  (function () {
    var TE = /([\u{1F5BC}❤✔☀✈☎✂⚠♥☺☃✏✉✖])(?!️)/gu;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), n;
    while ((n = w.nextNode())) {
      if (/^(STYLE|SCRIPT)$/.test(n.parentNode.nodeName)) continue;
      if (TE.test(n.nodeValue)) { TE.lastIndex = 0; n.nodeValue = n.nodeValue.replace(TE, '$1️'); }
      TE.lastIndex = 0;
    }
  })();
  // Phones: tighten variant buttons (less letter-spacing/padding) so ~5 styles fit on 2 lines at 360-414px.
  var compact = document.createElement('style');
  compact.textContent = '@media (max-width:768px){.labelStyle{gap:6px!important}.labelStyle .labelItem label{padding:7px 6px!important;letter-spacing:0!important;font-size:11.5px!important}}';
  root.appendChild(compact);

  // Delivery-date blocks in the style of Shopify "dynamic dates" apps: data-text contains [start_date]/[end_date],
  // data-min-days/max-days = days from today. The rebuild is static HTML, so recompute for the viewer's date.
  (function () {
    var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var dateIn = function (k) {
      var d = new Date(); d.setDate(d.getDate() + k); var n = d.getDate();
      var s = (n % 10 === 1 && n !== 11) ? 'st' : (n % 10 === 2 && n !== 12) ? 'nd' : (n % 10 === 3 && n !== 13) ? 'rd' : 'th';
      return ' ' + MONTHS[d.getMonth()] + ' ' + n + s;
    };
    $$('[data-dynamic-date="true"]').forEach(function (el) {
      var t = el.getAttribute('data-text') || ''; if (t.indexOf('[start_date]') < 0) return;
      el.innerHTML = t.replace('[start_date]', dateIn(+el.getAttribute('data-min-days') || 0))
                      .replace('[end_date]', dateIn(+el.getAttribute('data-max-days') || 0));
    });
  })();

  // gallery: scroll-snap track + counter + thumbnails
  var track = $('.ppc-track'), idx = $('[data-ppc="idx"]'), th = $$('.ppc-thumbs img');
  if (track) {
    track.addEventListener('scroll', function () {
      var i = Math.round(track.scrollLeft / track.clientWidth);
      if (idx) idx.textContent = i + 1;
      th.forEach(function (t, k) { t.classList.toggle('on', k === i); });
    }, { passive: true });
    th.forEach(function (t) {
      t.addEventListener('click', function () {
        track.scrollTo({ left: track.clientWidth * +t.getAttribute('data-i'), behavior: 'smooth' });
      });
    });
  }

  // quantity box
  var qty = $('.product_qty_num');
  if (qty) { qty.value = qty.value || 1; qty.removeAttribute('disabled'); qty.removeAttribute('readonly'); }
  var getQ = function () { var n = parseInt(qty && qty.value, 10); return n > 0 ? n : 1; };
  var sub = $('.product_qty .subtract'), add = $('.product_qty .add');
  if (sub) sub.addEventListener('click', function (e) { e.preventDefault(); if (qty) qty.value = Math.max(1, getQ() - 1); });
  if (add) add.addEventListener('click', function (e) { e.preventDefault(); if (qty) qty.value = getQ() + 1; });

  // fallback add-to-cart (only used if the cart drawer section is missing)
  function addToCart(n, next) {
    host.style.opacity = '.6';
    fetch('/cart/add.js', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ items: [{ id: +variant, quantity: n }] })
    }).then(function (r) {
      if (!r.ok) throw new Error('add');
      window.location.href = next;
    }).catch(function () {
      host.style.opacity = '';
      alert('Sorry, we could not add this item. Please try again.');
    });
  }
  var main = $('.product_single_add_button');
  if (main) main.addEventListener('click', function (e) { e.preventDefault(); addToCart(getQ(), '/cart'); });
  var now = $('[data-ppc="buynow"]');
  if (now) now.addEventListener('click', function (e) { e.preventDefault(); addToCart(getQ(), '/checkout'); });
  // "Buy More Save More" buttons: quantity is read from the "Buy N" text
  $$('.couponItem').forEach(function (it) {
    var m = (it.textContent || '').match(/Buy\s+(\d+)/i), b = it.querySelector('button');
    if (b && m) b.addEventListener('click', function (e) { e.preventDefault(); addToCart(+m[1], '/cart'); });
  });

  // VARIANTS: the Shopify variant list is printed by the section into <script id="ppc-variants">.
  // Clicking a .labelItem picks the variant matching every option group, updates data-variant on #ppc-root
  // (the cart drawer reads it), price / compare-at / % off, scrolls the gallery to the variant image and
  // updates ?variant= in the URL. Single-variant products: nothing happens.
  var vs = [];
  try { vs = JSON.parse((document.getElementById('ppc-variants') || {}).textContent || '[]'); } catch (e) {}
  var groups = $$('.variant_select');
  // Shopify is the source of truth: if a group has exactly 1 button and Shopify also has exactly 1 value,
  // show Shopify's text (renaming e.g. a size on Shopify then needs no snippet edit).
  groups.forEach(function (g, k) {
    var vals = []; vs.forEach(function (v) { if (v.options[k] != null && vals.indexOf(v.options[k]) < 0) vals.push(v.options[k]); });
    var its = g.querySelectorAll('.labelItem');
    if (its.length === 1 && vals.length === 1) {
      var inp = its[0].querySelector('input'), lb = its[0].querySelector('label');
      if (inp) inp.value = vals[0]; if (lb) lb.textContent = vals[0];
    }
  });
  function money(c) { return (c / 100).toFixed(2); }
  function applyVariant(v, scroll) {
    if (!v) return;
    variant = String(v.id);
    host.setAttribute('data-variant', variant);
    var sp = $('.product_price_price .symbol-price__price'), cp = $('.product_price_cross .symbol-price__price'),
        pc = $('.discount-label__percent');
    if (sp) sp.textContent = money(v.price);
    if (cp && v.compare_at_price) cp.textContent = money(v.compare_at_price);
    if (pc && v.compare_at_price > v.price) pc.textContent = ' ' + Math.round(100 - v.price * 100 / v.compare_at_price) + '% ';
    if (scroll && track && v.featured_image && v.featured_image.src) {
      var key = (v.featured_image.src.match(/files\/([^/?]+?)(?:\.[a-z]+)?(?:\?|$)/i) || [])[1];
      var imgs = $$('.ppc-track img');
      for (var i = 0; i < imgs.length; i++) {
        if (key && imgs[i].src.indexOf(key) > -1) { track.scrollTo({ left: track.clientWidth * i, behavior: 'smooth' }); break; }
      }
    }
    // Shopify-source pages: a label like "Style - <value>" follows the selected variant
    // (html_fixes adds data-ppc-label="<option index>" and data-label-prefix="Style - ").
    $$('[data-ppc-label]').forEach(function (el) {
      var k = +el.getAttribute('data-ppc-label'); if (v.options[k] != null) el.textContent = (el.getAttribute('data-label-prefix') || '') + v.options[k];
    });
    try { history.replaceState(null, '', location.pathname + '?variant=' + v.id); } catch (e) {}
    // real Shop Pay button (light DOM, <slot>): buy the selected variant
    Array.prototype.forEach.call(host.querySelectorAll('form input[name="id"]'), function (x) { x.value = v.id; });
    host.dispatchEvent(new CustomEvent('ppc:variant', { detail: v }));
  }
  function selected() {
    return groups.map(function (g) { var a = g.querySelector('.labelItem.active input'); return a ? a.value.trim() : null; });
  }
  function findVariant(c) {
    var match = function (c) { return vs.filter(function (v) { return v.options.every(function (o, k) { return c[k] == null || o === c[k]; }); })[0]; };
    // Fallback: if an option value was renamed on Shopify but the copied buttons were not, match the first group only
    // so the style buttons keep working.
    return match(c) || match([c[0]]);
  }
  if (vs.length > 1 && groups.length) {
    groups.forEach(function (g) {
      var items = Array.prototype.slice.call(g.querySelectorAll('.labelItem'));
      items.forEach(function (it) {
        it.addEventListener('click', function (e) {
          e.preventDefault();
          items.forEach(function (x) { x.classList.toggle('active', x === it); });
          applyVariant(findVariant(selected()), true);
        });
      });
    });
    var q = (location.search.match(/variant=(\d+)/) || [])[1];
    var v0 = vs.filter(function (v) { return String(v.id) === q; })[0] ||
             vs.filter(function (v) { return String(v.id) === host.getAttribute('data-variant'); })[0];
    if (v0) {
      groups.forEach(function (g, gi) {
        Array.prototype.forEach.call(g.querySelectorAll('.labelItem'), function (x) {
          var inp = x.querySelector('input'); x.classList.toggle('active', !!inp && inp.value.trim() === v0.options[gi]);
        });
      });
      applyVariant(v0, true);
    }
  }

  // THE REFERENCE STORE'S OWN STICKY ADD-TO-CART BAR. html_fixes KEEPS their <sticky-atc>, tagged data-ppc="sticky";
  // its button becomes data-ppc="sticky-atc" (the cart drawer intercepts it in capture phase and adds 1 of the
  // selected variant, like the reference). Here: show it once the main buy button has scrolled out of view
  // (Shopify themes use the data-after-scroll attribute), rebuild its <select> from the REAL Shopify variants,
  // and keep its image + price in sync with the selected variant.
  var bar = $('[data-ppc="sticky"]');
  if (bar) {
    var stB = document.createElement('style');
    stB.textContent = '[data-ppc="sticky"]{z-index:2147480000!important}';
    root.appendChild(stB);
    var mainBtn = $('.product_single_add_button');
    var checkBar = function () {
      var r = mainBtn && mainBtn.getBoundingClientRect();
      var show = !!r && r.bottom < 0;
      bar.setAttribute('data-after-scroll', show ? 'false' : 'true');
    };
    // Some themes scroll inside a wrapper element on desktop, not the window -> listen on document, capture phase.
    document.addEventListener('scroll', checkBar, { passive: true, capture: true });
    window.addEventListener('resize', checkBar); checkBar();
    var escB = function (x) { return String(x).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
    var selB = bar.querySelector('select');
    if (selB && vs.length) {
      selB.innerHTML = vs.map(function (v) { return '<option value="' + v.id + '">' + escB(v.options.join(' / ')) + '</option>'; }).join('');
      selB.value = host.getAttribute('data-variant');
      selB.addEventListener('change', function () {
        var v = vs.filter(function (x) { return String(x.id) === selB.value; })[0]; if (!v) return;
        groups.forEach(function (g, gi) {
          Array.prototype.forEach.call(g.querySelectorAll('.labelItem'), function (x) {
            var inp = x.querySelector('input'); x.classList.toggle('active', !!inp && inp.value.trim() === v.options[gi]);
          });
        });
        applyVariant(v, false);
      });
    }
    var imgB = bar.querySelector('.sticky-atc__image img');
    var $B = function (c) { return '$' + (c / 100).toFixed(2); };
    host.addEventListener('ppc:variant', function (e) {
      var v = e.detail; if (selB) selB.value = String(v.id);
      if (imgB && v.featured_image && v.featured_image.src) {
        var u = v.featured_image.src; if (u.indexOf('//') === 0) u = 'https:' + u;
        imgB.src = u + (u.indexOf('?') > -1 ? '&' : '?') + 'width=200';
      }
      Array.prototype.forEach.call(bar.querySelectorAll('.price__regular .price-item, .price-item--sale'), function (x) { x.textContent = $B(v.price); });
      var cmp = bar.querySelector('.price__compare-price s');
      if (cmp && v.compare_at_price) cmp.textContent = $B(v.compare_at_price);
    });
  }

  // MIX & MATCH: #ppc-root has data-mix="1" + data-tiers='[[qty,%,"badge"],...]'.
  // Replaces their quantity box + "Buy More Save More" block with a tier list: each tier has N style pickers
  // (buy 3 different styles in one click). Their own style buttons are KEPT (customers need them to browse styles).
  // A variant priced > 2x the cheapest = BUNDLE (e.g. "5 pcs"): hidden from the style buttons, sold as its own tier.
  // The cart drawer calls host.__ppcMix() to get [[variant, qty], ...] on ADD TO CART / BUY IT NOW.
  if (host.getAttribute('data-mix') === '1' && vs.length > 1) {
    var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
    var minPrice = Math.min.apply(null, vs.map(function (v) { return v.price; }));
    var singles = vs.filter(function (v) { return v.price <= minPrice * 2; });
    var bundle = vs.filter(function (v) { return v.price > minPrice * 2; })[0];
    if (bundle) $$('.labelItem').forEach(function (x) { var i = x.querySelector('input'); if (i && i.value.trim() === bundle.options[0]) x.style.display = 'none'; });
    if (bundle && host.getAttribute('data-variant') === String(bundle.id)) {
      var l0 = $$('.variant_select')[0] && $$('.variant_select')[0].querySelector('.labelItem'); if (l0) l0.click();
    }
    var TT = JSON.parse(host.getAttribute('data-tiers') || '[[1,0,""],[2,5,""],[3,10,""],[4,20,""]]');
    var defTier = +(host.getAttribute('data-default-tier') || 0);
    var img = function (v, w) {
      var s = (v.featured_image && v.featured_image.src) || ''; if (!s) return '';
      if (s.indexOf('//') === 0) s = 'https:' + s;
      return s + (s.indexOf('?') > -1 ? '&' : '?') + 'width=' + w;
    };
    var label = function (v) { return v.options[0]; };
    var m$ = function (c) { return '$' + (c / 100).toFixed(2); };
    var st = document.createElement('style');
    st.textContent = '.product-qty-module,.bulkcoupon{display:none!important}.ppc-mx-w[hidden]{display:none!important}' +
      '.ppc-mx-h{font-size:15px;font-weight:700;margin:0 0 10px;color:#2f2f2f}' +
      '.ppc-mx{display:flex;flex-direction:column;gap:10px;margin:0 0 16px}' +
      '.ppc-t{border:2px solid #e4e4e4;border-radius:8px;padding:12px 14px;cursor:pointer;position:relative;transition:border-color .15s,background .15s;text-align:left}' +
      '.ppc-t.on{border-color:var(--main-btn-bg);background:rgba(146,165,66,.08)}' +
      '.ppc-th{display:flex;align-items:center;gap:10px}' +
      '.ppc-rd{width:18px;height:18px;border-radius:50%;border:2px solid #bbb;flex:0 0 auto;position:relative}' +
      '.ppc-t.on .ppc-rd{border-color:var(--main-btn-bg)}.ppc-t.on .ppc-rd::after{content:"";position:absolute;inset:3px;border-radius:50%;background:var(--main-btn-bg)}' +
      '.ppc-tn{flex:1;font-weight:700;font-size:15px;line-height:1.3}.ppc-tn small{display:block;font-weight:400;color:#777;font-size:12.5px;margin-top:2px}' +
      '.ppc-tp{text-align:right;font-weight:700;color:var(--price-color);font-size:16px;line-height:1.3}.ppc-tp s{display:block;color:#999;font-weight:400;font-size:13px}' +
      '.ppc-bd{position:absolute;top:-10px;right:12px;background:var(--price-color);color:#fff;font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;letter-spacing:.3px;line-height:1.4}' +
      '.ppc-pk{display:none;margin-top:12px;border-top:1px dashed #cfd6b0;padding-top:10px;gap:8px;flex-direction:column}.ppc-t.on .ppc-pk{display:flex}' +
      '.ppc-p{display:flex;align-items:center;gap:8px}.ppc-p span{font-size:13px;color:#666;width:22px}' +
      '.ppc-p img{width:38px;height:38px;border-radius:4px;object-fit:cover;border:1px solid #ddd}' +
      '.ppc-p select{flex:1;min-width:0;height:38px;border:1px solid #ccc;border-radius:4px;padding:0 8px;font-size:14px;background:#fff;color:#2f2f2f}';
    root.appendChild(st);
    var opts = singles.map(function (v) { return '<option value="' + v.id + '">' + esc(label(v)) + '</option>'; }).join('');
    var box = document.createElement('div');
    box.innerHTML = '<p class="ppc-mx-h">Buy More Save More! — mix &amp; match any styles</p><div class="ppc-mx">' + TT.map(function (t, i) {
      var n = t[0], full = singles[0].price * n, after = full - n * Math.floor(singles[0].price * t[1] / 100), pk = '';
      for (var k = 0; k < n; k++) {
        var v = singles[k % singles.length];
        pk += '<div class="ppc-p"><span>#' + (k + 1) + '</span><img src="' + img(v, 100) + '" alt=""><select>' +
              opts.replace('value="' + v.id + '"', 'value="' + v.id + '" selected') + '</select></div>';
      }
      return '<div class="ppc-t' + (i === defTier ? ' on' : '') + '" data-n="' + n + '">' + (t[2] ? '<span class="ppc-bd">' + esc(t[2]) + '</span>' : '') +
        '<div class="ppc-th"><span class="ppc-rd"></span><div class="ppc-tn">' + (t[1] ? 'Buy ' + n + ' – Save ' + t[1] + '%' : 'Buy ' + n) +
        '<small>' + (n > 1 ? 'Mix &amp; match any styles' : 'Standard price') + '</small></div>' +
        '<div class="ppc-tp">' + m$(after) + (t[1] ? '<s>' + m$(full) + '</s>' : '') + '</div></div><div class="ppc-pk">' + pk + '</div></div>';
    }).join('') + '</div>';
    var buyBtn = $('.product_single_add_button');
    if (buyBtn) buyBtn.parentNode.insertBefore(box, buyBtn);
    box.className = 'ppc-mx-w';
    var isBundle = function () { return !!bundle && host.getAttribute('data-variant') === String(bundle.id); };
    // Clicking a style button puts that style into slot #1 of the active tier; whichever slot already held it
    // swaps with slot #1's old style (no accidental duplicates).
    var followButton = function (v) {
      if (!v) return;
      box.hidden = !!bundle && v.id === bundle.id;
      if (box.hidden) return;
      var ss = Array.prototype.slice.call(box.querySelectorAll('.ppc-t.on select')), s1 = ss[0], id = String(v.id);
      if (!s1 || s1.value === id) return;
      var old1 = s1.value, dup = ss.filter(function (s) { return s.value === id; })[0];
      var set = function (s, val) { s.value = val; var x = vs.filter(function (y) { return String(y.id) === val; })[0]; if (x) s.previousElementSibling.src = img(x, 100); };
      set(s1, id); if (dup) set(dup, old1);
    };
    host.addEventListener('ppc:variant', function (e) { followButton(e.detail); });
    followButton(vs.filter(function (x) { return String(x.id) === host.getAttribute('data-variant'); })[0]);
    var scrollTo = function (v) {
      var key = ((v.featured_image && v.featured_image.src || '').match(/files\/([^/?]+?)(?:\.[a-z]+)?(?:\?|$)/i) || [])[1];
      $$('.ppc-track img').some(function (im, i) {
        if (key && im.src.indexOf(key) > -1) { track.scrollTo({ left: track.clientWidth * i, behavior: 'smooth' }); return true; }
      });
    };
    box.addEventListener('click', function (e) {
      var t = e.target.closest('.ppc-t'); if (!t || e.target.closest('select')) return;
      $$('.ppc-t').forEach(function (x) { x.classList.toggle('on', x === t); });
    });
    box.addEventListener('change', function (e) {
      var v = vs.filter(function (x) { return String(x.id) === e.target.value; })[0]; if (!v) return;
      e.target.previousElementSibling.src = img(v, 100); if (track) scrollTo(v);
    });
    // [[variant, qty], ...] of the active tier (identical styles merged)
    host.__ppcMix = function () {
      if (isBundle()) return [[bundle.id, 1]];
      var count = {}, order = [];
      $$('.ppc-t.on select').forEach(function (s) { if (!count[s.value]) { count[s.value] = 0; order.push(s.value); } count[s.value]++; });
      return order.map(function (id) { return [+id, count[id]]; });
    };
  }
})();
