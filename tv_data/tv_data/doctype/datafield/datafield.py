# Copyright (c) 2024, cryptolinx <jango_blockchained> and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document
import os
import json
import secrets
import string
import csv


class Datafield(Document):

    def generate_files():
        # Directory to store the generated files
        data_dir = 'tv_data'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        storage_file_path = os.path.join(data_dir, 'seed_jango-blockchained_storage.json')
        storage_data = []

        datafields = frappe.get_all('Datafield', fields=['name', 'user', 'field_name', 'data'])

        for datafield in datafields:
            # Generate the symbol name
            symbol = f"{datafield['name']}_{datafield['field_name'].replace(' ', '_').upper()}"

            # Path to the CSV file
            csv_file_path = os.path.join(data_dir, f"{symbol}.csv")

            # Write CSV file
            with open(csv_file_path, mode='w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                # Writing headers
                csv_writer.writerow(['timestamp', 'value'])
                # Writing data
                csv_writer.writerow([frappe.utils.now(), datafield['data']])

            # Append to storage data
            storage_data.append({
                "symbol": symbol,
                "description": datafield['field_name'],
                "path": csv_file_path
            })

        # Write the storage JSON file
        with open(storage_file_path, 'w') as json_file:
            json.dump(storage_data, json_file, indent=4)

        return f"Files generated successfully in {data_dir}"

    def generate_custom_id(self):
        # Generate a unique 16-character alphanumeric hash
        hash_part = frappe.generate_hash(length=16).upper()
        # Format the description
        field_name_part = self.field_name.replace(' ', '_').upper()
        # Combine the parts
        custom_id = f"DATA_{hash_part}_{field_name_part}"
        return custom_id

    def validate(self):
        if self.field_exists():
            frappe.throw(f"A Datafield with description '{self.field_name}' already exists for user '{self.user}'.")
        return

    def on_update(self):
        pass

    def on_cancel(self):
        pass

    def on_trash(self):
        pass

    def on_submit(self):
        if not self.name:
            self.name = self.generate_custom_id()
        return

    def field_exists(self):
        return frappe.db.exists({
            "doctype": "Datafield",
            "user": self.user,
            "field_name": self.field_name
        })
