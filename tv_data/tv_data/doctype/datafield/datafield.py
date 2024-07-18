import frappe
from frappe.model.document import Document
import os
import json
import csv
import datetime


class Datafield(Document):

    useID = False

    @property
    def created(self):
        return self.creation

    @property
    def last_modified(self):
        return self.modified

    @property
    def dynamic(self):
        return 1 if self.n >= 1 else 0

    def autoname(self):
        """Generates a unique name for the Datafield document."""
        self.key = self.key.replace(' ', '_').upper()
        if not self.field_exists():
            hash_part = frappe.generate_hash(length=16).upper()
            self.name = f"DATA_{hash_part}_{self.key}"
        return

    def before_insert(self):
        """Check if a Datafield with the same key and user already exists before inserting."""
        if self.field_exists():
            frappe.throw(f"A Datafield with description '{self.key}' already exists for user '{self.user}'.")
        self.scale = self.convert_to_pricescale()
        self.start_doc_series()
        return

    def validate(self):
        """Sanitize and validate the key."""
        self.key = self.key.replace(' ', '_').upper()
        return

    def on_update(self):
        pass

    def on_cancel(self):
        pass

    def on_trash(self):
        pass

    def on_submit(self):
        pass

    def field_exists(self, key=None):
        """Check if a Datafield with the specified key or name and user already exists."""
        key_to_check = self.key.replace(' ', '_').upper() if key is None else key.replace(' ', '_').upper()
        exists = frappe.db.exists({
            "doctype": "Datafield",
            "user": self.user,
            "key": key_to_check
        })
        if not exists:
            exists = frappe.db.exists({
                "doctype": "Datafield",
                "user": self.user,
                "name": key_to_check
            })
            if exists:
                self.useID = True
        return exists

    def convert_to_pricescale(self):
        int_part, frac_part = str(self.value).split('.')
        base_multiplier = 10 ** len(int_part)
        if len(int_part) > 1:
            adjustment_factor = 10 ** ((len(int_part) - 1) * 2)
            base_multiplier *= adjustment_factor
        frac_multiplier = 10 ** len(frac_part)
        total_multiplier = base_multiplier * frac_multiplier
        return round(total_multiplier)

    def start_doc_series(self):                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
        """Initialize the document series."""
        try:
            series_entry = {
                "date_string": getSeriesDate(),
                "open": self.value,
                "high": self.value,
                "low": self.value,
                "close": self.value,
                "volume": 1,
                "parent": self.name,
                "parenttype": "Datafield",
                "parentfield": "datafield_series_table"
            }
            self.append("datafield_series_table", series_entry)
            print("Datafield Series entry created successfully.")
        except Exception as e:
            frappe.log_error(f"An error occurred: {e}", "DataField Series Initialization Error")
            print(f"An error occurred: {e}")


    @frappe.whitelist()
    def extend_doc_series(self, day: int = 0):
        """
        This method extends the doc series for all Datafield documents.
        """
        try:
            new_entry = {
                "date_string": getSeriesDate(day),
                "open": self.value,
                "high": self.value,
                "low": self.value,
                "close": self.value,
                "volume": 1,
                "parent": self.name,
                "parenttype": "Datafield",
                "parentfield": "datafield_series_table"
            }
            self.append("datafield_series_table", new_entry)
            self.save()
            frappe.db.commit()
            pass
        except Exception as e:
            frappe.log_error(f"An error occurred: {e}", "Extend Doc Series Error")


    @frappe.whitelist()
    def update_doc(self, user, key, value, n=None):
        """Update or insert a Datafield document and its series table."""
        try:
            # Update the value of the parent document
            self.value = value

            # Check and update the last series in the child table if it exists
            if self.datafield_series_table:
                last_series = self.datafield_series_table[-1]
                if not n:
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

            # Save changes to the parent document (including its child table)
            self.save()
            frappe.db.commit()

            # Notify the user of success
            frappe.msgprint(f"Updated datafield '{key}'")

        except Exception as e:
            # Log and raise error messages
            frappe.log_error(f"An error occurred: {e}", "DataField Update Error")
            frappe.throw(f"An error occurred: {e}")


# STATICS
# -------

@staticmethod
def getSeriesDate(days: int = 0):
    current_date = datetime.datetime.now()
    adjusted_date = current_date + datetime.timedelta(days=days)
    return adjusted_date.strftime('%Y%m%dT')


@staticmethod
def generate_files():
    settings = frappe.get_single("TV Data Settings")
    base_dir = 'tv_data'
    data_dir = os.path.join(base_dir, 'data')
    symbol_info_dir = os.path.join(base_dir, 'symbol_info')
    github_dir = os.path.join(base_dir, '.github')

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(symbol_info_dir, exist_ok=True)
    os.makedirs(github_dir, exist_ok=True)

    storage_data = []

    datafields = frappe.get_all('Datafield', fields=['name', 'user', 'key', 'value'])

    for datafield in datafields:
        # Generate CSV file
        csv_file_path = os.path.join(data_dir, f"{datafield['name']}.csv")
        with open(csv_file_path, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            # Assuming the first row should contain timestamps starting from now
            csv_writer.writerow([datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datafield['value']])
            # Add additional rows as per requirement

        # Generate JSON file for symbol info
        json_file_path = os.path.join(symbol_info_dir, f"seed_{datafield['name']}_{datafield['key']}.json")
        with open(json_file_path, 'w') as json_file:
            json.dump({
                "symbol": datafield['name'],
                "description": datafield['key'],
                "value": datafield['value']
            }, json_file, indent=4)

        # Prepare storage data structure
        storage_data.append({
            "symbol": datafield['name'],
            "description": datafield['key'],
            "path": csv_file_path
        })

    # Generate storage JSON file
    storage_file_path = os.path.join(base_dir, f'{settings.fork_name}.json')
    with open(storage_file_path, 'w') as json_file:
        json.dump(storage_data, json_file, indent=4)

    return f"Files generated successfully in {base_dir}"

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

def update_doc(doc, user, key, value, n):
    return Datafield.update_doc(doc, user, key, value, n)