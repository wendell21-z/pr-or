import unittest
from data_models import get_default_data, Task, ScheduleData, Day, Die, Part, DiePart, PartDemand
from core_model import PunchingScheduler
from ortools.sat.python import cp_model


def create_feasible_data():
    """Create a simplified, feasible dataset for testing"""
    day_ids = ["2026-4-7", "2026-4-8", "2026-4-9"]
    day_map = {day_id: Day(day_id, 480, 0) for day_id in day_ids}  # 480 min = 28800 sec

    dies = [
        Die("Die_A", 50, 120),  # min_batch=50, 120 sec per hit
    ]
    die_map = {d.id: d for d in dies}

    parts = [
        Part("Part_1", 500, 5000),  # initial_stock=500, max_stock=5000
    ]
    part_map = {p.id: p for p in parts}

    die_parts = [
        DiePart("Die_A", "Part_1", 1),
    ]
    die_part_map = {(dp.die_id, dp.part_id): dp for dp in die_parts}

    # Demands that can be satisfied: 500 initial + production
    # Max production per day: 28800 sec / 120 sec = 240 hits
    # Over 3 days: 500 + 240*3 = 1220 total available
    demands = [
        ("2026-4-7", "Part_1", 300),
        ("2026-4-8", "Part_1", 400),
        ("2026-4-9", "Part_1", 500),
    ]
    part_demand_map = {
        (day_id, part_id): PartDemand(day_id, part_id, demand)
        for day_id, part_id, demand in demands
    }

    tasks = [Task("0", day_id, "Die_A") for day_id in day_ids]

    return ScheduleData(day_map, die_map, part_map, die_part_map, part_demand_map, tasks)


class TestSchedulerBasic(unittest.TestCase):
    """Test basic scheduling functionality"""

    def setUp(self):
        self.data = create_feasible_data()
        self.scheduler = PunchingScheduler(self.data)

    def test_solve_feasible(self):
        """Test that the scheduler can find a feasible solution"""
        solver, status, reasons = self.scheduler.solve()
        
        self.assertIn(status, [cp_model.OPTIMAL, cp_model.FEASIBLE], 
                     f"Expected feasible solution, got {solver.StatusName(status)}. Reasons: {reasons}")

    def test_all_days_have_tasks(self):
        """Test that all days have scheduled tasks"""
        solver, status, _ = self.scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for day_id in self.scheduler._sorted_days:
                tasks = self.scheduler._tasks_by_day.get(day_id, [])
                has_active = False
                for task in tasks:
                    if solver.Value(task.quantity) > 0:
                        has_active = True
                        break
                self.assertTrue(has_active, f"No active tasks scheduled for {day_id}")

    def test_inventory_non_negative(self):
        """Test that inventory never goes negative"""
        solver, status, _ = self.scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for (part_id, day_id), stock_var in self.scheduler.part_stock.items():
                stock = solver.Value(stock_var)
                self.assertGreaterEqual(stock, 0, 
                    f"Negative inventory for {part_id} on {day_id}: {stock}")

    def test_inventory_within_limits(self):
        """Test that inventory doesn't exceed maximum capacity"""
        solver, status, _ = self.scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for (part_id, day_id), stock_var in self.scheduler.part_stock.items():
                stock = solver.Value(stock_var)
                max_stock = self.data.part_map[part_id].max_stock
                self.assertLessEqual(stock, max_stock,
                    f"Inventory exceeds max for {part_id} on {day_id}: {stock}/{max_stock}")

    def test_production_time_within_limits(self):
        """Test that daily production time is within working hours"""
        solver, status, _ = self.scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for day_id in self.scheduler._sorted_days:
                day = self.data.day_map[day_id]
                work_sec = (day.working_time - day.out_minutes) * 60
                tasks = self.scheduler._tasks_by_day.get(day_id, [])
                
                total_time = sum(solver.Value(task.duration) for task in tasks)
                self.assertLessEqual(total_time, work_sec,
                    f"Production time exceeds limit on {day_id}: {total_time}/{work_sec}")


class TestSchedulerWithPins(unittest.TestCase):
    """Test scheduling with pinned values"""

    def setUp(self):
        self.data = create_feasible_data()

    def test_pinned_quantity_respected(self):
        """Test that pinned quantity is respected in the solution"""
        # Pin the first task's quantity
        task_to_pin = self.data.tasks[0]
        task_to_pin.pinned_quantity = 200
        
        scheduler = PunchingScheduler(self.data)
        solver, status, _ = scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            qty = solver.Value(task_to_pin.quantity)
            self.assertEqual(qty, 200, 
                f"Pinned quantity not respected: expected 200, got {qty}")

    def test_pinned_order_respected(self):
        """Test that pinned order results in active task"""
        # Pin the first task's order
        task_to_pin = self.data.tasks[0]
        task_to_pin.pinned_order = 1
        
        scheduler = PunchingScheduler(self.data)
        solver, status, _ = scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            active = solver.Value(task_to_pin.active)
            self.assertEqual(active, 1, 
                "Task with pinned order should be active")

    def test_multiple_pinned_quantities(self):
        """Test multiple pinned quantities are all respected"""
        pinned_tasks = self.data.tasks[:3]
        for i, task in enumerate(pinned_tasks):
            task.pinned_quantity = 150 + (i * 10)
        
        scheduler = PunchingScheduler(self.data)
        solver, status, _ = scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for i, task in enumerate(pinned_tasks):
                expected_qty = 150 + (i * 10)
                actual_qty = solver.Value(task.quantity)
                self.assertEqual(actual_qty, expected_qty,
                    f"Task {task.id}: expected pinned qty {expected_qty}, got {actual_qty}")

    def test_no_pins_still_works(self):
        """Test that scheduler works without any pins"""
        scheduler = PunchingScheduler(self.data)
        solver, status, _ = scheduler.solve()
        
        self.assertIn(status, [cp_model.OPTIMAL, cp_model.FEASIBLE],
                     f"Expected feasible solution without pins, got {solver.StatusName(status)}")


class TestSchedulerConstraints(unittest.TestCase):
    """Test specific constraint behaviors"""

    def setUp(self):
        self.data = create_feasible_data()
        self.scheduler = PunchingScheduler(self.data)

    def test_minimum_batch_size(self):
        """Test that production quantity respects minimum batch size"""
        solver, status, _ = self.scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for task in self.data.tasks:
                qty = solver.Value(task.quantity)
                if qty > 0:
                    min_batch = self.data.die_map[task.die_id].min_batch
                    self.assertGreaterEqual(qty, min_batch,
                        f"Task {task.id}: quantity {qty} below min batch {min_batch}")

    def test_inactive_tasks_have_zero_quantity(self):
        """Test that inactive tasks have zero quantity"""
        solver, status, _ = self.scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for task in self.data.tasks:
                active = solver.Value(task.active)
                qty = solver.Value(task.quantity)
                if not active:
                    self.assertEqual(qty, 0,
                        f"Inactive task {task.id} should have 0 quantity, got {qty}")

    def test_task_duration_calculation(self):
        """Test that duration = quantity * production_time"""
        solver, status, _ = self.scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for task in self.data.tasks:
                if solver.Value(task.quantity) > 0:
                    qty = solver.Value(task.quantity)
                    duration = solver.Value(task.duration)
                    prod_time = self.data.die_map[task.die_id].production_time
                    expected_duration = qty * prod_time
                    self.assertEqual(duration, expected_duration,
                        f"Task {task.id}: duration {duration} != qty {qty} * prod_time {prod_time}")

    def test_no_task_overlap(self):
        """Test that tasks on the same day don't overlap"""
        solver, status, _ = self.scheduler.solve()
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for day_id in self.scheduler._sorted_days:
                tasks = self.scheduler._tasks_by_day.get(day_id, [])
                active_tasks = []
                for task in tasks:
                    if solver.Value(task.active):
                        start = solver.Value(task.start)
                        duration = solver.Value(task.duration)
                        end = solver.Value(task.end)
                        active_tasks.append((task.id, start, end))
                
                # Sort by start time and check no overlaps
                active_tasks.sort(key=lambda x: x[1])
                for i in range(len(active_tasks) - 1):
                    _, _, end_time = active_tasks[i]
                    next_id, next_start, _ = active_tasks[i + 1]
                    self.assertLessEqual(end_time, next_start,
                        f"Task overlap on {day_id}: task {active_tasks[i][0]} ends at {end_time}, "
                        f"but task {next_id} starts at {next_start}")


class TestSchedulerEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""

    def test_empty_task_list(self):
        """Test scheduler handles empty task list gracefully"""
        data = create_feasible_data()
        data.tasks = []
        scheduler = PunchingScheduler(data)
        
        # Should not raise an exception
        try:
            solver, status, reasons = scheduler.solve(log_search=False)
        except Exception as e:
            self.fail(f"Solve raised exception with empty tasks: {e}")

    def test_single_task(self):
        """Test scheduler with a single day of multiple tasks"""
        data = create_feasible_data()
        # Add more dies to make 80% minimum work constraint satisfiable
        data.die_map = {
            "Die_A": Die("Die_A", 50, 120),
            "Die_B": Die("Die_B", 50, 120),
            "Die_C": Die("Die_C", 50, 120),
        }
        data.tasks = [
            Task("0", "2026-4-7", "Die_A"),
            Task("1", "2026-4-7", "Die_B"),
            Task("2", "2026-4-7", "Die_C"),
        ]
        # Adjust demand to be feasible
        data.part_demand_map = {
            ("2026-4-7", "Part_1"): PartDemand("2026-4-7", "Part_1", 200),
        }
        # Remove demands for other days
        data.day_map = {"2026-4-7": data.day_map["2026-4-7"]}
        
        scheduler = PunchingScheduler(data)
        solver, status, reasons = scheduler.solve(log_search=False)
        
        self.assertIn(status, [cp_model.OPTIMAL, cp_model.FEASIBLE],
                     f"Expected feasible solution, got {solver.StatusName(status)}. Reasons: {reasons}")

    def test_pin_value_range(self):
        """Test that pinning values within valid range works"""
        data = create_feasible_data()
        # Add more dies to make 80% minimum work constraint satisfiable
        data.die_map = {
            "Die_A": Die("Die_A", 50, 120),
            "Die_B": Die("Die_B", 50, 120),
            "Die_C": Die("Die_C", 50, 120),
        }
        data.tasks = [
            Task("0", "2026-4-7", "Die_A"),
            Task("1", "2026-4-7", "Die_B"),
            Task("2", "2026-4-7", "Die_C"),
        ]
        # Remove demands for other days
        data.day_map = {"2026-4-7": data.day_map["2026-4-7"]}
        data.part_demand_map = {
            ("2026-4-7", "Part_1"): PartDemand("2026-4-7", "Part_1", 200),
        }
        task = data.tasks[0]
        
        # Pin to a reasonable quantity
        task.pinned_quantity = 100
        task.pinned_order = 1
        
        scheduler = PunchingScheduler(data)
        solver, status, reasons = scheduler.solve(log_search=False)
        
        self.assertIn(status, [cp_model.OPTIMAL, cp_model.FEASIBLE],
                     f"Pinned values in range should be feasible, got {solver.StatusName(status)}. Reasons: {reasons}")


if __name__ == '__main__':
    unittest.main()
