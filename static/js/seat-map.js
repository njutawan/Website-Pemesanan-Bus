/* Denah kursi interaktif: batasi jumlah pilihan, hitung total, isi input CSV */
(function () {
  'use strict';

  var map = document.getElementById('seatMap');
  if (!map) return;

  var max = parseInt(map.getAttribute('data-max'), 10) || 1;
  var price = parseInt(map.getAttribute('data-price'), 10) || 0;
  var buttons = Array.prototype.slice.call(map.querySelectorAll('.seat-btn:not(.taken)'));
  var input = document.getElementById('seatsInput');
  var countEl = document.getElementById('seatCount');
  var labelsEl = document.getElementById('seatLabels');
  var totalEl = document.getElementById('seatTotal');
  var form = document.getElementById('seatForm');
  var continueBtn = document.getElementById('btnContinue');

  var toIdr = function (n) {
    return 'Rp ' + String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  };

  var selected = function () {
    return buttons.filter(function (b) { return b.classList.contains('selected'); });
  };

  var refresh = function () {
    var sel = selected();
    var labels = sel.map(function (b) { return b.getAttribute('data-label'); });
    if (countEl) countEl.textContent = String(sel.length);
    if (labelsEl) labelsEl.textContent = labels.length ? labels.join(', ') : '—';
    if (totalEl) totalEl.textContent = toIdr(sel.length * price);
    if (input) input.value = labels.join(',');
    if (continueBtn) continueBtn.disabled = sel.length === 0;
  };

  buttons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var isSelected = btn.classList.contains('selected');
      if (!isSelected && selected().length >= max) {
        // Batas penumpang tercapai — goyangkan kartu ringkasan
        if (form) {
          form.classList.remove('needs-shake');
          void form.offsetWidth;
          form.classList.add('needs-shake');
        }
        return;
      }
      btn.classList.toggle('selected');
      refresh();
    });
  });

  if (form) {
    form.addEventListener('submit', function (e) {
      if (selected().length === 0) {
        e.preventDefault();
      }
    });
  }
})();
