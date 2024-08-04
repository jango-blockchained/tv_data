from datetime import datetime, timedelta
import re


class CycleManager:
    def __init__(self, timeframe, daily_updates, scheduler_pre_runtime):
        self.timeframe = self._parse_timeframe(timeframe)
        self.daily_updates = daily_updates
        self.cycle_duration = self.timeframe / daily_updates
        self.scheduler_pre_runtime = timedelta(seconds=int(scheduler_pre_runtime))

    def _parse_timeframe(self, timeframe):
        if isinstance(timeframe, (int, float)):
            return timedelta(seconds=int(timeframe))
        elif isinstance(timeframe, str):
            try:
                return timedelta(seconds=int(timeframe))
            except ValueError:
                pass

            match = re.match(r"^(\d+)([dhm])$", timeframe)
            if match:
                value, unit = int(match.group(1)), match.group(2)
                if unit == "d":
                    return timedelta(days=value)
                elif unit == "h":
                    return timedelta(hours=value)
                elif unit == "m":
                    return timedelta(minutes=value)

            raise ValueError(f"Invalid timeframe format: {timeframe}")
        else:
            raise ValueError(f"Invalid timeframe type: {type(timeframe)}")

    def get_cycles(self):
        now = datetime.now()
        timeframe_start = self._get_timeframe_start(now)
        current_time = now.time()

        past_cycles, future_cycles = self._compute_cycles(timeframe_start, current_time)

        # Ensure there is at least one future cycle if all cycles are past
        if not future_cycles and past_cycles:
            future_cycles.append(past_cycles.pop(0))

        return {"past": past_cycles, "future": future_cycles}

    def _compute_cycles(self, timeframe_start, current_time):
        past_cycles = []
        future_cycles = []

        for i in range(self.daily_updates):
            cycle_time = (
                timeframe_start + i * self.cycle_duration - self.scheduler_pre_runtime
            ).time()

            cycle_info = {
                "index": i + 1,
                "time": cycle_time.strftime("%H:%M:%S.%f"),
            }

            if cycle_time < current_time:
                past_cycles.append(cycle_info)
            elif cycle_time > current_time:
                future_cycles.append(cycle_info)

        return past_cycles, future_cycles

    def _get_timeframe_start(self, now):
        # Calculate the start of the timeframe, aligned with the beginning of the day
        midnight = datetime.combine(now.date(), datetime.min.time())
        timeframe_start = (
            midnight + ((now - midnight) // self.timeframe) * self.timeframe
        )
        return timeframe_start

    def get_next_cycle(self):
        now = datetime.now()
        timeframe_start = self._get_timeframe_start(now)

        # Calculate the time of the next cycle
        for i in range(self.daily_updates):
            next_cycle_time = timeframe_start + i * self.cycle_duration
            if next_cycle_time > now:
                return {
                    "index": i + 1,
                    "time": next_cycle_time.time().strftime("%H:%M:%S.%f"),
                    "datetime": next_cycle_time,
                }

        return None

    def get_previous_cycle(self):
        now = datetime.now()
        timeframe_start = self._get_timeframe_start(now)

        # Calculate the time of the previous cycle
        for i in range(self.daily_updates - 1, -1, -1):
            prev_cycle_time = timeframe_start + i * self.cycle_duration
            if prev_cycle_time < now:
                return {
                    "index": i + 1,
                    "time": prev_cycle_time.time().strftime("%H:%M:%S.%f"),
                    "datetime": prev_cycle_time,
                }

        return None
