/* Hitung mundur batas pembayaran: data-deadline ISO 8601 ber-offset zona
   (mis. +07:00), agar Date menguraikannya sebagai instant yang sama di
   zona waktu browser mana pun — bukan waktu lokal browser. */
(function () {
  'use strict';

  var els = document.querySelectorAll('.countdown[data-deadline]');
  if (!els.length) return;

  var fmt = function (ms) {
    if (ms < 0) ms = 0;
    var s = Math.floor(ms / 1000);
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = s % 60;
    var pad = function (n) { return String(n).padStart(2, '0'); };
    return pad(h) + 'j ' + pad(m) + 'm ' + pad(sec) + 's';
  };

  var tick = function () {
    var now = Date.now();
    var allExpired = true;
    els.forEach(function (el) {
      var deadline = new Date(el.getAttribute('data-deadline')).getTime();
      var remaining = deadline - now;
      if (remaining > 0) {
        allExpired = false;
        el.textContent = fmt(remaining);
        el.classList.add('text-danger', 'fw-bold');
      } else {
        el.textContent = '00j 00m 00s';
      }
    });
    if (allExpired) {
      // Batas lewat: muat ulang agar status EXPIRED tampil
      setTimeout(function () { window.location.reload(); }, 1500);
    }
  };

  tick();
  setInterval(tick, 1000);
})();
