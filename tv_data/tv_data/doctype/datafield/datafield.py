import frappe
from frappe.model.document import Document
import datetime
from typing import Dict, Optional, Union


from frappe import _


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
            doc.value = float(df.value)
            doc.n = int(df.n)
            doc.user = user
            doc.insert()
            # doc.insert_update(df.value, df.n)
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
    # cfg = frappe.get_single("TV Data Settings")
    while True:
        hash_code: str = frappe.generate_hash(length=8).upper()
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

        if self.is_new() and frappe.db.exists(
            "Datafield", {"key": self.key.upper(), "user": self.user}
        ):
            frappe.throw(
                f"A Datafield with key '{self.key}' already exists for user '{self.user}'"
            )

    def set_scale(self) -> None:
        """Sets the pricescale based on the number of decimal places in the value."""
        if self.value is None:
            self.scale = 1
            return
        value_str = str(float(self.value))
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
    def insert_update(self, value: float, n: Optional[int]) -> None:
        """Handle new data for the Datafield."""

        try:
            new_entry = {
                "date_string": get_series_date(),
                "time_received": datetime.datetime.now(),
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
        """Merge all open updates in the update table, prepare OHLCV data, and handle the movement of updates to Datafield Merged Update.

        Args:
            day (int): The number of days to extend the series. Defaults to 0.

        Returns:
            Dict[str, Union[int, float]]: A dictionary containing the merged
            values for the series.
        """
        try:
            if not self.datafield_update_table:
                return (
                    self.datafield_series_table[-1].as_dict()
                    if self.datafield_series_table
                    else {}
                )

            updates = self.datafield_update_table
            _open: float = updates[0].value
            _close: float = updates[-1].value
            _high: float = _open
            _low: float = _open
            _volume = len(updates)

            frappe.db.begin()

            try:
                for update in updates:
                    _high = max(_high, update.value)
                    _low = min(_low, update.value)

                    merged_update = frappe.get_doc(
                        {
                            "doctype": "Datafield Merged Update",
                            "datafield": self.name,
                            "datafield_update": update.name,
                            "value": update.value,
                        }
                    )
                    merged_update.insert(ignore_permissions=True)
                    update.delete()

                frappe.db.commit()

            except Exception as e:
                frappe.db.rollback()
                frappe.log_error(
                    f"Error in merge_updates transaction: {str(e)}", "Datafield Error"
                )
                raise

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


@frappe.whitelist()
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
        frappe.log_error(
            f"Error in extend_all_series: {str(e)}",
            "Datafield Series Error",
            "Datafield Series",
            doc_name,
        )
        raise


@frappe.whitelist()
def extend_series(doc_name: str) -> None:
    """Extend the series for all Datafield documents."""
    frappe.db.begin()
    try:
        doc = frappe.get_doc("Datafield", doc_name)
        doc.extend_doc_series()
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            f"Error in extend_series: {str(e)}",
            "Datafield Series Error",
            "Datafield Series",
            doc_name,
        )
        raise


@frappe.whitelist(allow_guest=True)
def get_list():
    if not frappe.has_permission("Datafield", "read"):
        frappe.throw(_("No permission for Datafield"), frappe.PermissionError)

    return frappe.get_list("Datafield", fields=["name", "key", "value", "user", "type"])


# STATICS
# -------


@staticmethod
def generate_files():
    settings = frappe.get_single("TV Data Settings")
    base_dir = "tv_data"
    data_dir = os.path.join(base_dir, "data")
    symbol_info_dir = os.path.join(base_dir, "symbol_info")
    github_dir = os.path.join(base_dir, ".github")

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(symbol_info_dir, exist_ok=True)
    os.makedirs(github_dir, exist_ok=True)

    storage_data = []

    datafields = frappe.get_all("Datafield", fields=["name", "user", "key", "value"])

    for datafield in datafields:

        csv_file_path = os.path.join(data_dir, f"{datafield['name']}.csv")

        with open(csv_file_path, mode="w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            # csv_writer.writerow(['timestamp', 'value'])
            csv_writer.writerow([frappe.utils.now(), datafield["value"]])

        json_file_path = os.path.join(
            symbol_info_dir, f"seed_{datafield['name']}_{datafield['key']}.json"
        )

        with open(json_file_path, "w") as json_file:
            json.dump(
                {
                    "symbol": datafield["name"],
                    "description": datafield["key"],
                    "value": datafield["value"],
                },
                json_file,
                indent=4,
            )

        storage_data.append(
            {
                "symbol": datafield["name"],
                "description": datafield["key"],
                "path": csv_file_path,
            }
        )

    storage_file_path = os.path.join(base_dir, f"{settings.fork_name}.json")
    with open(storage_file_path, "w") as json_file:
        json.dump(storage_data, json_file, indent=4)

    return f"Files generated successfully in {base_dir}"


@staticmethod
def update_repository():
    import os
    import subprocess

    settings = frappe.get_single("TV Data Settings")
    repo_dir = "tv_data_repo"
    remote_url = (
        f"https://github.com/{settings.fork_owner}/{settings.fork_repo_name}.git"
    )

    if not os.path.exists(repo_dir):
        subprocess.run(["git", "clone", remote_url, repo_dir])

    os.chdir(repo_dir)
    subprocess.run(["git", "pull"])
    base_dir = "../tv_data"
    subprocess.run(["cp", "-r", f"{base_dir}/.", "."])
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", settings.daily_commit_message])
    subprocess.run(["git", "push"])
    os.chdir("..")

    return "Repository updated successfully"


@staticmethod
def create_pull_request():
    settings = frappe.get_single("TV Data Settings")
    token = get_decrypted_password(  # type: ignore
        "TV Data Settings", "TV Data Settings", "github_token", False
    )
    url = f"{settings.repo_url}/{settings.repo_owner}/{settings.repo_name}/pulls"

    data = {
        "title": settings.daily_commit_message,
        "head": f"{settings.fork_owner}:{settings.fork_branch}",
        "base": "main",
        "body": settings.pr_body,
    }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        return "Pull request created successfully"
    else:
        return f"Failed to create pull request: {response.json()}"


# EOF
