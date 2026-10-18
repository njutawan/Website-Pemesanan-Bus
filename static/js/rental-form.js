/* Estimasi harga sewa live: hari × harga (+ sopir) */
(function () {
  'use strict';

  // Ambil data dari atribut pada tag <script> ini sendiri
  var script = document.querySelector('script[src*="rental-form.js"]');
  if (!script) return;
  var price = parseInt(script.getAttribute('data-price'), 10) || 0;
  var driverFee = parseInt(script.getAttribute('data-driver'), 10) || 0;

  var pickup = document.getElementById('id_pickup_date');
  var ret = document.getElementById('id_return_date');
  var driver = document.getElementById('id_with_driver');
  var daysEl = document.getElementById('estDays');
  var totalEl = document.getElementById('estTotal');
  if (!pickup || !ret || !daysEl || !totalEl) return;

  var toIdr = function (n) {
    return 'Rp ' + String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  };

  var update = function () {
    if (!pickup.value || !ret.value) {
      daysEl.textContent = '—';
      totalEl.textContent = toIdr(price);
      return;
    }
    var p = new Date(pickup.value);
    var r = new Date(ret.value);
    var diff = Math.floor((r - p) / 86400000) + 1; // inklusif
    if (diff < 1) {
      daysEl.innerHTML = '<span class="text-danger">tanggal tidak valid</span>';
      totalEl.textContent = '—';
      return;
    }
    daysEl.textContent = diff + ' hari';
    var total = diff * price + (driver && driver.checked ? diff * driverFee : 0);
    totalEl.textContent = toIdr(total);
  };

  [pickup, ret, driver].forEach(function (el) {
    if (el) el.addEventListener('change', update);
  });

  // Default: besok → lusa
  var tomorrow = new Date(Date.now() + 86400000);
  var dayAfter = new Date(Date.now() + 2 * 86400000);
  var iso = function (d) { return d.toISOString().split('T')[0]; };
  if (!pickup.value) pickup.value = iso(tomorrow);
  if (!ret.value) ret.value = iso(dayAfter);
  update();
})();
