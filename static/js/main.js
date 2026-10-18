/* Util global: navbar, salin rekening, tukar kota, tanggal minimum */
(function () {
  'use strict';

  // Navbar: bayangan saat discroll
  var nav = document.querySelector('.nt-navbar');
  if (nav) {
    var onScroll = function () {
      nav.classList.toggle('shadow-lg', window.scrollY > 10);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Tombol salin rekening
  document.querySelectorAll('.copy-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var text = btn.getAttribute('data-copy') || '';
      var done = function () {
        var old = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check me-1"></i>OK';
        btn.classList.add('btn-success');
        btn.classList.remove('btn-outline-primary');
        setTimeout(function () {
          btn.innerHTML = old;
          btn.classList.remove('btn-success');
          btn.classList.add('btn-outline-primary');
        }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () {});
      } else {
        var ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); done(); } catch (e) {}
        document.body.removeChild(ta);
      }
    });
  });

  // Tukar kota asal/tujuan (beranda)
  var swapBtn = document.querySelector('[data-swap]');
  if (swapBtn) {
    swapBtn.addEventListener('click', function () {
      var o = document.getElementById('id_origin');
      var d = document.getElementById('id_destination');
      if (o && d) {
        var tmp = o.value;
        o.value = d.value;
        d.value = tmp;
      }
    });
  }

  // Semua input tanggal tidak boleh masa lalu
  document.querySelectorAll('input[type="date"]').forEach(function (input) {
    if (!input.min) input.min = new Date().toISOString().split('T')[0];
  });
})();
