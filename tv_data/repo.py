import frappe
from frappe.model.document import Document
import os
import json
import csv
import requests
import subprocess
import datetime
from frappe.utils.password import get_decrypted_password  # Careful with security
from git import Repo


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
    token = get_decrypted_password(  # type: ignore
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