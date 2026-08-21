/* Modern slideout menus - click/tap based */
(function() {
    'use strict';

    const overlay = document.createElement('div');
    overlay.id = 'menu-overlay';
    overlay.setAttribute('aria-hidden', 'true');
    document.body.appendChild(overlay);

    const chapterBtn = document.getElementById('slideout_chapter');
    const generalBtn = document.getElementById('slideout_general');
    const chapterPanel = document.getElementById('slideout_inner_chapter');
    const generalPanel = document.getElementById('slideout_inner_general');

    const menuMap = {
        'slideout_inner_chapter': 'slideout_chapter',
        'slideout_inner_general': 'slideout_general'
    };

    let activeMenu = null;

    function isInteractive(el) {
        if (!el) return false;
        const tag = el.tagName && el.tagName.toLowerCase();
        if (tag === 'a' || tag === 'button' || tag === 'input') return true;
        if (el.closest('a') || el.closest('button') || el.closest('input')) return true;
        return false;
    }

    function addCloseButton(panel) {
        if (panel.querySelector('.menu-close')) return;
        const btn = document.createElement('button');
        btn.className = 'menu-close';
        btn.innerHTML = '✕';
        btn.setAttribute('aria-label', 'Cerrar menú');
        panel.insertBefore(btn, panel.firstChild);
    }

    function openMenu(panel, btnId) {
        if (activeMenu && activeMenu !== panel) {
            closeMenu(activeMenu);
        }
        document.body.classList.add('menu-open');
        panel.classList.add('open');
        const btn = document.getElementById(btnId);
        if (btn) btn.classList.add('active');
        overlay.classList.add('visible');
        overlay.setAttribute('aria-hidden', 'false');
        activeMenu = panel;
    }

    function closeMenu(panel) {
        if (!panel) return;
        document.body.classList.remove('menu-open');
        panel.classList.remove('open');
        const btnId = menuMap[panel.id];
        if (btnId) {
            const btn = document.getElementById(btnId);
            if (btn) btn.classList.remove('active');
        }
        overlay.classList.remove('visible');
        overlay.setAttribute('aria-hidden', 'true');
        activeMenu = null;
    }

    if (chapterBtn && chapterPanel) {
        addCloseButton(chapterPanel);
        chapterBtn.addEventListener('click', (e) => {
            if (isInteractive(e.target)) return;
            if (chapterPanel.classList.contains('open')) {
                closeMenu(chapterPanel);
            } else {
                openMenu(chapterPanel, 'slideout_chapter');
            }
        });
        chapterPanel.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        chapterPanel.querySelector('.menu-close').addEventListener('click', () => {
            closeMenu(chapterPanel);
        });
    }

    if (generalBtn && generalPanel) {
        addCloseButton(generalPanel);
        generalBtn.addEventListener('click', (e) => {
            if (isInteractive(e.target)) return;
            if (generalPanel.classList.contains('open')) {
                closeMenu(generalPanel);
            } else {
                openMenu(generalPanel, 'slideout_general');
            }
        });
        generalPanel.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        generalPanel.querySelector('.menu-close').addEventListener('click', () => {
            closeMenu(generalPanel);
        });
    }

    overlay.addEventListener('click', () => {
        if (activeMenu) closeMenu(activeMenu);
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && activeMenu) {
            closeMenu(activeMenu);
        }
    });
})();