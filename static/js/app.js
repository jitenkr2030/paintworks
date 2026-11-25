// PaintWorks platform – minimal front-end helper
(function () {
  // Auto-close alerts after 4s
  setTimeout(function () {
    document.querySelectorAll('.alert-dismissible').forEach(function (a) {
      var btn = a.querySelector('.btn-close');
      if (btn) btn.click();
    });
  }, 4000);

  // Helper: format a number as INR
  window.formatINR = function (n) {
    if (n === null || n === undefined) return '₹0';
    return '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 });
  };

  // Auto-disable submit on forms with data-disable-once, and add loading spinner
  document.addEventListener('submit', function (e) {
    if (e.target.matches('form[data-disable-once], form[data-loading]')) {
      var btn = e.target.querySelector('button[type=submit]');
      if (btn) {
        btn.classList.add('btn-loading');
        btn.disabled = true;
        var original = btn.innerHTML;
        btn.setAttribute('data-original-html', original);
        // Don't replace innerHTML — keep icon + label, just append spinner via CSS pseudo
      }
    }
  });

  // Confirm dialog for elements with data-confirm
  document.addEventListener('click', function (e) {
    var el = e.target.closest('[data-confirm]');
    if (el) {
      if (!confirm(el.getAttribute('data-confirm'))) {
        e.preventDefault();
      }
    }
  });

  // Auto-focus first input on forms
  document.querySelectorAll('form').forEach(function (f) {
    if (!document.activeElement || document.activeElement === document.body) {
      var firstInput = f.querySelector('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea');
      if (firstInput && !firstInput.value) {
        // Don't autofocus to avoid scroll jumps; only on small forms
        if (f.querySelectorAll('input, select, textarea').length < 8) {
          firstInput.focus();
        }
      }
    }
  });

  // Toast helper
  window.showToast = function (message, type) {
    type = type || 'success';
    var container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    var toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-' + type + ' border-0 show';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = '<div class="d-flex"><div class="toast-body">' +
                      message + '</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
    container.appendChild(toast);
    setTimeout(function () {
      toast.classList.remove('show');
      setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 300);
    }, 4000);
  };
})();
