/* 37AC 训练报告交互脚本（src/cli/assets/report.js，v12 精简版）
   只保留：折线悬浮 -> 显示该轮一个小圆点 + 跟随光标的数值浮层
   （缩放与软刷新已按需求移除；页面用 meta refresh 定时刷新） */
(function () {
  function payloadOf(box) {
    var el = document.getElementById(box.getAttribute("data-src"));
    if (!el) { return null; }
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }
  function tipOf(box) {
    var id = box.getAttribute("data-tip");
    return id ? document.getElementById(id) : null;
  }
  function showAt(box, i, ev) {
    var ps = payloadOf(box);
    if (!ps || !ps[i]) { return; }
    var dots = box.querySelectorAll("circle.pt");
    for (var k = 0; k < dots.length; k++) {
      var on = (parseInt(dots[k].getAttribute("data-i"), 10) === i);
      dots[k].setAttribute("r", on ? "3.2" : "1.6");
      dots[k].setAttribute("opacity", on ? "1" : "0");
    }
    var tip = tipOf(box);
    if (!tip) { return; }
    tip.textContent = ps[i].t;
    var x = ev ? ev.clientX : null, y = ev ? ev.clientY : null;
    if (x === null || y === null) {
      var rc = box.getBoundingClientRect();
      x = rc.left + rc.width / 2; y = rc.top + rc.height / 2;
    }
    tip.style.display = "block";
    var tw = tip.offsetWidth || 140, th = tip.offsetHeight || 24;
    var left = x + 14;
    if (left + tw > window.innerWidth - 8) { left = x - tw - 14; }
    var top = y + 16;
    if (top + th > window.innerHeight - 8) { top = y - th - 12; }
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  }
  function hide(box) {
    var dots = box.querySelectorAll("circle.pt");
    for (var k = 0; k < dots.length; k++) {
      dots[k].setAttribute("r", "1.6");
      dots[k].setAttribute("opacity", "0");
    }
    var tip = tipOf(box);
    if (tip) { tip.style.display = "none"; }
  }
  function bindBox(box) {
    var hits = box.querySelectorAll(".hit");
    for (var k = 0; k < hits.length; k++) {
      (function (hit) {
        function fire(ev) {
          var idx = parseInt(hit.getAttribute("data-i"), 10);
          var ps = payloadOf(box);
          if (ps && ps[idx]) { showAt(box, idx, ev); }
        }
        hit.addEventListener("mousemove", fire);
        hit.addEventListener("mouseenter", fire);
      })(hits[k]);
    }
    box.addEventListener("mouseleave", function () { hide(box); });
  }
  function boot() {
    var boxes = document.querySelectorAll(".chartbox");
    for (var i = 0; i < boxes.length; i++) { bindBox(boxes[i]); }
    try {
      var st = document.getElementById("jsstat");
      if (st) { st.style.color = "#2FA36B"; st.textContent = "JS v12 已运行（悬浮交互）"; }
    } catch (e) {}
  }
  if (document.readyState !== "loading") { boot(); }
  else { document.addEventListener("DOMContentLoaded", boot); }
})();
