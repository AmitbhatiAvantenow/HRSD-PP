/* =========================================================================
   AvanteNow HR Portal — Recruitment Careers landing page interactions
   ========================================================================= */
(function () {
  "use strict";

  function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  /* ---- destination for each card is set here once it is known -------- */
  var CARD_DESTINATIONS = {
    "open-recruitment": "/hrsd/recruitment/requirements",
    "open-dashboard": null,
    "open-kanban": "/hrsd/tasks",
  };

  onReady(function () {
    var root = document.querySelector(".rcp-shell");
    if (!root) return;

    root.querySelectorAll(".rcp-card[data-action]").forEach(function (card) {
      card.addEventListener("click", function (ev) {
        var action = card.getAttribute("data-action");
        var url = CARD_DESTINATIONS[action];
        if (url) {
          window.location.href = url;
        } else {
          ev.preventDefault();
        }
      });
    });

    var brand = root.querySelector(".rcp-brand");
    if (brand) {
      brand.addEventListener("click", function (ev) {
        ev.preventDefault();
        window.location.href = "/hrsd/dashboard";
      });
    }
  });
})();
