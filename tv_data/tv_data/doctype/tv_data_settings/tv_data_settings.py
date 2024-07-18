# Copyright (c) 2024, cryptolinx <jango_blockchained> and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TVDataSettings(Document):

    @property
    def fork_name(self):
        if self.fork_owner and self.fork_data_type_name:
            return f"seed_{self.fork_owner.lower()}_{self.fork_data_type_name.lower()}"
        return

    @property
    def repo_url(self):
        if self.repo_owner and self.repo_name:
            return f"{self.github_url}/{self.repo_owner}/{self.repo_name}.git"
        return

    @property
    def fork_url(self):
        if self.repo_owner and self.repo_name and self.fork_name:
            return f"{self.github_url}/{self.fork_owner}/{self.fork_name}.git"
        return
