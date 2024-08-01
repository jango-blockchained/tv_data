frappe.ui.form.on("Datafield", {
  refresh: function (frm) {
    frm.events.render_chart(frm);
  },

  render_chart: function (frm) {
    let wrapper = frm.get_field("chart_html").$wrapper;

    // If chart_html field doesn't exist, create a new section for the chart
    if (!wrapper.length) {
      let chart_area = $(
        '<div class="form-group"><div class="clearfix"><label class="control-label">Chart</label></div><div class="control-value"></div></div>'
      );
      frm.fields_dict.chart_area = {
        wrapper: chart_area.find(".control-value"),
      };
      wrapper = frm.fields_dict.chart_area.wrapper;

      // Append the new section to the form
      frm.wrapper.find(".form-page:first").append(chart_area);
    }

    wrapper.empty();

    let data = frm.events.get_chart_data(frm);

    if (data.labels.length === 0) {
      wrapper.html(
        '<div class="alert alert-warning">No data available for the chart.</div>'
      );
      return;
    }

    try {
      new frappe.Chart(wrapper[0], {
        title: "Datafield Series Chart",
        data: data,
        type: "axis-mixed",
        height: 300,
        colors: ["#ff0066", "#00ffbb", "#00ddff", "#ffcc00", "#ff4d00"],
        lineOptions: {
          hideDots: 1,
          heatline: 1,
        },
        barOptions: {
          spaceRatio: 0.5,
        },
        axisOptions: {
          xIsSeries: true,
        },
        // tooltipOptions: {
        //   formatTooltipX: (d) => (d + "").toUpperCase(),
        //   formatTooltipY: (d) => d + " units",
        // },
      });
    } catch (error) {
      console.error("Error rendering chart:", error);
      wrapper.html(
        '<div class="alert alert-danger">Error rendering chart. Please check console for details.</div>'
      );
    }
  },

  get_chart_data: function (frm) {
    let labels = [];
    let datasets = [
      { name: "Open", values: [], chartType: "line" },
      { name: "High", values: [], chartType: "line" },
      { name: "Low", values: [], chartType: "line" },
      { name: "Close", values: [], chartType: "line" },
      { name: "Volume", values: [], chartType: "bar" },
    ];

    (frm.doc.datafield_series_table || []).forEach(function (row) {
      labels.push(row.date_string);
      datasets[0].values.push(row.open);
      datasets[1].values.push(row.high);
      datasets[2].values.push(row.low);
      datasets[3].values.push(row.close);
      datasets[4].values.push(row.volume);
    });

    return {
      labels: labels,
      datasets: datasets,
    };
  },
});

frappe.realtime.on("datafield_update", function (data) {
  console.log("Datafield Update", data);
  if (
    frappe.get_route_str() === `Form/${frappe.router.slug(data.doc_name)}` ||
    data.doc_name == cur_frm.doc.name
  ) {
    frappe.show_alert({
      message: data.message,
      indicator: "green",
    });

    // Refresh the form
    cur_frm.reload_doc();
  }
});
