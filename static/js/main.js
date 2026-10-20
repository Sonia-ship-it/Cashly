// Cashly interactive scripts
window.toggleNotifMenu = function() {
  const dropdown = document.getElementById('notifDropdown');
  if (dropdown) {
    const isShowing = dropdown.style.display === 'block';
    dropdown.style.display = isShowing ? 'none' : 'block';
  }
};

window.toggleCardDetails = function(targetId, btn) {
  const drawer = document.getElementById(targetId);
  if (!drawer) return;
  const isOpen = drawer.classList.contains('open');
  if (isOpen) {
    drawer.classList.remove('open');
    if (btn) {
      btn.innerHTML = 'View Details ▾';
      btn.setAttribute('aria-expanded', 'false');
    }
  } else {
    drawer.classList.add('open');
    if (btn) {
      btn.innerHTML = 'Hide Details ▴';
      btn.setAttribute('aria-expanded', 'true');
    }
  }
};

window.toggleBudgetDetails = window.toggleCardDetails;

document.addEventListener('DOMContentLoaded', () => {
  // Close notification dropdown when clicking outside
  document.addEventListener('click', (e) => {
    const bellBtn = document.getElementById('notifBellBtn');
    const dropdown = document.getElementById('notifDropdown');
    if (dropdown && bellBtn && !bellBtn.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });

  // Mobile sidebar toggle
  const toggleBtn = document.getElementById('mobileToggle');
  const sidebar = document.getElementById('sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });
  }

  // Quick Transaction Modal
  const openModalBtn = document.getElementById('openQuickTxModal');
  const modalBackdrop = document.getElementById('quickTxModal');
  const closeModalBtn = document.getElementById('closeQuickTxModal');

  if (openModalBtn && modalBackdrop) {
    openModalBtn.addEventListener('click', (e) => {
      e.preventDefault();
      modalBackdrop.classList.add('show');
    });
  }

  if (closeModalBtn && modalBackdrop) {
    closeModalBtn.addEventListener('click', () => {
      modalBackdrop.classList.remove('show');
    });
  }

  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', (e) => {
      if (e.target === modalBackdrop) {
        modalBackdrop.classList.remove('show');
      }
    });
  }

  // Dismiss notification helper with live badge decrement (keeps item visible as read)
  document.querySelectorAll('.btn-dismiss-notif').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const notifId = btn.getAttribute('data-id');
      try {
        const res = await fetch(`/notifications/${notifId}/read/`, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (res.ok) {
          const item = document.getElementById(`notif-item-${notifId}`);
          if (item) {
            item.style.opacity = '0.85';
            item.style.background = 'var(--bg-card)';
            item.style.borderLeft = 'none';
            btn.outerHTML = '<span style="font-size: 0.7rem; color: var(--text-muted); padding: 2px 4px;">✓ Read</span>';
            const dot = item.querySelector('span[style*="background: #ef4444"]');
            if (dot) dot.remove();
          }
          
          // Decrement badge count
          const badge = document.getElementById('notifBadge');
          if (badge) {
            let count = parseInt(badge.textContent) - 1;
            if (count <= 0) {
              badge.remove();
            } else {
              badge.textContent = count;
            }
          }
        }
      } catch (err) {
        console.error('Failed to dismiss notification:', err);
      }
    });
  });

  // Delete notification helper
  document.querySelectorAll('.btn-delete-notif').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const notifId = btn.getAttribute('data-id');
      try {
        const res = await fetch(`/notifications/${notifId}/delete/`, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (res.ok) {
          const item = document.getElementById(`notif-item-${notifId}`);
          if (item) {
            // Check if it was unread before removing
            if (item.querySelector('.unread-dot')) {
              const badge = document.getElementById('notifBadge');
              if (badge) {
                let count = parseInt(badge.textContent) - 1;
                if (count <= 0) badge.remove();
                else badge.textContent = count;
              }
            }
            item.style.transition = 'all 0.25s ease';
            item.style.opacity = '0';
            item.style.transform = 'translateX(20px)';
            setTimeout(() => {
              item.remove();
              const container = document.getElementById('notifListContainer');
              if (container && container.querySelectorAll('[id^="notif-item-"]').length === 0) {
                container.innerHTML = '<div style="padding: 32px 20px; text-align: center; color: var(--text-muted); font-size: 0.88rem;">No notifications yet 🎉</div>';
              }
            }, 250);
          }
        }
      } catch (err) {
        console.error('Failed to delete notification:', err);
      }
    });
  });

  // Animate progress bars based on data-width attribute
  document.querySelectorAll('.progress-bar-fill[data-width]').forEach(bar => {
    const rawVal = parseFloat(bar.getAttribute('data-width') || '0');
    const clamped = Math.min(100, Math.max(0, isNaN(rawVal) ? 0 : rawVal));
    bar.style.width = clamped + '%';
  });

  // Request browser Web Push notification permission if supported
  if ('Notification' in window && Notification.permission === 'default') {
    // Non-intrusively ask after a moment
    setTimeout(() => {
      Notification.requestPermission();
    }, 4000);
  }
});
