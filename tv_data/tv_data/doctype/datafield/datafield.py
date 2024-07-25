import frappe
from frappe.model.document import Document
import datetime
from typing import Dict, Optional, List, Any, Union


def exists_doc_from_user_key(key: str, user: str) -> bool:
    """
    Check if a Datafield with the specified key and user combination already exists.

    Args:
        key (str): The key of the Datafield.
        user (str): The user associated with the Datafield.

    Returns:
        bool: True if the combination exists, False otherwise.
    """
    return frappe.db.exists({"doctype": "Datafield", "key": key, "user": user})


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
            return frappe.get_doc(query)
        elif insert:

            doc = frappe.get_doc(
                {
                    "doctype": "Datafield",
                    "name": generate_unique_name(key),
                    "key": key,
                    "user": user,
                }
            )
            doc.insert(ignore_permissions=True)

            return doc
        else:
            return None
    except Exception as e:

        frappe.log_error(f"Error in get_doc_from_user_key: {str(e)}", "Datafield Error")
        return None


def get_series_date(days: int = 0) -> str:
    """
    Get the current date adjusted by the specified number of days and return it in the format "YYYYMMDDT".

    Args:
        days (int): The number of days to adjust the current date. Default is 0.

    Returns:
        str: The adjusted date in the format "YYYYMMDDT".
    """
    current_date: datetime.datetime = datetime.datetime.now()
    adjusted_date: datetime.datetime = current_date + datetime.timedelta(days=days)
    return adjusted_date.strftime("%Y%m%dT")


def generate_unique_name(key: str) -> str:
    """
    Generate a unique name for a Datafield document.

    Args:
        key (str): The key of the Datafield.

    Returns:
        str: The generated unique name in the format "DATA_{hash_code}_{key.upper()}".
    """
    while True:
        hash_code: str = frappe.generate_hash(length=16).upper()
        name = f"DATA_{hash_code}_{key.upper()}"
        if not frappe.db.exists("Datafield", name):
            return name


class Datafield(Document):
    @property
    def created(self) -> str:
        """Return the creation date of the document."""
        return self.creation

    @property
    def last_modified(self) -> str:
        """Return the last modification date of the document."""
        return self.modified

    @property
    def series_count(self) -> int:
        """Return the count of series entries in the document."""
        return len(self.datafield_series_table)

    def before_insert(self) -> None:
        """Perform actions before inserting the document."""
        self.set_scale()
        self.start_doc_series()

    def before_save(self) -> None:
        """Store the original value of the field before it is updated."""
        if not self.is_new():
            self._original_value = frappe.db.get_value("Datafield", self.name, "value")

    def on_update(self) -> None:
        """Check if the value has changed and updates the series."""
        if hasattr(self, "_original_value") and self.value != self._original_value:
            self.handle_new_data(self.value, self.n)

    def key_exists(self) -> bool:
        """Check if a Datafield with the specified key or name and user already exists."""
        return frappe.db.exists(
            {"doctype": "Datafield", "key": self.key, "user": self.user}
        )

    def autoname(self) -> None:
        """Generates a unique name for the Datafield document."""
        if self.is_new():
            self.name = generate_unique_name(self.key)

    def validate(self) -> None:
        """Validate the document before saving."""
        if not self.key:
            frappe.throw("Key is required for Datafield")
        if not self.user:
            frappe.throw("User is required for Datafield")

        # Check for unique key-user combination
        if self.is_new() and frappe.db.exists(
            "Datafield", {"key": self.key, "user": self.user}
        ):
            frappe.throw(
                f"A Datafield with key '{self.key}' already exists for user '{self.user}'"
            )

    def set_scale(self) -> None:
        """Sets the pricescale based on the number of decimal places in the value."""
        if not self.value:
            self.scale = 1
            return
        value_str = str(self.value)
        if "." in value_str:
            separator = "."
        elif "," in value_str:
            separator = ","
        else:
            self.scale = 1
            return
        try:
            _, fractional_part = value_str.split(separator)
            self.scale = 10 ** len(fractional_part)
        except ValueError:
            self.scale = 1

    def start_doc_series(self) -> None:
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
        except Exception as e:
            frappe.log_error(f"Error in start_doc_series: {str(e)}", "Datafield Error")
            raise

    @frappe.whitelist()
    def extend_doc_series(self, day: int = 0) -> None:
        """Extends the doc series for the Datafield document."""
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
        except Exception as e:
            frappe.log_error(f"Error in extend_doc_series: {str(e)}", "Datafield Error")
            raise

    @frappe.whitelist()
    def update_doc_series(
        self, value: Union[int, float], n: Optional[int] = None
    ) -> None:
        """Update or insert a Datafield document and its series table."""

        try:
            if self.datafield_series_table:
                last_series = self.datafield_series_table[-1]
                last_series.volume += 1
                if not n and last_series:
                    last_series.close = value
                    last_series.high = max(last_series.high, value)
                    last_series.low = min(last_series.low, value)
                elif n in [1, 2, 3, 4]:
                    field_map = {1: "open", 2: "high", 3: "low", 4: "close"}
                    setattr(last_series, field_map[n], value)
        except Exception as e:
            frappe.log_error(f"Error in update_doc_series: {str(e)}", "Datafield Error")
            raise

    @frappe.whitelist()
    def handle_new_data(self, value: Union[int, float], n: Optional[int]) -> None:
        """Handle new data for the Datafield."""
        try:
            self.value = value
            self.n = n
            self.update_doc_series(value, n)
        except Exception as e:
            frappe.log_error(f"Error in handle_new_data: {str(e)}", "Datafield Error")
            raise


def extend_all_series() -> None:
    """Extend the series for all Datafield documents."""
    frappe.db.begin()
    try:
        all_docs = frappe.get_all("Datafield")
        for doc_name in all_docs:
            doc = frappe.get_doc("Datafield", doc_name.name)
            doc.extend_doc_series()
            doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error in extend_all_series: {str(e)}", "Datafield Error")
        raise
