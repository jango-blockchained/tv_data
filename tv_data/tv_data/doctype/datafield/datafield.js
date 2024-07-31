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

    frappe.realtime.on("datafield_update", function (data) {
      if (
        (frappe.get_route_str() === `Form/${frappe.router.slug(data.doc_name)}`) or (data.doc_name === frm.doc.name)
      ) {
        frappe.show_alert({
          message: data.message,
          indicator: "green",
        });

        // Optionally, refresh the form
        frm.reload_doc();
      }
    });
  },
});
