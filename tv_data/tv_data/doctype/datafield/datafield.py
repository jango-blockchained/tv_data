import frappe
from frappe.model.document import Document
import datetime
from typing import Dict, Optional, Union
from frappe import _
import os
import csv
import json
import requests


def get_doc_from_user_key(user: str, df: object = None) -> Optional[Document]:
    query = {"key": df.key.upper(), "user": user}
    try:
        if frappe.db.exists("Datafield", query):
            return frappe.get_doc("Datafield", query)
        elif df.insert:
            doc = frappe.new_doc("Datafield")
            doc.update(
                {"key": df.key, "value": float(df.value), "n": int(df.n), "user": user}
            )
            doc.insert(ignore_permissions=True)
            return doc
        return None
    except Exception as e:
        frappe.log_error(f"Error in get_doc_from_user_key: {str(e)}", "Datafield Error")
        return None


def get_series_date(days: int = 0) -> str:
    return (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y%m%dT")


def generate_unique_name(key: str) -> str:
    cfg = frappe.get_single("TV Data Settings")
    while True:
        hash_code = frappe.generate_hash(length=cfg.field_name_hash_length).upper()
        name = f"DATA_{hash_code}_{key.upper()}"
        if not frappe.db.exists("Datafield", name):
            return name


class Datafield(Document):
    @property
    def created(self) -> str:
        return self.creation

    @property
    def last_modified(self) -> str:
        return self.modified

    @property
    def series_count(self) -> int:
        return len(self.datafield_series_table)

    @property
    def update_count(self) -> int:
        return len(self.datafield_update_table)

    def before_insert(self) -> None:
        self.set_scale()
        self.set_type()
        self.start_doc_series()

    def before_save(self) -> None:
        if not self.is_new():
            self._original_value = frappe.db.get_value("Datafield", self.name, "value")

    def on_update(self) -> None:
        if hasattr(self, "_original_value") and self.value != self._original_value:
            self.insert_update(self.value, self.n)

    def autoname(self) -> None:
        if self.is_new():
            self.name = generate_unique_name(self.key)

    def validate(self) -> None:
        self.key = self.key.upper()
        if not self.key:
            frappe.throw("Key is required for Datafield")
        if not self.user:
            frappe.throw("User is required for Datafield")
        if self.is_new() and frappe.db.exists(
            "Datafield", {"key": self.key, "user": self.user}
        ):
            frappe.throw(
                f"A Datafield with key '{self.key}' already exists for user '{self.user}'"
            )

    def set_scale(self) -> None:
        if self.value is None:
            self.scale = 1
            return
        value_str = str(float(self.value))
        separator = "." if "." in value_str else "," if "," in value_str else None
        if separator:
            try:
                _, fractional_part = value_str.split(separator)
                self.scale = 10 ** len(fractional_part)
            except ValueError:
                self.scale = 1
        else:
            self.scale = 1

    def set_type(self) -> None:
        self.type = (
            "Dynamic Value" if getattr(self, "n", 0) in (1, 2, 3, 4) else "OHLCV Series"
        )

    def start_doc_series(self) -> None:
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

    # @frappe.whitelist()
    # def extend_doc_series(self, day: int = 0) -> None:
    #     try:
    #         m = self.merge_updates(day)
    #         m.update(
    #             {
    #                 "date_string": get_series_date(day),
    #                 "parent": self.name,
    #                 "parenttype": "Datafield",
    #                 "parentfield": "datafield_series_table",
    #             }
    #         )
    #         self.append("datafield_series_table", m)
    #     except Exception as e:
    #         frappe.log_error(f"Error in extend_doc_series: {str(e)}", "Datafield Error")
    #         raise

    def insert_update(self, value: float, n: Optional[int]) -> None:
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
        try:
            if not self.datafield_update_table:
                return (
                    self.datafield_series_table[-1].as_dict()
                    if self.datafield_series_table
                    else {}
                )

            updates = self.datafield_update_table
            _open, _close = updates[0].value, updates[-1].value
            _high = max(update.value for update in updates)
            _low = min(update.value for update in updates)
            _volume = len(updates)

            merged_data = {
                "doctype": "Datafield Series",
                "open": _open,
                "high": _high,
                "low": _low,
                "close": _close,
                "volume": _volume,
                "date_string": get_series_date(day),
                "parent": self.name,
                "parenttype": "Datafield",
                "parentfield": "datafield_series_table",
            }

            # frappe.db.begin()
            try:
                # First, append the new series entry
                self.append("datafield_series_table", merged_data)
                self.save()

                # Only after successful save, process the updates
                for update in updates:
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

        except Exception as e:
            frappe.log_error(f"Error in merge_updates: {str(e)}", "Datafield Error")
            raise


@frappe.whitelist(allow_guest=True)
def extend_all_series() -> None:
    try:
        for doc_name in frappe.get_all("Datafield", pluck="name"):
            doc = frappe.get_doc("Datafield", doc_name)
            doc.merge_updates()
            doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            f"Error in extend_all_series: {str(e)}", "Datafield Series Error"
        )
        raise


@frappe.whitelist(allow_guest=True)
def merge_updates(doc_name: str) -> None:
    try:
        doc = frappe.get_doc("Datafield", doc_name)
        doc.merge_updates()
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


@staticmethod
def generate_files():
    settings = frappe.get_single("TV Data Settings")
    base_dir = "tv_data"
    dirs = {
        "data": os.path.join(base_dir, "data"),
        "symbol_info": os.path.join(base_dir, "symbol_info"),
        "github": os.path.join(base_dir, ".github"),
    }
    for directory in dirs.values():
        os.makedirs(directory, exist_ok=True)

    storage_data = []
    for datafield in frappe.get_all(
        "Datafield", fields=["name", "user", "key", "value"]
    ):
        csv_file_path = os.path.join(dirs["data"], f"{datafield['name']}.csv")
        with open(csv_file_path, mode="w", newline="") as csv_file:
            csv.writer(csv_file).writerow([frappe.utils.now(), datafield["value"]])

        json_file_path = os.path.join(
            dirs["symbol_info"], f"seed_{datafield['name']}_{datafield['key']}.json"
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

    with open(os.path.join(base_dir, f"{settings.fork_name}.json"), "w") as json_file:
        json.dump(storage_data, json_file, indent=4)

    return f"Files generated successfully in {base_dir}"


@staticmethod
def update_repository():
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
    subprocess.run(["cp", "-r", "../tv_data/.", "."])
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", settings.daily_commit_message])
    subprocess.run(["git", "push"])
    os.chdir("..")

    return "Repository updated successfully"


@staticmethod
def create_pull_request():
    settings = frappe.get_single("TV Data Settings")
    # Instead of using get_decrypted_password, we'll assume the token is stored securely
    # and can be accessed directly from the settings
    token = settings.get_password("github_token")
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

    return (
        "Pull request created successfully"
        if response.status_code == 201
        else f"Failed to create pull request: {response.json()}"
    )
