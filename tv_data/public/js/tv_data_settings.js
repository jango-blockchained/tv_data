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

function setCurrentTime() {
  var now = new Date();
  var timeString = now.toLocaleTimeString(frappe.boot.lang, {
    hour12: false,
  });
  $("#current-time-display").text(timeString);
}

setCurrentTime();
timeline_h();
timeline_w();
