import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt
from typing import List, Union, Optional, Any
from datetime import datetime, timedelta
from tv_data.cycle import CycleManager


class TVDataSettingsDefaults:
    def __init__(self, defaults_table: List[Document]) -> None:
        for default in defaults_table:
            setattr(
                self,
                default.def_name,
                self._convert_value(default.def_value, default.def_type),
            )

    @staticmethod
    def _convert_value(value: str, value_type: str) -> Union[float, int, str, bool]:
        converters = {
            "Float": flt,
            "Int": cint,
            "Check": lambda v: cint(v) == 1,
        }
        return converters.get(value_type, lambda x: x)(value)

    def __getattr__(self, name):
        return None


class TVDataSettings(Document):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._defaults: Optional[TVDataSettingsDefaults] = None
        self._cycle_manager: Optional[CycleManager] = None

    @property
    def defaults(self):
        if self._defaults is None:
            self._defaults = TVDataSettingsDefaults(
                self.tv_data_settings_defaults_table
            )
        return self._defaults

    @property
    def cycle_manager(self):
        if self._cycle_manager is None:
            self._cycle_manager = CycleManager(
                timeframe=self.timeframe,
                daily_updates=self.daily_updates,
                scheduler_pre_runtime=self.scheduler_pre_runtime,
            )
        return self._cycle_manager

    @property
    def fork_name(self):
        return (
            f"seed_{self.fork_owner.lower()}_{self.fork_data_type_name.lower()}"
            if self.fork_owner and self.fork_data_type_name
            else None
        )

    @property
    def repo_url(self):
        return (
            f"{self.github_url}/{self.repo_owner}/{self.repo_name}.git"
            if self.repo_owner and self.repo_name
            else None
        )

    @property
    def fork_url(self):
        return (
            f"{self.github_url}/{self.fork_owner}/{self.fork_name}.git"
            if self.repo_owner and self.repo_name and self.fork_name
            else None
        )

    @property
    def cycle_duration(self) -> int:
        return int(self.cycle_manager.cycle_duration.total_seconds())

    @property
    def cycle_duration_datetime(self) -> timedelta:
        return self.cycle_manager.cycle_duration

    @property
    def next_cycle(self) -> datetime:
        next_cycle = self.cycle_manager.get_next_cycle()
        return next_cycle["datetime"] if next_cycle else None

    @property
    def last_cycle(self) -> datetime:
        prev_cycle = self.cycle_manager.get_previous_cycle()
        return prev_cycle["datetime"] if prev_cycle else None

    def validate(self):
        for attr in ["fork_data_type_name", "repo_owner", "repo_name", "fork_owner"]:
            if getattr(self, attr):
                setattr(self, attr, getattr(self, attr).strip())

    def convert_decimal_to_duration(self, decimal_hours):
        hours = int(decimal_hours)
        minutes = int((decimal_hours - hours) * 60)
        seconds = int(((decimal_hours - hours) * 60 - minutes) * 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def get_cycles(self):
        cycle_manager = CycleManager(
            timeframe=self.timeframe,
            daily_updates=self.daily_updates,
            scheduler_pre_runtime=self.scheduler_pre_runtime,
        )
        return cycle_manager.get_cycles()

    @frappe.whitelist()
    def get_cycle_timeline_html(self):
        cycles = self.get_cycles()
        context = {
            "cycles": cycles["past"] + cycles["future"],
            "past_cycles": cycles["past"],
            "future_cycles": cycles["future"],
        }

        return frappe.render_template(
            "templates/includes/timeline_template.html", context
        )

    @frappe.whitelist()
    def get_horizontal_timeline_html(self):
        cycles = self.get_cycles()
        context = {
            "cycles": cycles["past"] + cycles["future"],
            "current_cycle_index": len(cycles["past"]),
        }

        return frappe.render_template(
            "templates/includes/timeline_horizontal_template.html", context
        )


def dev_log(message: str) -> None:
    if frappe.flags.in_test:
        print(message)


@frappe.whitelist()
def _get_cycle_timeline_html():
    return frappe.get_doc("TV Data Settings").get_cycle_timeline_html()


@frappe.whitelist()
def _get_horizontal_timeline_html():
    return frappe.get_doc("TV Data Settings").get_horizontal_timeline_html()
