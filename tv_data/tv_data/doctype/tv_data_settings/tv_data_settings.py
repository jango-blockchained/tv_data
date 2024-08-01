# import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt
from typing import List, Union


class TVDataSettingsDefaults:
    def __init__(self, defaults_table: List[Document]) -> None:
        """
        Initialize the TVDataSettingsDefaults object.

        Args:
            defaults_table (List[Document]): A list of documents representing the defaults table.

        Returns:
            None
        """
        for default in defaults_table:
            value = self._convert_value(default.def_value, default.def_type)
            setattr(self, default.def_name, value)

    def _convert_value(self, value: str, value_type: str) -> Union[float, int, str]:
        """
        Convert the given value to the specified value type.

        Args:
            value (str): The value to be converted.
            value_type (str): The type to which the value should be converted.
                Possible values are "Float", "Int", "Check", or "Data".

        Returns:
            Union[float, int, str]: The converted value.
        """
        if value_type == "Float":
            return flt(value)
        elif value_type == "Int":
            return cint(value)
        elif value_type == "Check":
            return cint(value) == 1
        else:  # "Data" or any other type
            return value

    def __getattr__(self, name):
        return None


class TVDataSettings(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._defaults = None

    @property
    def defaults(self):
        if self._defaults is None:
            self._defaults = TVDataSettingsDefaults(
                self.tv_data_settings_defaults_table
            )
        return self._defaults

    @property
    def fork_name(self):
        if self.fork_owner and self.fork_data_type_name:
            return f"seed_{self.fork_owner.lower()}_{self.fork_data_type_name.lower()}"
        return None

    @property
    def repo_url(self):
        if self.repo_owner and self.repo_name:
            return f"{self.github_url}/{self.repo_owner}/{self.repo_name}.git"
        return None

    @property
    def fork_url(self):
        if self.repo_owner and self.repo_name and self.fork_name:
            return f"{self.github_url}/{self.fork_owner}/{self.fork_name}.git"
        return None

    def validate(self):
        if self.fork_data_type_name:
            self.fork_data_type_name = self.fork_data_type_name.strip()
        if self.repo_owner:
            self.repo_owner = self.repo_owner.strip()
        if self.repo_name:
            self.repo_name = self.repo_name.strip()
        if self.fork_owner:
            self.fork_owner = self.fork_owner.strip()
        if self.fork_data_type_name:
            self.fork_data_type_name = self.fork_data_type_name.strip()
