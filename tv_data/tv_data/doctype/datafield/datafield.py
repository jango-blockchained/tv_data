import frappe
from frappe.model.document import Document
import os
import json
import csv
import datetime

from typing import Dict, Optional, cast


def get_doc_from_user_key(
    user: str, key: str, insert: bool = False
) -> Optional[Document]:
    """
    Get the document associated with the key and user.

    Args:
        user (str): The user associated with the document.
        key (str): The key of the document.
        insert (bool, optional): Whether to insert a new document if not found. Defaults to False.

    Returns:
        Optional[Document]: The document associated with the key and user if found, None otherwise.
    """
    query: Dict[str, str] = {"doctype": "Datafield", "key": key, "user": user}

    try:
        if frappe.db.exists(query):
            return cast(Optional[Document], frappe.get_doc(query))
        else:
            if insert:
                doc: Document = frappe.new_doc("Datafield")
                doc.run_method("autoname")
                doc.key = key
                doc.user = user
                doc.insert(ignore_permissions=True)
                return doc
            else:
                return None
    except Exception:
        return None


def get_series_date(days: int = 0):
    current_date = datetime.datetime.now()
    adjusted_date = current_date + datetime.timedelta(days=days)
    return adjusted_date.strftime("%Y%m%dT")


class Datafield(Document):

    @property
    def created(self):
        return self.creation

    @property
    def last_modified(self):
        return self.modified

    @property
    def series_count(self):
        return len(self.datafield_series_table)

    # --------------------------------------------------------------------------------------------------------

    def autoname(self):
        """Generates a unique name for the Datafield document."""
        if self.is_new() and not self.name and self.key:
            # Generate a unique name using the key
            self.key = self.key.upper()
            hash_part = frappe.generate_hash(length=16).upper()
            self.name = f"DATA_{hash_part}_{self.key}"

    def before_insert(self):
        """Check if a Datafield with the same key and user already exists before inserting."""
        self.set_scale()
        self.start_doc_series()

    def before_save(self):
        """Store the original value of the field before it is updated."""
        if not self.is_new():
            self._original_value = frappe.db.get_value("Datafield", self.name, "value")

    def on_update(self):
        """Check if the value has changed and updates the series."""
        if hasattr(self, "_original_value") and self.value != self._original_value:
            self.handle_new_data(self.value, self.n)

    def key_exists(self):
        """Check if a Datafield with the specified key or name and user already exists."""
        return frappe.db.exists(
            {"doctype": "Datafield", "key": self.key, "user": self.user}
        )

    def validate(self):
        pass

    def on_cancel(self):
        pass

    def on_trash(self):
        pass

    def on_submit(self):
        pass

    # --------------------------------------------------------------------------------------------------------

    def set_scale(self):
        """
        Sets the pricescale based on the number of decimal places in the value.
        Args:
            self: The Datafield document object.
        """
        if not self.value:
            # Handle case where value is empty or None
            self.pricescale = 1
            return

        try:
            integer_part, fractional_part = str(self.value).split(".")
        except ValueError:
            self.pricescale = 1
            return

        # Calculate the scale based on the number of decimal places
        decimal_places = len(fractional_part)
        self.pricescale = 10**decimal_places

    def start_doc_series(self):
        """Initialize the document series."""
        try:
            series_entry = {
                "date_string": get_series_date(),
                "open": self.value,
                "high": self.value,
                "low": self.value,
                "close": self.value,
                "volume": 1,
                "parent": self.name,
                "parenttype": "Datafield",
                "parentfield": "datafield_series_table",
            }
            self.append("datafield_series_table", series_entry)
            self.save()
            frappe.db.commit()
            print("Datafield Series entry created successfully.")
        except Exception as e:
            frappe.log_error(
                f"An error occurred: {e}", "DataField Series Initialization Error"
            )
            print(f"An error occurred: {e}")

    @frappe.whitelist()
    def extend_doc_series(self, day: int = 0):
        """
        This method extends the doc series for all Datafield documents.
        """
        try:
            new_entry = {
                "date_string": get_series_date(day),
                "open": self.value,
                "high": self.value,
                "low": self.value,
                "close": self.value,
                "volume": 0,
                "parent": self.name,
                "parenttype": "Datafield",
                "parentfield": "datafield_series_table",
            }
            self.append("datafield_series_table", new_entry)
            self.save()
            frappe.db.commit()
            pass
        except Exception as e:
            frappe.log_error(f"An error occurred: {e}", "Extend Doc Series Error")

    @frappe.whitelist()
    def get_last_series(self):
        return self.datafield_series_table[-1]

    @frappe.whitelist()
    def update_doc_series(self, value, n=None):
        """Update or insert a Datafield document and its series table."""
        try:
            # Check and update the last series in the child table if it exists
            if self.datafield_series_table:
                last_series = self.get_last_series()
                if not n and last_series:
                    last_series.close = value
                    if last_series.high < value:
                        last_series.high = value
                    if last_series.low > value:
                        last_series.low = value
                    last_series.volume += 1
                else:
                    if n == 1:
                        last_series.open = value
                    elif n == 2:
                        last_series.high = value
                    elif n == 3:
                        last_series.low = value
                    elif n == 4:
                        last_series.close = value

            self.save()
            frappe.msgprint(f"Updated datafield '{self.name}'")
            return

        except Exception as e:
            # Log and raise error messages
            frappe.log_error(f"An error occurred: {e}", "DataField Update Error")
            frappe.throw(f"An error occurred: {e}")

    @frappe.whitelist()
    def handle_new_data(self, value, n):
        try:
            # Update the value of the parent document
            self.value = value
            self.n = n

            self.update_doc_series(value, n)
            self.save()

            frappe.db.commit()
            return

        except Exception as e:
            frappe.db.rollback()
            print(f"An error occurred: {e}")


def extend_all_series():
    try:
        all_docs = frappe.get_all("Datafield")

        for doc_name in all_docs:
            doc = frappe.get_doc("Datafield", doc_name.name)
            doc.extend_doc_series()

        frappe.db.commit()
        print("Successfull Extended Datafield Series")

    except Exception as e:
        frappe.db.rollback()
        print(f"An error occurred: {e}")


# @staticmethod
# def generate_files():
#     settings = frappe.get_single("TV Data Settings")
#     base_dir = 'tv_data'
#     data_dir = os.path.join(base_dir, 'data')
#     symbol_info_dir = os.path.join(base_dir, 'symbol_info')
#     github_dir = os.path.join(base_dir, '.github')

#     os.makedirs(data_dir, exist_ok=True)
#     os.makedirs(symbol_info_dir, exist_ok=True)
#     os.makedirs(github_dir, exist_ok=True)

#     storage_data = []

#     datafields = frappe.get_all('Datafield', fields=['name', 'user', 'key', 'value'])

#     for datafield in datafields:
#         # Generate CSV file
#         csv_file_path = os.path.join(data_dir, f"{datafield['name']}.csv")
#         with open(csv_file_path, mode='w', newline='') as csv_file:
#             csv_writer = csv.writer(csv_file)
#             # Assuming the first row should contain timestamps starting from now
#             csv_writer.writerow([datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datafield['value']])
#             # Add additional rows as per requirement

#         # Generate JSON file for symbol info
#         json_file_path = os.path.join(symbol_info_dir, f"seed_{datafield['name']}_{datafield['key']}.json")
#         with open(json_file_path, 'w') as json_file:
#             json.dump({
#                 "symbol": datafield['name'],
#                 "description": datafield['key'],
#                 "value": datafield['value']
#             }, json_file, indent=4)

#         # Prepare storage data structure
#         storage_data.append({
#             "symbol": datafield['name'],
#             "description": datafield['key'],
#             "path": csv_file_path
#         })

#     # Generate storage JSON file
#     storage_file_path = os.path.join(base_dir, f'{settings.fork_name}.json')
#     with open(storage_file_path, 'w') as json_file:
#         json.dump(storage_data, json_file, indent=4)

#     return f"Files generated successfully in {base_dir}"
