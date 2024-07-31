# Copyright (c) 2024, cryptolinx <jango_blockchained> and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class DatafieldUpdateTable(Document):

    @property
    def time_received(self) -> str:
        """Return the creation date of the document."""
        return self.creation

    @property
    def update_id(self) -> str:
        return self.name

    pass
