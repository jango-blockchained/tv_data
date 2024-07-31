frappe.ui.form.on("Datafield", {
  refresh: function (frm) {
    frm.add_custom_button(__("Merge Updates"), function () {
      frappe
        .call({
          method: "tv_data.tv_data.doctype.datafield.datafield.extend_series",
          args: {
            doc_name: frm.doc.name,
          },
        })
        .then((r) => {
          if (r.message) {
            frappe.msgprint(__("Merge Updates executed successfully."));
            frm.reload_doc();
          }
        });
    });
  },
});
