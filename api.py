"""Flask API 入口"""
import os

from flask import Flask

from biz.api.routes.webhook import webhook_bp
from biz.service.storage_service import StorageService

app = Flask(__name__)
app.register_blueprint(webhook_bp)


@app.route("/")
def index():
    return {"message": "Code-to-Reasoning server is running.", "webhook": "/reasoning/webhook"}


def main():
    StorageService.init_db()
    port = int(os.getenv("PORT", 5003))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
