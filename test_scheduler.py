from pathlib import Path
import unittest

from scheduler import SCHEDULER_ORDER, parse_input_file, run_scheduler


INPUT_PATH = Path(__file__).with_name("input.txt")
EXPECTED_PASSENGER_COUNT = 50
EXPECTED_TOTAL_SERVICE_TIME = 379


class SchedulerInputTests(unittest.TestCase):
    def test_input_file_matches_expected_workload(self):
        passengers = parse_input_file(INPUT_PATH)

        self.assertEqual(len(passengers), EXPECTED_PASSENGER_COUNT)
        self.assertEqual(
            sum(passenger.service_time for passenger in passengers),
            EXPECTED_TOTAL_SERVICE_TIME,
            "input.txt service_time total must match the required workload total.",
        )

    def test_all_schedulers_are_runnable_and_complete_all_passengers(self):
        for scheduler_name in SCHEDULER_ORDER:
            with self.subTest(scheduler=scheduler_name):
                result = run_scheduler(parse_input_file(INPUT_PATH), scheduler_name)

                self.assertEqual(len(result.passengers), EXPECTED_PASSENGER_COUNT)
                self.assertEqual(len(result.completed_passengers), EXPECTED_PASSENGER_COUNT)

    def test_all_schedulers_preserve_required_service_time_total(self):
        for scheduler_name in SCHEDULER_ORDER:
            with self.subTest(scheduler=scheduler_name):
                result = run_scheduler(parse_input_file(INPUT_PATH), scheduler_name)

                self.assertEqual(
                    sum(passenger.service_time for passenger in result.passengers),
                    EXPECTED_TOTAL_SERVICE_TIME,
                    "completed passenger service_time total must match input workload total.",
                )

    def test_all_schedulers_record_valid_completion_and_turnaround_times(self):
        for scheduler_name in SCHEDULER_ORDER:
            with self.subTest(scheduler=scheduler_name):
                result = run_scheduler(parse_input_file(INPUT_PATH), scheduler_name)

                for passenger in result.passengers:
                    self.assertIsNotNone(passenger.service_start_time)
                    self.assertIsNotNone(passenger.completion_time)
                    self.assertIsNotNone(passenger.turnaround_time)
                    self.assertEqual(
                        passenger.completion_time,
                        passenger.service_start_time + passenger.service_time,
                    )
                    self.assertEqual(
                        passenger.turnaround_time,
                        passenger.completion_time - passenger.arrival_time,
                    )


if __name__ == "__main__":
    unittest.main()
