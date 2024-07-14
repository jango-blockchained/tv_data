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

    def autoname(self):
        if not self.field_exists():
            hash_part = frappe.generate_hash(length=16).upper()
            key_part = self.key.replace(' ', '_').upper()
            self.name = f"DATA_{hash_part}_{key_part}"
        return

    def before_insert(self):
        if self.field_exists():
            frappe.throw(f"A Datafield with description '{self.key}' already exists for user '{self.user}'.")
        self.start_doc_series()
        return

    def validate(self):
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

    def field_exists(self):
        return frappe.db.exists({
            "doctype": "Datafield",
            "user": self.user,
            "key": self.key.replace(' ', '_').upper()
        })

    @staticmethod
    def getSeriesDate(days: int = 0):
        current_date = datetime.datetime.now()
        adjusted_date = current_date + datetime.timedelta(days=days)
        return adjusted_date.strftime('%Y%m%dT')

    # @staticmethod
    # def get_last_child(doc, child_table_field):
    #     child_table_data = doc.get(child_table_field)
    #     if child_table_data:
    #         last_entry = sorted(child_table_data, key=lambda x: x.idx, reverse=True)[0]
    #         return last_entry
    #     else:
    #         return None

    def start_doc_series(self):
        try:
            series_entry = {
                "doctype": "Datafield Series",
                "symbol": self.name,
                "date": self.getSeriesDate(),
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
            print(f"An error occurred: {e}")

    @staticmethod
    def extend_doc_series(doc):
        try:
            # last_series_entry = Datafield.get_last_child(doc, "datafield_series_table")
            new_series_entry = {
                "doctype": "Datafield Series",
                "date": Datafield.getSeriesDate(),
                "open": doc.value,
                "high": doc.value,
                "low": doc.value,
                "close": doc.value,
                "volume": 0,
                "parent": doc.name,
                "parenttype": "Datafield",
                "parentfield": "datafield_series_table"
            }
            doc.append("datafield_series_table", new_series_entry)
            doc.insert()
            print("Datafield Series entry created successfully.")
        except Exception as e:
            print(f"An error occurred: {e}")

    @staticmethod
    def extend_all_series():
        try:
            all = frappe.get_all("Datafield", fields={["name","key","value"]})
            for doc in all:
                Datafield.extend_doc_series(doc)

            frappe.db.commit()
            print(f"Successfull Extended Datafield Series: {len(all)}")

        except Exception as e:
            frappe.db.rollback()
            print(f"An error occurred: {e}")

    # STATICS
    # -------

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