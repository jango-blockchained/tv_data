import frappe
from frappe.model.document import Document
import os
import json
import csv
import subprocess
import requests
import datetime
from frappe.utils.password import get_decrypted_password

class Datafield(Document):

    useID = False


    def autoname(self):
        """Generates a unique name for the Datafield document."""
        if not self.field_exists():
            hash_part = frappe.generate_hash(length=16).upper()
            key_part = self.key.replace(' ', '_').upper()
            self.name = f"DATA_{hash_part}_{key_part}"
        return

    def before_insert(self):
        """Check if a Datafield with the same key and user already exists before inserting."""
        if self.field_exists():
            frappe.throw(f"A Datafield with description '{self.key}' already exists for user '{self.user}'.")
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
    def update_doc(user, key, value, n=None, insert=False):
        """Update or insert a Datafield document and its series table."""
        try:
            normalized_key = key.replace(' ', '_').upper()
            existing_doc = frappe.get_all('Datafield', filters={'user': user, 'key': normalized_key}, limit=1)

            if not existing_doc:
                existing_doc = frappe.get_all('Datafield', filters={'user': user, 'name': normalized_key}, limit=1)

            if existing_doc:
                doc = frappe.get_doc('Datafield', existing_doc[0].name)
            else:
                if insert:
                    doc = frappe.new_doc('Datafield')
                    doc.update({
                        'doctype': 'Datafield',
                        'key': normalized_key,
                        'user': user,
                        'value': value
                    })
                else:
                    frappe.log_error(f"No Datafield found for user '{user}' with key or name '{key}'")

            # Update the value of the parent document
            doc.value = value

            # Check and update the last series in the child table if it exists
            if doc.datafield_series_table:
                last_series = doc.datafield_series_table[-1]
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
                    elif n == 5:
                        last_series.volume = value

            # Save changes to the parent document (including its child table)
            doc.save()
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

        csv_file_path = os.path.join(data_dir, f"{datafield['name']}.csv")

        with open(csv_file_path, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            # csv_writer.writerow(['timestamp', 'value'])
            csv_writer.writerow([frappe.utils.now(), datafield['value']])

        json_file_path = os.path.join(symbol_info_dir, f"seed_{datafield['name']}_{datafield['key']}.json")

        with open(json_file_path, 'w') as json_file:
            json.dump({
                "symbol": datafield['name'],
                "description": datafield['key'],
                "value": datafield['value']
            }, json_file, indent=4)

        storage_data.append({
            "symbol": datafield['name'],
            "description": datafield['key'],
            "path": csv_file_path
        })

    storage_file_path = os.path.join(base_dir, f'{settings.fork_name}.json')
    with open(storage_file_path, 'w') as json_file:
        json.dump(storage_data, json_file, indent=4)

    return f"Files generated successfully in {base_dir}"


@staticmethod
def update_repository():
    settings = frappe.get_single("TV Data Settings")
    repo_dir = 'tv_data_repo'
    remote_url = f"https://github.com/{settings.fork_owner}/{settings.fork_repo_name}.git"

    if not os.path.exists(repo_dir):
        subprocess.run(['git', 'clone', remote_url, repo_dir])

    os.chdir(repo_dir)
    subprocess.run(['git', 'pull'])
    base_dir = '../tv_data'
    subprocess.run(['cp', '-r', f"{base_dir}/.", '.'])
    subprocess.run(['git', 'add', '.'])
    subprocess.run(['git', 'commit', '-m', settings.daily_commit_message])
    subprocess.run(['git', 'push'])
    os.chdir('..')

    return "Repository updated successfully"


@staticmethod
def create_pull_request():
    settings = frappe.get_single("TV Data Settings")
    token = get_decrypted_password( # type: ignore
        "TV Data Settings", "TV Data Settings", "github_token", False
    )
    url = f"{settings.repo_url}/{settings.repo_owner}/{settings.repo_name}/pulls"

    data = {
        "title": settings.daily_commit_message,
        "head": f"{settings.fork_owner}:{settings.fork_branch}",
        "base": "main",
        "body": settings.pr_body
    }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        return "Pull request created successfully"
    else:
        return f"Failed to create pull request: {response.json()}"

@frappe.whitelist
@staticmethod
def extend_all_series():
    try:
        all = frappe.get_all("Datafield", fields={["name","key","value","datafield_series_table"]})
        for doc in all:
            doc.extend_doc_series()

        frappe.db.commit()
        print(f"Successfull Extended Datafield Series: {len(all)}")

    except Exception as e:
        frappe.db.rollback()
        print(f"An error occurred: {e}")