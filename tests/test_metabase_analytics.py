import http.server
import json
import threading
import itertools
import unittest

from analytics.metabase import MetabaseAnalytics


class FakeMetabaseServer:
    def __init__(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            boards: dict[str, dict] = {}
            board_data: dict[str, list] = {}
            counter = itertools.count(1)

            def _json_response(self, code: int, obj: dict | list):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(obj).encode())

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/session":
                    if data.get("username") == "user" and data.get("password") == "pass":
                        self._json_response(200, {"id": "token"})
                    else:
                        self._json_response(403, {"error": "forbidden"})
                elif self.path == "/api/collection":
                    if self.headers.get("X-Metabase-Session") != "token":
                        self._json_response(401, {"error": "unauthorized"})
                        return
                    board_id = str(next(self.counter))
                    self.boards[board_id] = {"id": board_id, "name": data.get("name")}
                    self.board_data[board_id] = []
                    self._json_response(200, self.boards[board_id])
                elif self.path == "/api/dataset":
                    if self.headers.get("X-Metabase-Session") != "token":
                        self._json_response(401, {"error": "unauthorized"})
                        return
                    board_id = data.get("board_id")
                    rows = data.get("rows", [])
                    self.board_data.setdefault(board_id, []).extend(rows)
                    self._json_response(200, {})
                else:
                    self._json_response(404, {"error": "not found"})

            def do_GET(self):
                if self.headers.get("X-Metabase-Session") != "token":
                    self._json_response(401, {"error": "unauthorized"})
                    return
                if self.path == "/api/collection":
                    self._json_response(200, list(self.boards.values()))
                elif self.path.startswith("/api/collection/"):
                    board_id = self.path.split("/")[-1]
                    board = self.boards.get(board_id)
                    if board:
                        board_with_data = dict(board)
                        board_with_data["rows"] = self.board_data[board_id]
                        self._json_response(200, board_with_data)
                    else:
                        self._json_response(404, {"error": "not found"})
                else:
                    self._json_response(404, {"error": "not found"})

            def log_message(self, *args, **kwargs):
                pass

        self._server = http.server.ThreadingHTTPServer(("localhost", 0), Handler)
        host, port = self._server.server_address
        self.url = f"http://{host}:{port}"
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True

    def start(self):
        self._thread.start()

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()


class MetabaseAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeMetabaseServer()
        self.server.start()
        self.analytics = MetabaseAnalytics(self.server.url, "user", "pass")

    def tearDown(self):
        self.server.stop()

    def test_full_flow(self):
        board_id = self.analytics.create_board("demo")
        self.analytics.import_data(board_id, [{"x": 1}, {"x": 2}])
        board = self.analytics.get_board(board_id)
        self.assertEqual(board["name"], "demo")
        self.assertEqual(len(board["rows"]), 2)

        boards = list(self.analytics.list_boards())
        self.assertEqual(len(boards), 1)
        self.assertEqual(boards[0]["id"], board_id)


if __name__ == "__main__":
    unittest.main()
