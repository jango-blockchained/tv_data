import frappe
from frappe.model.document import Document
import os
import json
import csv
import subprocess
import requests


class Datafield(Document):

    def autoname(self):
        if not self.field_exists():
            hash_part = frappe.generate_hash(length=16).upper()
            field_name_part = self.field_name.replace(' ', '_').upper()
            self.name = f"DATA_{hash_part}_{field_name_part}"
        return

    def before_insert(self):
        pass

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
        pass

    def field_exists(self):
        return frappe.db.exists({
            "doctype": "Datafield",
            "user": self.user,
            "field_name": self.field_name
        })


# STATICS
# -------

@staticmethod
def generate_files():
    settings = frappe.get_single("Datafield Settings")

    base_dir = 'tv_data'
    data_dir = os.path.join(base_dir, 'data')
    symbol_info_dir = os.path.join(base_dir, 'symbol_info')
    github_dir = os.path.join(base_dir, '.github')

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(symbol_info_dir, exist_ok=True)
    os.makedirs(github_dir, exist_ok=True)

    storage_data = []

    datafields = frappe.get_all('Datafield', fields=['name', 'user', 'field_name', 'data'])

    for datafield in datafields:
        symbol = f"{datafield['name']}_{datafield['field_name'].replace(' ', '_').upper()}"

        csv_file_path = os.path.join(data_dir, f"{symbol}.csv")

        with open(csv_file_path, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['timestamp', 'value'])
            csv_writer.writerow([frappe.utils.now(), datafield['data']])

        json_file_path = os.path.join(symbol_info_dir, f"seed_{datafield['name']}_{datafield['field_name']}.json")

        with open(json_file_path, 'w') as json_file:
            json.dump({
                "symbol": symbol,
                "description": datafield['field_name'],
                "data": datafield['data']
            }, json_file, indent=4)

        storage_data.append({
            "symbol": symbol,
            "description": datafield['field_name'],
            "path": csv_file_path
        })

    storage_file_path = os.path.join(base_dir, f'{settings.fork_name}.json')
    with open(storage_file_path, 'w') as json_file:
        json.dump(storage_data, json_file, indent=4)

    return f"Files generated successfully in {base_dir}"

@staticmethod
def update_repository():
    settings = frappe.get_single("Datafield Settings")
    repo_dir = 'tv_data_repo'
    remote_url = f'https://github.com/{settings.fork_owner}/{settings.fork_repo_name}.git'

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
    settings = frappe.get_single("Datafield Settings")
    repo_owner = settings.repo_owner
    repo_name = settings.repo_name
    fork_owner = settings.fork_owner
    fork_repo_name = settings.fork_repo_name
    branch_name = settings.branch_name
    repo_url = settings.github_url
    token = settings.github_token

    url = f'{settings.repo_url}/{settings.repo_owner}/{settings.repo_name}/pulls'

    data = {
        "title": settings.daily_commit_message,
        "head": f"{fork_owner}:{branch_name}",
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