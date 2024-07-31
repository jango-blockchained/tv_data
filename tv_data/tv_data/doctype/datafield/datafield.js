frappe.ui.form.on('Datafield', {
	refresh: function (frm) {
		frm.events.render_chart(frm);
		frm.add_custom_button(__('Merge Updates'), function () {
			frappe
				.call({
					method: 'tv_data.tv_data.doctype.datafield.datafield.extend_series',
					args: {
						doc_name: frm.doc.name,
					},
				})
				.then((r) => {
					if (r.message) {
						frappe.msgprint(__('Merge Updates executed successfully.'));
						frm.reload_doc();
					}
				});
		});
	},
	render_chart: function (frm) {
		if (!frm.doc.chart_html) {
			return;
		}

		frm.events.clear_chart(frm);

		let data = frm.events.get_chart_data(frm);

		if (data.labels.length === 0) {
			$(frm.fields_dict.chart_html.wrapper).html(
				'<div class="alert alert-warning">No data available for the chart.</div>'
			);
			return;
		}

		let chart = new frappe.Chart(frm.fields_dict.chart_html.wrapper, {
			title: 'Datafield Series Chart',
			data: data,
			type: 'line',
			height: 300,
			colors: ['#7cd6fd', '#743ee2', '#5e64ff', '#ffa00a', '#ff5858'],
			lineOptions: {
				hideDots: 1,
				heatline: 1,
			},
			axisOptions: {
				xIsSeries: true,
			},
			tooltipOptions: {
				formatTooltipX: (d) => (d + '').toUpperCase(),
				formatTooltipY: (d) => d + ' units',
			},
		});
	},

	clear_chart: function (frm) {
		$(frm.fields_dict.chart_html.wrapper).empty();
	},

	get_chart_data: function (frm) {
		let labels = [];
		let datasets = [
			{ name: 'Open', values: [] },
			{ name: 'High', values: [] },
			{ name: 'Low', values: [] },
			{ name: 'Close', values: [] },
			{ name: 'Volume', values: [] },
		];

		(frm.doc.datafield_series || []).forEach(function (row) {
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

// frappe.realtime.on('datafield_update', function (data) {
// 	console.log('Datafield Update', data);
// 	if (frappe.get_route_str() === `Form/${frappe.router.slug(data.doc_name)}` || data.doc_name == cur_frm.doc.name) {
// 		frappe.show_alert({
// 			message: data.message,
// 			indicator: 'green',
// 		});

// 		// Optionally, refresh the form
// 		frm.reload_doc();
// 	}
// });

// function render_chart(frm) {
// 	// HTML content for the chart
// 	let html = '<canvas id="myChart" width="100%" min-height="400"></canvas>';
// 	frm.fields_dict['chart'].wrapper.innerHTML = html;

// 	// Data for the chart
// 	let data = {
// 		labels: ['January', 'February', 'March', 'April', 'May', 'June'],
// 		datasets: [
// 			{
// 				label: 'My Dataset',
// 				backgroundColor: 'rgba(75,192,192,0.4)',
// 				borderColor: 'rgba(75,192,192,1)',
// 				data: [65, 59, 80, 81, 56, 55],
// 			},
// 		],
// 	};

// 	// Options for the chart
// 	let options = {
// 		responsive: true,
// 		maintainAspectRatio: false,
// 	};

// 	// Render the chart
// 	let ctx = document.getElementById('myChart').getContext('2d');
// 	new Chart(ctx, {
// 		type: 'line', // Change the type as needed: 'bar', 'line', 'pie', etc.
// 		data: data,
// 		options: options,
// 	});
// }
