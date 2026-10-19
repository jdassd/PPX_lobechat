import unittest

from api.system.window_geometry import (
    calculate_window_geometry,
    logicalize_native_window_value,
    logicalize_saved_window_state,
    migrate_display_geometry,
)


class WindowGeometryTests(unittest.TestCase):
    def setUp(self):
        self.workareas = [
            {'x': 0, 'y': 0, 'width': 1920, 'height': 1040, 'primary': True},
            {'x': -1600, 'y': 0, 'width': 1600, 'height': 900, 'primary': False},
        ]

    def test_first_open_uses_standard_size_capped_by_primary_work_area(self):
        geometry = calculate_window_geometry(self.workareas)

        self.assertEqual(geometry['width'], 1280)
        self.assertEqual(geometry['height'], 800)
        self.assertEqual(geometry['x'], 320)
        self.assertEqual(geometry['y'], 120)
        self.assertEqual(geometry['min_size'], (640, 400))

    def test_first_open_caps_standard_size_at_ninety_percent_of_work_area(self):
        geometry = calculate_window_geometry(
            [{'x': 0, 'y': 0, 'width': 1440, 'height': 852, 'primary': True}],
        )

        self.assertEqual(geometry['width'], 1280)
        self.assertEqual(geometry['height'], 766)
        self.assertEqual(geometry['x'], 80)
        self.assertEqual(geometry['y'], 43)

    def test_saved_window_is_kept_on_matching_monitor_and_clamped(self):
        geometry = calculate_window_geometry(
            self.workareas,
            saved_state={'width': 4000, 'height': 1200, 'x': -3990, 'y': 0},
        )

        self.assertEqual(geometry['width'], 1600)
        self.assertEqual(geometry['height'], 900)
        self.assertEqual(geometry['x'], -1600)
        self.assertEqual(geometry['y'], 0)
        self.assertEqual(geometry['min_size'], (640, 400))

    def test_off_screen_saved_window_moves_to_primary(self):
        geometry = calculate_window_geometry(
            self.workareas,
            saved_state={'width': 1000, 'height': 700, 'x': 5000, 'y': 4000},
        )

        self.assertEqual(geometry['width'], 1000)
        self.assertEqual(geometry['height'], 700)
        self.assertEqual(geometry['x'], 460)
        self.assertEqual(geometry['y'], 170)

    def test_minimum_size_is_limited_by_small_work_area(self):
        geometry = calculate_window_geometry(
            [{'x': 0, 'y': 0, 'width': 500, 'height': 300, 'primary': True}],
            initial_size=(1280, 800),
            min_size=(640, 400),
        )

        self.assertEqual(geometry['width'], 500)
        self.assertEqual(geometry['height'], 300)
        self.assertEqual(geometry['min_size'], (500, 300))

    def test_saved_window_is_fully_clamped_inside_work_area(self):
        geometry = calculate_window_geometry(
            self.workareas,
            saved_state={'width': 900, 'height': 600, 'x': -2000, 'y': -200},
        )

        self.assertEqual(geometry['x'], -1600)
        self.assertEqual(geometry['y'], 0)
        self.assertEqual(geometry['width'], 900)
        self.assertEqual(geometry['height'], 600)

    def test_legacy_200_percent_window_state_is_converted_to_startup_units(self):
        state = logicalize_saved_window_state(
            {'schemaVersion': 1, 'width': 1868, 'height': 1220, 'x': 480, 'y': 170},
            scale_factor=2,
        )

        self.assertEqual(state, {'schemaVersion': 1, 'width': 934, 'height': 610, 'x': 240, 'y': 85})
        self.assertEqual(logicalize_native_window_value(1868, 2), 934)

    def test_current_schema_window_state_is_already_in_startup_units(self):
        state = logicalize_saved_window_state(
            {'schemaVersion': 2, 'width': 934, 'height': 610, 'x': 240, 'y': 85},
            scale_factor=2,
        )

        self.assertEqual(state['width'], 934)
        self.assertEqual(state['height'], 610)
        self.assertEqual(state['x'], 240)
        self.assertEqual(state['y'], 85)

    def test_schema_three_compensation_migrates_once_to_actual_displayed_size(self):
        geometry = {'width': 1280, 'height': 766, 'x': 80, 'y': 43}

        migrated = migrate_display_geometry(geometry, 3, (26, 71))
        self.assertEqual(migrated, {'width': 1254, 'height': 695, 'x': 80, 'y': 43})
        self.assertEqual(migrate_display_geometry(migrated, 4, (26, 71)), migrated)

    def test_schema_three_migration_respects_minimum_size(self):
        migrated = migrate_display_geometry(
            {'width': 650, 'height': 410, 'x': 0, 'y': 0},
            3,
            (100, 100),
            min_size=(640, 400),
        )

        self.assertEqual(migrated['width'], 640)
        self.assertEqual(migrated['height'], 400)


if __name__ == '__main__':
    unittest.main()
