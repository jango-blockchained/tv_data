import frappe
from frappe.model.document import Document
import datetime
from typing import Dict, Optional, List, Any, Union


def get_doc_from_user_key(
    user: str,
    df: object = None,
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
    query: Dict[str, str] = {"key": df.key.upper(), "user": user}

    try:
        if frappe.db.exists("Datafield", query):
            return frappe.get_doc("Datafield", query)
        elif df.insert:
            doc = frappe.new_doc("Datafield")
            doc.key = df.key
            doc.value = df.value
            doc.n = df.n
            doc.user = user
            doc.insert()
            doc.insert_update(df.value, df.n)
            doc.save(ignore_permissions=True)
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

    @property
    def update_count(self) -> int:
        """Return the count of series entries in the document."""
        return len(self.datafield_update_table)

    def before_insert(self) -> None:
        """Perform actions before inserting the document."""
        self.set_scale()
        self.set_type()
        self.start_doc_series()

    def before_save(self) -> None:
        """Store the original value of the field before it is updated."""
        if not self.is_new():
            self._original_value = frappe.db.get_value("Datafield", self.name, "value")

    def on_update(self) -> None:
        """Check if the value has changed and updates the series."""
        if hasattr(self, "_original_value") and self.value != self._original_value:
            self.insert_update(self.value, self.n)

    def autoname(self) -> None:
        """Generates a unique name for the Datafield document."""
        if self.is_new():
            self.name = generate_unique_name(self.key)

    def validate(self) -> None:
        """Validate the document before saving."""
        self.key = self.key.upper()

        if not self.key:
            frappe.throw("Key is required for Datafield")
        if not self.user:
            frappe.throw("User is required for Datafield")

        # Check for unique key-user combination
        if self.is_new() and frappe.db.exists(
            "Datafield", {"key": self.key.upper(), "user": self.user}
        ):
            frappe.throw(
                f"A Datafield with key '{self.key}' already exists for user '{self.user}'"
            )

    def set_scale(self) -> None:
        """Sets the pricescale based on the number of decimal places in the value."""
        if not self.value:
            print("no value")
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

    def set_type(self) -> None:
        """Sets the type of the Datafield."""
        try:
            if self.n in (1, 2, 3, 4):
                self.type = "Dynamic Value"
            else:
                self.type = "OHLCV Series"
        except AttributeError:
            # Handle the case where self.n is None
            self.type = "OHLCV Series"

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
            m = self.merge_updates(day)
            m.update(
                {
                    "date_string": get_series_date(day),
                    "parent": self.name,
                    "parenttype": "Datafield",
                    "parentfield": "datafield_series_table",
                }
            )
            self.append("datafield_series_table", m)
        except Exception as e:
            frappe.log_error(f"Error in extend_doc_series: {str(e)}", "Datafield Error")
            raise

    @frappe.whitelist()
    def insert_update(self, value: Union[int, float], n: Optional[int]) -> None:
        """Handle new data for the Datafield."""

        try:
            print("insert update")
            new_entry = {
                "date_string": get_series_date(),
                "value": value,
                "n": n,
                "parent": self.name,
                "parenttype": "Datafield",
                "parentfield": "datafield_update_table",
            }
            self.append("datafield_update_table", new_entry)
        except Exception as e:
            frappe.log_error(
                f"Error in update_doc_series: {str(e)}", "Datafield Update Error"
            )
            raise

    def merge_updates(self, day: int = 0) -> Dict[str, Union[int, float]]:
        """Merge all open updates in the update table into the series table, to create a time series with OHLCV data.

        Args:
            day (int): The number of days to extend the series. Defaults to 0.

        Returns:
            Dict[str, Union[int, float]]: A dictionary containing the merged
            values for the series.
        """
        try:
            if not self.datafield_update_table:
                return self.datafield_series_table[-1].as_dict()

            updates = self.datafield_update_table
            _open = updates[0].value
            _close = updates[-1].value
            _high = updates[0].value
            _low = updates[0].value
            _volume = len(updates)
            for update in updates:
                _high = max(_high, update.value)
                _low = min(_low, update.value)
                update.delete()
            return {
                "open": _open,
                "high": _high,
                "low": _low,
                "close": _close,
                "volume": _volume,
            }
        except Exception as e:
            frappe.log_error(f"Error in merge_updates: {str(e)}", "Datafield Error")
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
