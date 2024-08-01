frappe.form.link_formatters["Datafield"] = function (value, doc) {
  console.log("link_formatters", value, doc);
  let statusIcon = "";
  let statusColor = "";

  // Define status icons and colors
  switch (doc.status) {
    case "Committed":
      statusIcon = "fa-check-circle";
      statusColor = "green";
      break;
    case "Pending":
      statusIcon = "fa-clock";
      statusColor = "gray";
      break;
    case "Rejected":
      statusIcon = "fa-times-circle";
      statusColor = "red";
      break;
    default:
      statusIcon = "fa-question-circle";
      statusColor = "gray";
  }

  // Create the HTML for the status icon
  let iconHtml = `<i class="fa ${statusIcon}" style="color: ${statusColor}; margin-right: 5px;"></i>`;
  console.log(iconHtml, value, "ÖÖÖ");
  // Combine the icon with the original value
  return `${iconHtml}${value} ÖÖÖ`;
};
