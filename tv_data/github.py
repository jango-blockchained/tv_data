import os
import csv
import json
import subprocess
import logging
from contextlib import contextmanager
from typing import Dict, List
from datetime import datetime

import frappe
from frappe import _
from frappe.utils.password import get_decrypted_password


class GithubManager:
    @staticmethod
    def setup_logging(cycle_name):
        log_dir = "tv_data_logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{cycle_name}_{timestamp}.log")

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        return log_file

    @staticmethod
    def run_with_logging(cycle_name, func, *args, **kwargs):
        log_file = GithubManager.setup_logging(cycle_name)

        try:
            result = func(*args, **kwargs)
            logging.info(f"Operation completed successfully: {result}")
            return result
        except Exception as e:
            logging.error(f"Error occurred: {str(e)}", exc_info=True)
            raise
        finally:
            logging.info(f"Log file created: {log_file}")

    @staticmethod
    def generate_files():
        def _generate_files():
            settings = frappe.get_single("TV Data Settings")
            base_dir = "tv_data"
            dirs = {
                "data": os.path.join(base_dir, "data"),
                "symbol_info": os.path.join(base_dir, "symbol_info"),
                "github": os.path.join(base_dir, ".github"),
            }

            logging.info("Clearing directories...")
            GithubManager._clear_directories(dirs)
            logging.info("Creating directories...")
            GithubManager._create_directories(dirs)

            logging.info("Processing datafields...")
            storage_data = GithubManager._process_datafields(dirs["data"])

            storage_file_path = os.path.join(
                dirs["symbol_info"], f"{settings.fork_name}.json"
            )
            logging.info(f"Writing JSON to {storage_file_path}...")
            GithubManager._write_json(storage_file_path, storage_data)

            return f"Files generated successfully in {base_dir}"

        return GithubManager.run_with_logging("generate_files", _generate_files)

    @staticmethod
    def update_repository():
        def _update_repository():
            settings = frappe.get_single("TV Data Settings")
            repo_dir = "tv_data_repo"
            token = get_decrypted_password(
                "TV Data Settings", "TV Data Settings", "github_token", False
            )
            remote_url = f"https://{token}:x-oauth-basic@github.com/{settings.fork_owner}/{settings.fork_name}.git"

            if not os.path.exists(repo_dir):
                logging.info(f"Cloning repository to {repo_dir}...")
                subprocess.run(
                    ["git", "clone", remote_url, repo_dir],
                    check=True,
                    capture_output=True,
                    text=True,
                )

            with GithubManager._change_dir(repo_dir):
                logging.info("Setting up git config...")
                GithubManager._setup_git_config(settings)
                logging.info("Updating repository...")
                GithubManager._update_repo(settings)

            return "Repository updated successfully"

        return GithubManager.run_with_logging("update_repository", _update_repository)

    @staticmethod
    def _clear_directories(dirs: Dict[str, str]):
        for directory in dirs.values():
            if os.path.exists(directory):
                for file_name in os.listdir(directory):
                    file_path = os.path.join(directory, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

    @staticmethod
    def _create_directories(dirs: Dict[str, str]):
        for directory in dirs.values():
            os.makedirs(directory, exist_ok=True)

    @staticmethod
    def _process_datafields(data_dir: str) -> Dict[str, List[str]]:
        storage_data = {"description": [], "pricescale": [], "symbol": []}
        datafields = frappe.get_all("Datafield", fields=["name", "key", "scale"])

        for datafield in datafields:
            csv_file_path = os.path.join(data_dir, f"{datafield['name']}.csv")

            series_data = frappe.get_all(
                "Datafield Series",
                filters={"parent": datafield["name"]},
                fields=["date_string", "open", "high", "low", "close", "volume"],
            )

            GithubManager._write_csv(csv_file_path, series_data)
            storage_data["description"].append(datafield["key"])
            storage_data["pricescale"].append(datafield["scale"])
            storage_data["symbol"].append(datafield["name"])

        return storage_data

    @staticmethod
    def _setup_git_config(settings):
        subprocess.run(
            ["git", "config", "user.name", settings.github_username],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.email", settings.github_email],
            check=True,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _update_repo(settings):
        try:
            subprocess.run(["git", "pull"], check=True, capture_output=True, text=True)
            subprocess.run(
                ["cp", "-r", "../tv_data/.", "."],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "add", "."], check=True, capture_output=True, text=True
            )
            commit_message = settings.daily_commit_message or "Planned Daily Updates"

            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True,
                capture_output=True,
                text=True,
            )

            frappe.logger().info(f"Git commit output: {result.stdout}")

            subprocess.run(["git", "push"], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            error_msg = f"Git operation failed: {e.cmd}. Error: {e.stderr}"
            frappe.log_error(error_msg, _("GitHub Manager Error"))
            raise

    @staticmethod
    def _write_csv(file_path: str, data: List[Dict]):
        try:
            with open(file_path, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    ["date_string", "open", "high", "low", "close", "volume"]
                )
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
        except IOError as e:
            frappe.log_error(
                f"Error writing CSV file {file_path}: {str(e)}",
                _("GitHub Manager Error"),
            )
            raise

    @staticmethod
    def _write_json(file_path: str, data: Dict):
        try:
            with open(file_path, "w") as json_file:
                json.dump(data, json_file, indent=4)
        except IOError as e:
            frappe.log_error(
                f"Error writing JSON file {file_path}: {str(e)}",
                _("GitHub Manager Error"),
            )
            raise

    @staticmethod
    @contextmanager
    def _change_dir(path: str):
        orig_path = os.getcwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(orig_path)


@frappe.whitelist()
def _generate_files():
    try:
        return GithubManager.generate_files()
    except Exception as e:
        frappe.log_error(
            f"Error in generate_files: {str(e)}", _("GitHub Manager Error")
        )
        frappe.msgprint(
            _("Failed to generate files. Please check the error log for details.")
        )
        raise


@frappe.whitelist()
def _update_repository():
    try:
        return GithubManager.update_repository()
    except Exception as e:
        frappe.log_error(
            f"Error in update_repository: {str(e)}", _("GitHub Manager Error")
        )
        frappe.msgprint(
            _("Failed to update repository. Please check the error log for details.")
        )
        raise
