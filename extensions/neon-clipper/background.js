const NOTION_FORM_URL = "https://wealthy-operation-579.notion.site/3230088c2a0880a682e1ec078b9f4fb6?pvs=105";

// Coincide con youtube.com/watch y music.youtube.com/watch
const isValidTab = (url) => !!url?.match(/https:\/\/(www\.|music\.)?youtube\.com\/watch/);

chrome.action.onClicked.addListener(async (tab) => {

  // — Pestaña inválida —
  if (!tab.id || !isValidTab(tab.url)) {
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        showToast("[⮚] ACCESO DENEGADO: Solo funciona en videos de YouTube.", false);

        function showToast(message, success) { renderToast(message, success); }
        function renderToast(message, success) {
          const el = document.createElement('div');
          el.textContent = message;
          applyToastStyles(el, success);
          mountToast(el);
        }
        function applyToastStyles(el, success) {
          const color = success ? '#90ee90' : '#ff6b6b';
          Object.assign(el.style, {
            position:   'fixed',
            bottom:     '30px',
            left:       '30px',
            background: 'repeating-linear-gradient(-45deg,#0c0c0c,#0c0c0c 8px,#242424 8px,#242424 16px)',
            color,
            border:          `1px solid ${color}`,
            padding:         '12px 18px',
            fontFamily:      '"Courier New", Courier, monospace',
            fontSize:        '12px',
            fontWeight:      'bold',
            letterSpacing:   '0.06em',
            textTransform:   'uppercase',
            zIndex:          '999999',
            maxWidth:        '300px',
            pointerEvents:   'none',
            opacity:         '0',
            transition:      'opacity 0.3s ease-in-out'
          });
        }
        function mountToast(el) {
          document.body.appendChild(el);
          requestAnimationFrame(() => (el.style.opacity = '1'));
          setTimeout(() => {
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 300);
          }, 2500);
        }
      }
    });
    return;
  }

  // — Copiar URL + obtener dimensiones de pantalla —
  const [{ result }] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: async () => {
      let ok = false;
      try {
        await navigator.clipboard.writeText(window.location.href);
        ok = true;
      } catch { /* se notificará vía toast */ }
      return { ok, sw: screen.width, sh: screen.height };
    }
  });

  // — Toast izquierdo —
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: (ok) => {
      const message = ok
        ? '[⮚] URL COPIADA [⮚] ABRIENDO NOTION...'
        : '[⮚] AVISO: Notion abierto. URL no copiada.';
      showToast(message, ok);

      function showToast(message, success) {
        const el = document.createElement('div');
        el.textContent = message;

        const color = success ? '#90ee90' : '#ff6b6b';
        Object.assign(el.style, {
          position:      'fixed',
          bottom:        '30px',
          left:          '30px',
          background:    'repeating-linear-gradient(-45deg,#1F1F1F,#1F1F1F 8px,#2C2C2C 8px,#2C2C2C 16px)',
          color,
          border:        `1px solid ${color}`,
          padding:       '12px 18px',
          fontFamily:    '"Courier New", Courier, monospace',
          fontSize:      '12px',
          fontWeight:    'bold',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          zIndex:        '999999',
          maxWidth:      '350px',
          pointerEvents: 'none',
          opacity:       '0',
          transition:    'opacity 0.3s ease-in-out'
        });

        document.body.appendChild(el);
        requestAnimationFrame(() => (el.style.opacity = '1'));
        setTimeout(() => {
          el.style.opacity = '0';
          setTimeout(() => el.remove(), 300);
        }, 2500);
      }
    },
    args: [result.ok]
  });

  // — Abrir ventana posicionada a la derecha —
  const W = 470, H = 735;
  const left = Math.max(0, result.sw - W - 20);
  const top  = Math.round((result.sh - H) / 2);

  const win = await chrome.windows.create({
    url:     NOTION_FORM_URL,
    type:    'popup',
    width:   W,
    height:  H,
    left,
    top,
    focused: true
  });

  // — Auto-cierre al enviar el formulario —
  const notionTabId = win.tabs[0].id;

  chrome.tabs.onUpdated.addListener(function monitor(tabId, info) {
    if (tabId !== notionTabId || info.status !== 'complete') return;
    chrome.tabs.onUpdated.removeListener(monitor);

    chrome.scripting.executeScript({
      target: { tabId: notionTabId },
      func: () => {
        // Detecta el texto de confirmación de Notion y cierra la ventana
        new MutationObserver((_, obs) => {
          const text = document.body?.innerText ?? '';
          if (text.includes('Tu respuesta se envió correctamente') || text.includes('response was submitted')) {
            obs.disconnect();
            setTimeout(() => window.close(), 800);
          }
        }).observe(document.body, { childList: true, subtree: true });
      }
    });
  });
});