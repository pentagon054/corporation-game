/* Corporation v22.1 performance + responsive statistics layer */
(() => {
  "use strict";

  const lowPower = (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) ||
    (navigator.deviceMemory && navigator.deviceMemory <= 4);

  const style = document.createElement("style");
  style.id = "corporation-v221-responsive-style";
  style.textContent = `
    *,*::before,*::after{box-sizing:border-box}
    html,body{max-width:100%;overflow-x:hidden}
    img { content-visibility:auto; }
    .card,.stats-card,.property-card,.corp-stock-row,article,section { contain:layout paint style; }

    /* Statistics must never make Telegram WebView wider than the screen. */
    #content,.stats-page,.stats-page>*{min-width:0;max-width:100%;}
    .stats-page{width:100%!important;overflow:visible!important;}
    .stats-page .stats-card,
    .stats-page .chart-card,
    .stats-page .v221-responsive-grid,
    .stats-page .v221-responsive-grid>*{
      min-width:0!important;
      max-width:100%!important;
    }
    .stats-page .stats-card,
    .stats-page .chart-card{
      width:100%!important;
    }
    .stats-page .stats-card b,
    .stats-page .stats-card strong,
    .stats-page .v221-responsive-grid b,
    .stats-page .v221-responsive-grid strong{
      max-width:100%;
      overflow-wrap:anywhere;
      word-break:normal;
    }

    /* Capital breakdown: one column on phones, two only when it actually fits. */
    .stats-page .v221-responsive-grid{
      width:100%!important;
      display:grid!important;
      grid-template-columns:minmax(0,1fr)!important;
      gap:12px!important;
      overflow:visible!important;
    }
    @media (min-width:620px){
      .stats-page .v221-responsive-grid{
        grid-template-columns:repeat(2,minmax(0,1fr))!important;
      }
    }

    /* Daily-profit chart: the card stays inside the Mini App, only the bars scroll. */
    .chart-card{overflow:hidden!important;}
    .v221-profit-scroll{
      display:block;
      width:100%;
      max-width:100%;
      overflow-x:auto!important;
      overflow-y:hidden!important;
      overscroll-behavior-x:contain;
      -webkit-overflow-scrolling:touch;
      touch-action:pan-x pan-y;
      padding:2px 0 7px;
      scrollbar-width:thin;
    }
    .v221-profit-scroll .profit-chart{
      width:max-content!important;
      min-width:100%!important;
      max-width:none!important;
      display:flex!important;
      align-items:flex-end!important;
      justify-content:flex-start!important;
      gap:10px!important;
      overflow:visible!important;
      padding-left:2px;
      padding-right:2px;
    }
    .v221-profit-scroll .chart-column{
      flex:0 0 58px!important;
      width:58px!important;
      min-width:58px!important;
      max-width:58px!important;
    }
    .v221-profit-scroll .chart-value{
      width:100%;
      max-width:100%;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
      text-align:center;
      font-size:9px!important;
    }
    .v221-profit-scroll .chart-date{white-space:nowrap;text-align:center;}

    @media (max-width:420px){
      .stats-page{display:grid!important;grid-template-columns:minmax(0,1fr)!important;gap:12px!important;}
      .stats-page .stats-card,.stats-page .chart-card{grid-column:1/-1!important;}
      .v221-profit-scroll .chart-column{flex-basis:56px!important;width:56px!important;min-width:56px!important;max-width:56px!important;}
    }

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

  function wrapProfitCharts(root=document){
    root.querySelectorAll?.(".profit-chart").forEach(chart => {
      if (chart.parentElement?.classList.contains("v221-profit-scroll")) return;
      const scroller = document.createElement("div");
      scroller.className = "v221-profit-scroll";
      chart.parentNode.insertBefore(scroller, chart);
      scroller.appendChild(chart);
      // On a long season open at the newest days, while keeping the entire history swipeable.
      requestAnimationFrame(() => { scroller.scrollLeft = scroller.scrollWidth; });
    });
  }

  function findCapitalGrid(root=document){
    const page = root.matches?.(".stats-page") ? root : root.querySelector?.(".stats-page");
    if (!page) return;
    const labels = ["Свободные деньги","Бизнес","Акции","Облигации","Недвижимость"];
    const leaves = [...page.querySelectorAll("span,p,div")].filter(el => labels.some(t => el.textContent?.trim() === t));
    if (leaves.length < 2) return;

    const cards = leaves.map(el => el.closest("article,.card,.stats-card") || el.parentElement).filter(Boolean);
    let candidate = null;
    for (const card of cards) {
      let p = card.parentElement;
      while (p && p !== page) {
        const count = cards.filter(c => p.contains(c)).length;
        if (count >= 2) { candidate = p; break; }
        p = p.parentElement;
      }
      if (candidate) break;
    }
    if (candidate && candidate !== page) candidate.classList.add("v221-responsive-grid");
  }

  function tuneStatistics(root=document){
    wrapProfitCharts(root);
    findCapitalGrid(root);
    root.querySelectorAll?.(".stats-page,.stats-card,.chart-card").forEach(el => {
      el.style.maxWidth = "100%";
      el.style.minWidth = "0";
    });
  }

  tuneImages();
  tuneStatistics();

  let queued = false;
  const observer = new MutationObserver(records => {
    for (const rec of records) {
      for (const node of rec.addedNodes) {
        if (node.nodeType === 1) tuneImages(node);
      }
    }
    if (!queued) {
      queued = true;
      requestAnimationFrame(() => { queued = false; tuneStatistics(document); });
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
