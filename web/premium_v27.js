/* Corporation v27: keep rating jump controls attached to the viewport, not to scrollable content. */
(() => {
  "use strict";
  let portal = null;

  function currentPage27(){
    try { return page; } catch (_) { return null; }
  }
  function removePortal27(){
    if (portal?.isConnected) portal.remove();
    portal = null;
  }
  function syncPortal27(){
    const p = currentPage27();
    const ratingView = document.querySelector("#content .rating-page");
    if (p !== "rating" || !ratingView) { removePortal27(); return; }
    const candidate = ratingView.querySelector(".rank-jump25");
    if (candidate) {
      candidate.classList.add("rank-jump27");
      candidate.setAttribute("aria-label", "Навигация по рейтингу");
      document.body.appendChild(candidate);
      portal = candidate;
    }
  }

  const content = document.querySelector("#content");
  if (content) {
    new MutationObserver(() => requestAnimationFrame(syncPortal27))
      .observe(content,{childList:true,subtree:true});
  }
  document.querySelectorAll("[data-page]").forEach(btn => {
    btn.addEventListener("click",() => requestAnimationFrame(syncPortal27));
  });
  window.addEventListener("pageshow",syncPortal27);
  document.addEventListener("visibilitychange",() => { if(!document.hidden) syncPortal27(); });
  requestAnimationFrame(syncPortal27);
})();
