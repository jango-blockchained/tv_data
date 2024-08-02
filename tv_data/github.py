import os
import csv
import json
import subprocess
import requests
import frappe
from frappe.utils.password import get_decrypted_password


class GithubManager:
    @staticmethod
    def generate_files():
        settings = frappe.get_single("TV Data Settings")
        base_dir = "tv_data"
        dirs = {
            "data": os.path.join(base_dir, "data"),
            "symbol_info": os.path.join(base_dir, "symbol_info"),
            "github": os.path.join(base_dir, ".github"),
        }

        # Clear existing files in the target directories
        for directory in dirs.values():
            if os.path.exists(directory):
                for file_name in os.listdir(directory):
                    file_path = os.path.join(directory, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

        for directory in dirs.values():
            os.makedirs(directory, exist_ok=True)

        storage_data = {"description": [], "pricescale": [], "symbol": []}

        datafields = frappe.get_all(
            "Datafield", fields=["name", "user", "key", "value", "scale"]
        )

        for datafield in datafields:
            # Ensure `value` is a list of dictionaries
            value = datafield["value"]
            if isinstance(value, str):
                # Assuming the value might be a JSON string or CSV data
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, attempt to parse as CSV
                    value = GithubManager._parse_csv_string(value)
            elif not isinstance(value, list):
                # Handle unexpected formats
                raise TypeError(f"Unexpected data type for value: {type(value)}")

            csv_file_path = os.path.join(dirs["data"], f"{datafield['name']}.csv")
            GithubManager._write_csv(csv_file_path, value)
            storage_data["description"].append(datafield["key"])
            storage_data["pricescale"].append(datafield["scale"])
            storage_data["symbol"].append(datafield["name"])

        storage_file_path = os.path.join(
            dirs["symbol_info"], f"{settings.fork_name}.json"
        )
        GithubManager._write_json(storage_file_path, storage_data)

        return f"Files generated successfully in {base_dir}"

    @staticmethod
    def update_repository():
        settings = frappe.get_single("TV Data Settings")
        repo_dir = "tv_data_repo"
        token = get_decrypted_password(
            "TV Data Settings", "TV Data Settings", "github_token", False
        )
        remote_url = f"https://{token}:x-oauth-basic@github.com/{settings.fork_owner}/{settings.fork_name}.git"

        if not os.path.exists(repo_dir):
            subprocess.run(["git", "clone", remote_url, repo_dir], check=True)

        with GithubManager._change_dir(repo_dir):
            # Set up Git user configuration
            GithubManager._setup_git_config(settings)

            subprocess.run(["git", "pull"], check=True)
            subprocess.run(["cp", "-r", "../tv_data/.", "."], check=True)
            subprocess.run(
                ["git", "add", "."], check=True
            )  # Ensure commit message is set
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    (
                        settings.daily_commit_message
                        if settings.daily_commit_message
                        else "Planed Daily Updates"
                    ),
                ],
                check=True,
            )
            subprocess.run(["git", "push"], check=True)

        return "Repository updated successfully"

    @staticmethod
    def _setup_git_config(settings):
        # Set Git user configuration
        subprocess.run(
            ["git", "config", "user.name", settings.github_username], check=True
        )
        subprocess.run(
            ["git", "config", "user.email", settings.github_email], check=True
        )

    @staticmethod
    def _write_csv(file_path, data):
        # Ensure `data` is a list of dictionaries
        with open(file_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            for row in data:
                writer.writerow(
                    [
                        row.get("date_string", ""),
                        row.get("open", ""),
                        row.get("high", ""),
                        row.get("low", ""),
                        row.get("close", ""),
                        row.get("volume", ""),
                    ]
                )

    @staticmethod
    def _write_json(file_path, data):
        with open(file_path, "w") as json_file:
            json.dump(data, json_file, indent=4)

    @staticmethod
    def _change_dir(path):
        class ChangeDir:
            def __init__(self, path):
                self.path = path
                self.orig_path = os.getcwd()

            def __enter__(self):
                os.chdir(self.path)

            def __exit__(self, exc_type, exc_val, exc_tb):
                os.chdir(self.orig_path)

        return ChangeDir(path)

    @staticmethod
    def _parse_csv_string(csv_string):
        """Parse CSV string into a list of dictionaries."""
        import io

        csv_data = io.StringIO(csv_string)
        reader = csv.DictReader(
            csv_data,
            fieldnames=["date_string", "open", "high", "low", "close", "volume"],
        )
        return [row for row in reader]
