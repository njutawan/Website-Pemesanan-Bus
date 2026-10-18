/* Aktifkan stylesheet non-kritis setelah halaman diparse.
 * Menggantikan atribut inline onload (dilarang CSP script-src-attr 'none'). */
(function () {
  'use strict';
  var links = document.querySelectorAll('link[data-async-css]');
  for (var i = 0; i < links.length; i++) {
    links[i].media = 'all';
  }
})();
