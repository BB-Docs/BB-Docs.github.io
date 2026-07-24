(function () {
  var root = document.documentElement;
  var btn = document.getElementById('theme-toggle');

  function store(theme) {
    try { localStorage.setItem('theme', theme); } catch (e) {}
  }
  function stored() {
    try { return localStorage.getItem('theme'); } catch (e) { return null; }
  }
  function apply(theme) {
    root.setAttribute('data-theme', theme);
    if (btn) btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
  }

  if (btn) {
    apply(root.getAttribute('data-theme') || 'light');
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      apply(next);
      store(next);          // an explicit choice wins over the OS from now on
    });
  }

  // Follow the OS only while the reader hasn't made an explicit choice.
  try {
    var mq = matchMedia('(prefers-color-scheme: dark)');
    var onChange = function (e) {
      if (!stored()) apply(e.matches ? 'dark' : 'light');
    };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
    else if (mq.addListener) mq.addListener(onChange);   // older Safari
  } catch (e) {}
})();
