from datetime import datetime, timedelta
from .github import GithubManager


class CycleManager:
    def __init__(self, cycle_begin_time, daily_updates, cycle_duration):
        self.cycle_begin_time = cycle_begin_time
        self.daily_updates = daily_updates
        self.cycle_duration = cycle_duration

    def get_cycles(self):
        now = datetime.now()
        cycle_begin_datetime = datetime.combine(now.date(), self.cycle_begin_time)
        current_time = now.time()

        past_cycles = []
        future_cycles = []

        for i in range(self.daily_updates):
            cycle_time = (cycle_begin_datetime + i * self.cycle_duration).time()

            cycle_info = {
                "index": i + 1,
                "time": cycle_time.strftime("%H:%M:%S"),
            }

            if cycle_time < current_time:
                past_cycles.append(cycle_info)
            elif cycle_time > current_time:
                future_cycles.append(cycle_info)
            # If cycle_time == current_time, we skip it as it's neither past nor future

        # If no future cycles, select the first one
        if not future_cycles:
            future_cycles.append(past_cycles.pop(0))

        return {"past": past_cycles, "future": future_cycles}


# Example usage
# cycle_begin_time = datetime.strptime("08:00:00", "%H:%M:%S").time()
# daily_updates = 4
# cycle_duration = timedelta(hours=6)

# manager = CycleManager(cycle_begin_time, daily_updates, cycle_duration)
# cycles = manager.get_cycles()
# print(cycles)
