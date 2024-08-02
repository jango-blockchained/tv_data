import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt
from typing import List, Union, Optional, Any
from datetime import datetime, timedelta
import time


class TVDataSettingsDefaults:
    def __init__(self, defaults_table: List[Document]) -> None:
        """
        Initialize the TVDataSettingsDefaults object.

        Args:
            defaults_table (List[Document]): A list of documents representing the defaults table.

        Returns:
            None
        """
        for default in defaults_table:
            value = self._convert_value(default.def_value, default.def_type)
            setattr(self, default.def_name, value)

    def _convert_value(self, value: str, value_type: str) -> Union[float, int, str]:
        """
        Convert the given value to the specified value type.

        Args:
            value (str): The value to be converted.
            value_type (str): The type to which the value should be converted.
                Possible values are "Float", "Int", "Check", or "Data".

        Returns:
            Union[float, int, str]: The converted value.
        """
        if value_type == "Float":
            return flt(value)
        elif value_type == "Int":
            return cint(value)
        elif value_type == "Check":
            return cint(value) == 1
        else:  # "Data" or any other type
            return value

    def __getattr__(self, name):
        return None


class TVDataSettings(Document):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the TVDataSettings object.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None
        """
        super().__init__(*args, **kwargs)
        self._defaults: Optional[TVDataSettingsDefaults] = None
        # self.timeframe: str = '1d'
        # self.daily_updates: int = 5
        # self.cycle_begin: str = '00:00:00'
        # self.scheduler_pre_runtime: timedelta = timedelta(minutes=5)

    @property
    def defaults(self):
        if self._defaults is None:
            self._defaults = TVDataSettingsDefaults(
                self.tv_data_settings_defaults_table
            )
        return self._defaults

    @staticmethod
    def timeframe_to_timedelta(timeframe: str) -> timedelta:
        """
        Convert the given timeframe string into a timedelta object.

        Args:
            timeframe (str): The timeframe string to be converted.
                Possible values are in the format of '{int}{unit}', where
                {int} is the number of time units and {unit} is one of
                'd', 'h', 'm', 's'.

        Returns:
            timedelta: The timedelta object representing the given timeframe.
        """
        time_units = {
            "d": timedelta(days=1),
            "h": timedelta(hours=1),
            "m": timedelta(minutes=1),
            "s": timedelta(seconds=1),
        }
        try:
            num, unit = timeframe[:-1], timeframe[-1]
            return time_units[unit] * int(num)
        except (KeyError, ValueError):
            raise ValueError(f"Invalid timeframe: {timeframe}")

    @property
    def fork_name(self):
        if self.fork_owner and self.fork_data_type_name:
            return f"seed_{self.fork_owner.lower()}_{self.fork_data_type_name.lower()}"
        return None

    @property
    def repo_url(self):
        if self.repo_owner and self.repo_name:
            return f"{self.github_url}/{self.repo_owner}/{self.repo_name}.git"
        return None

    @property
    def fork_url(self):
        if self.repo_owner and self.repo_name and self.fork_name:
            return f"{self.github_url}/{self.fork_owner}/{self.fork_name}.git"
        return None

    @property
    def cycle_duration(self) -> timedelta:
        """Returns the duration of each cycle."""
        return timedelta(hours=24 / self.daily_updates)  # Duration of each cycle

    @property
    def cycle_begin_time(self) -> datetime:
        """Returns the cycle begin time as a time object."""
        return datetime.strptime(self.cycle_begin, "%H:%M:%S").time()

    @property
    def next_cycle(self) -> datetime:
        """Calculates the datetime for the next cycle."""
        now = datetime.now()
        cycle_begin_datetime = datetime.combine(now.date(), self.cycle_begin_time)

        # Calculate next cycle time from cycle begin, interval, and pre-runtime (sec)
        while cycle_begin_datetime < now:
            cycle_begin_datetime += self.cycle_duration

        return cycle_begin_datetime - self.timeframe_to_timedelta(
            self.scheduler_pre_runtime
        )

    @property
    def last_cycle(self) -> datetime:
        """Calculates the datetime for the last cycle."""
        now = datetime.now()
        cycle_begin_datetime = datetime.combine(now.date(), self.cycle_begin_time)

        # Calculate last cycle time from cycle begin and interval
        while cycle_begin_datetime < now:
            last_cycle_time = cycle_begin_datetime
            cycle_begin_datetime += self.cycle_duration

        return cycle_begin_datetime - self.scheduler_pre_runtime

    # Example usage
    # scheduler = Scheduler()
    # print("Cycle Interval:", scheduler.cycle_duration)
    # print("Next Cycle:", scheduler.next_cycle)
    # print("Last Cycle:", scheduler.last_cycle)

    def validate(self):
        if self.fork_data_type_name:
            self.fork_data_type_name = self.fork_data_type_name.strip()
        if self.repo_owner:
            self.repo_owner = self.repo_owner.strip()
        if self.repo_name:
            self.repo_name = self.repo_name.strip()
        if self.fork_owner:
            self.fork_owner = self.fork_owner.strip()
        if self.fork_data_type_name:
            self.fork_data_type_name = self.fork_data_type_name.strip()
