// Copyright (c) 2024, cryptolinx <jango_blockchained> and contributors
// For license information, please see license.txt

frappe.ui.form.on("Datafield", {
  refresh(frm) {
    frm.trigger("add_buttons");
  },

  add_buttons(frm) {
    frm.add_custom_button(__("Edit Value"), () => frm.trigger("edit_value"));
  },

  edit_value(frm) {
    open_dialog(frm, "value");
  },

  edit_n(frm) {
    open_dialog(frm, "n");
  },
});

function open_dialog(frm) {
  let d = new frappe.ui.Dialog({
    title: `Inject Update`,
    fields: [
      {
        label: "Value",
        fieldname: "value",
        fieldtype: "Float",
        reqd: 1,
      },
      {
        label: "N",
        fieldname: "n",
        fieldtype: "Float",
        reqd: 1,
      },
    ],
    primary_action_label: "Set",
    primary_action(values) {
      set_values_and_hide(frm, values, d);
    },
  });

  d.show();
}

function set_values_and_hide(frm, values, dialog) {
  return new Promise((resolve, reject) => {
    frm
      .set_value(values)
      .then(() => {
        dialog.hide();
        resolve();
      })
      .catch((err) => {
        frappe.throw(__("Error setting values: ") + err.message);
        reject(err);
      });
  });
}
