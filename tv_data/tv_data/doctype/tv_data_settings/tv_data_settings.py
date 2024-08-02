import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt
from typing import List, Union, Optional, Any
from datetime import datetime, timedelta
from functools import lru_cache
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

    @property
    def defaults(self):
        if self._defaults is None:
            self._defaults = TVDataSettingsDefaults(
                self.tv_data_settings_defaults_table
            )
        return self._defaults

    @staticmethod
    @lru_cache(maxsize=None)
    def timeframe_to_timedelta(timeframe: str) -> timedelta:
        time_units = {"d": 24 * 60 * 60, "h": 60 * 60, "m": 60, "s": 1}
        try:
            num, unit = int(timeframe[:-1]), timeframe[-1]
            return timedelta(seconds=time_units[unit] * num)
        except (KeyError, ValueError):
            raise ValueError(f"Invalid timeframe: {timeframe}")

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
    @lru_cache(maxsize=1)
    def cycle_duration(self) -> timedelta:
        return timedelta(hours=(24 / self.daily_updates))

    @property
    @lru_cache(maxsize=1)
    def cycle_begin_time(self) -> datetime.time:
        return datetime.strptime(self.cycle_begin, "%H:%M:%S").time()

    @property
    def next_cycle(self) -> datetime:
        now = datetime.now()
        cycle_begin_datetime = datetime.combine(now.date(), self.cycle_begin_time)
        while cycle_begin_datetime <= now:
            cycle_begin_datetime += self.cycle_duration
        return cycle_begin_datetime - timedelta(seconds=int(self.scheduler_pre_runtime))

    @property
    def last_cycle(self) -> datetime:
        now = datetime.now()
        cycle_begin_datetime = datetime.combine(now.date(), self.cycle_begin_time)
        last_cycle_time = None
        while cycle_begin_datetime <= now:
            last_cycle_time = cycle_begin_datetime
            cycle_begin_datetime += self.cycle_duration
        if last_cycle_time is None:
            raise ValueError("last_cycle_time is not set")
        return last_cycle_time - timedelta(seconds=int(self.scheduler_pre_runtime))

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
        # Use CycleManager to get cycle data
        cycle_manager = CycleManager(
            cycle_begin_time=self.cycle_begin_time,
            daily_updates=self.daily_updates,
            cycle_duration=self.cycle_duration,
        )
        return cycle_manager.get_cycles()

    @frappe.whitelist()
    def get_cycle_timeline_html(self):
        cycles = self.get_cycles()
        context = {"past_cycles": cycles["past"], "future_cycles": cycles["future"]}

        return frappe.render_template(
            "templates/includes/timeline_template_2.html", context
        )

    @frappe.whitelist()
    def get_horizontal_timeline_html(self):
        cycles = self.get_cycles()
        current_time_display = datetime.now().time().strftime("%H:%M:%S")
        context = {
            "cycles": cycles["past"] + cycles["future"],
            "current_cycle_index": len(cycles["past"]),
            "current_time_display": current_time_display,
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
