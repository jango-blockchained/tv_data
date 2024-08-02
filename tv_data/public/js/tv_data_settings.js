function timeline_w() {
  frappe.call({
    method:
      "tv_data.tv_data.doctype.tv_data_settings.tv_data_settings._get_cycle_timeline_html",
    callback: function (r) {
      if (r.message) {
        document.getElementById("cycle-timeline-container").innerHTML =
          r.message;
      }
    },
  });
}

function timeline_h() {
  frappe.call({
    method:
      "tv_data.tv_data.doctype.tv_data_settings.tv_data_settings._get_horizontal_timeline_html",
    callback: function (r) {
      if (r.message) {
        $("#horizontal-timeline-container").html(r.message);
      }
    },
  });
}

timeline_h();
timeline_w();

// Animate timeline items on load

function updateCurrentTime() {
  var now = new Date();
  var timeString = now.toLocaleTimeString(frappe.boot.lang, {
    hour12: false,
  });
  $("#current-time-display").text(timeString);
}

updateCurrentTime();
setInterval(updateCurrentTime, 1000);

// Animate timeline items on load
setTimeout(function () {
  $(".timeline-item").each(function (index) {
    var $item = $(this);
    setTimeout(function () {
      $item.find(".timeline-content").css({
        opacity: 1,
        transform: "translateY(0)",
      });
    }, index * 100);
  });
}, 500);
