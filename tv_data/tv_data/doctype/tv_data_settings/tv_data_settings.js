frappe.ui.form.on("TV Data Settings", {
  refresh(frm) {
    frm.trigger("repo_url");
    frm.trigger("fork_name");
    frm.trigger("fork_url");

    // Define button configurations
    const buttons = [
      {
        label: "GitHub Fork",
        icon: "fa fa-code-fork",
        action: () => window.open(frm.doc.fork_url),
      },
      {
        label: "GitHub Repo",
        icon: "fa fa-github",
        action: () => window.open(frm.doc.repo_url),
      },
      {
        label: "Generate Local Files",
        icon: "fa fa-file",
        action: generateLocalFiles,
      },
      {
        label: "Update Repo",
        icon: "fa fa-arrow-circle-o-up	",
        action: updateRepository,
      },
      {
        label: "Pull Request",
        icon: "fa fa-arrow-circle-o-right	",
        action: sendPullRequest,
      },
      { label: "Merge", icon: "fa fa-random", action: mergeUpdates },
    ];

    // Add buttons
    buttons.forEach((btn) =>
      addIconButton(frm, btn.label, btn.icon, btn.action)
    );

    // Call the timeline functions
    timeline_h();
    timeline_w();

    // Initialize current time display
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    // Animate timeline items on load
    animateTimelineItems();
  },

  onload_post_render(frm) {
    applyButtonStyles();
  },

  repo_url(frm) {
    return frm.doc.github_url;
  },

  fork_url(frm) {
    if (frm.doc.fork_name) {
      return frm.doc.github_url;
    }
  },

  fork_name(frm) {
    if (frm.doc.fork_data_type_name != "" && frm.doc.fork_owner != "") {
      let prefix = "seed";
      let us = "_";
      return (
        prefix + us + frm.doc.fork_owner + us + frm.doc.fork_data_type_name
      );
    }
  },
});

// Function to add buttons with icons and hover effects
function addIconButton(frm, label, iconClass, onClick) {
  const button = frm.add_custom_button(__(label), onClick);
  button.addClass("btn-icon-only");
  button.html(
    `<i class="${iconClass}" title="${label}"></i><span>${label}</span>`
  );

  button.hover(
    function () {
      $(this).find("span").fadeIn(200);
    },
    function () {
      $(this).find("span").fadeOut(200);
    }
  );
}

function applyButtonStyles() {
  const iconButtons = $(".btn-icon-only");
  if (iconButtons.length === 0) {
    return;
  }

  iconButtons.css({
    position: "relative",
    overflow: "hidden",
  });

  const iconButtonSpans = $(".btn-icon-only span");
  if (iconButtonSpans.length === 0) {
    return;
  }

  iconButtonSpans.css({
    display: "none",
    position: "absolute",
    left: "30px",
    whiteSpace: "nowrap",
  });

  iconButtons.hover(
    function () {
      $(this).css("width", "auto");
    },
    function () {
      $(this).css("width", "");
    }
  );
}

function generateLocalFiles() {
  frappe.show_progress(__("Generating Local Files"), 0, 100, "Please wait...");
  frappe.call({
    method: "tv_data.github._generate_files",
    callback: function (r) {
      frappe.hide_progress();
      if (!r.exc) frappe.msgprint(__("Local files generated successfully."));
    },
  });
}

function updateRepository() {
  frappe.show_progress(__("Updating Repository"), 0, 100, "Please wait...");
  frappe.call({
    method: "tv_data.github._update_repository",
    callback: function (r) {
      frappe.hide_progress();
      if (!r.exc) frappe.msgprint(__("Repository updated successfully."));
    },
  });
}

function sendPullRequest() {
  frappe.show_progress(__("Sending Pull Request"), 0, 100, "Please wait...");
  frappe.call({
    method: "tv_data.github._update_repository",
    callback: function (r) {
      frappe.hide_progress();
      if (!r.exc) frappe.msgprint(__("PR sent successfully."));
    },
  });
}

function mergeUpdates() {
  frappe.call({
    method: "tv_data.tv_data.doctype.datafield.datafield.extend_all_series",

    callback: function (r) {
      if (!r.exc) frappe.msgprint(__("Updates merged successfully."));
    },
  });
}

function animateTimelineItems() {
  setTimeout(() => {
    $(".timeline-item").each((index, item) => {
      setTimeout(() => {
        $(item).find(".timeline-content").css({
          opacity: 1,
          transform: "translateY(0)",
        });
      }, index * 100);
    });
  }, 500);
}

function updateCurrentTime() {
  const now = new Date();
  const timeString = now.toLocaleTimeString(frappe.boot.lang, {
    hour12: false,
  });
  $("#current-time-display").text(timeString);
}

// Timeline functions
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

// Function to update current time
// function updateCurrentTime() {
//   var now = new Date();
//   var timeString = now.toLocaleTimeString(frappe.boot.lang, {
//     hour12: false,
//   });
//   $("#current-time-display").text(timeString);
// }
