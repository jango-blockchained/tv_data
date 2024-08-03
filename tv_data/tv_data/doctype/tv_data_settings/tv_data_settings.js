// Copyright (c) 2024, cryptolinx <jango_blockchained> and contributors
// For license information, please see license.txt

frappe.ui.form.on("TV Data Settings", {
  refresh(frm) {
    frm.trigger("repo_url");
    frm.trigger("fork_name");
    frm.trigger("fork_url");
    frm.add_custom_button(__("GitHub Fork"), function () {
      window.open(frm.doc.fork_url);
    });
    frm.add_custom_button(__("GitHub Repo"), function () {
      window.open(frm.doc.repo_url);
    });
    frm.add_custom_button(__("Generate Local Files"), function () {
      frappe.call({
        method: "tv_data.github._generate_files",
      });
    });
    frm.add_custom_button(__("Update Repo"), function () {
      frappe.call({
        method: "tv_data.github._update_repository",
      });
    });
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
