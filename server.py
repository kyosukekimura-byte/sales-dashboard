"""
売上ダッシュボード用のローカルサーバー。

このフォルダ内のCSVファイルを一覧・提供し、売上ダッシュボード.html から
fetch でCSVデータを読み込めるようにする(ブラウザで直接file://を開くと
fetchがブロックされるため、ローカルサーバー経由にする必要がある)。

なお、ダッシュボードにドラッグ&ドロップしたCSVはブラウザのlocalStorageに
保存されるため、このサーバーを起動していなくても保存・ファイル切り替えが
可能。

使い方:
    python server.py [ポート番号]

起動後、ブラウザで http://localhost:8000/売上ダッシュボード.html を開く。
"""

import http.server
import json
import sys
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
DEFAULT_PORT = 8000


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def do_GET(self):
        if self.path == "/api/csvs":
            self.send_csv_list()
            return
        super().do_GET()

    def send_csv_list(self):
        files = sorted(p.name for p in DIRECTORY.glob("*.csv"))
        body = json.dumps(files, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"サーバー起動: http://127.0.0.1:{port}/売上ダッシュボード.html")
    print("終了するには Ctrl+C を押してください。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
