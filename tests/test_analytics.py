import unittest

from analytics.in_memory import InMemoryAnalytics


class InMemoryAnalyticsTests(unittest.TestCase):
    def test_create_import_and_list(self):
        analytics = InMemoryAnalytics()
        board_id = analytics.create_board("demo")
        analytics.import_data(board_id, [{"x": 1}, {"x": 2}])

        board = analytics.get_board(board_id)
        self.assertEqual(board["name"], "demo")

        boards = list(analytics.list_boards())
        self.assertEqual(len(boards), 1)
        self.assertEqual(boards[0]["id"], board_id)

        data = analytics.get_board_data(board_id)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["x"], 1)


if __name__ == "__main__":
    unittest.main()
