/* Corporation v22 performance layer */
(() => {
  "use strict";

  const lowPower = (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) ||
    (navigator.deviceMemory && navigator.deviceMemory <= 4);

  const style = document.createElement("style");
  style.textContent = `
    img { content-visibility:auto; }
    .card,.stats-card,.property-card,.corp-stock-row,article,section { contain:layout paint style; }
    @media (prefers-reduced-motion: reduce) {
      *,*::before,*::after { animation-duration:.001ms!important; animation-iteration-count:1!important; transition-duration:.001ms!important; scroll-behavior:auto!important; }
    }
    ${lowPower ? `
      *,*::before,*::after { animation-duration:.001ms!important; animation-iteration-count:1!important; transition-duration:.08s!important; }
      .tabs { backdrop-filter:none!important; -webkit-backdrop-filter:none!important; }
    ` : ""}
  `;
  document.head.appendChild(style);

  function tuneImages(root=document){
    root.querySelectorAll?.("img").forEach(img => {
      if (!img.hasAttribute("loading")) img.loading = "lazy";
      img.decoding = "async";
      img.fetchPriority = "low";
    });
  }
  tuneImages();

  const observer = new MutationObserver(records => {
    for (const rec of records) {
      for (const node of rec.addedNodes) {
        if (node.nodeType === 1) tuneImages(node);
      }
    }
  });
  observer.observe(document.documentElement, {childList:true, subtree:true});

  // Stop hidden Telegram WebViews from wasting CPU on animation frames.
  const nativeRAF = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = cb => {
    if (document.hidden) return setTimeout(() => cb(performance.now()), 250);
    return nativeRAF(cb);
  };
})();
