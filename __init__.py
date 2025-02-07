from os import abort
from flask import Flask, render_template, request, send_file, abort, redirect
from flask_httpauth import HTTPBasicAuth
import datetime as dt
from psql import SQLObject
from io import BytesIO
import loginlib


class Sound(SQLObject):
    SERVER_NAME = "hector"
    SCHEMA_NAME = "plsound"
    TABLE_NAME = "sounds"
    SQL_KEYS = ["id", "name", "extension", "data", "mime", "uploader", "uploaded"]
    PRIMARY_KEY = SQL_KEYS[0]

    def __init__(self, _id: int, name: str, extension: str, data: bytes, mime: str, uploader: int, uploaded: dt.datetime):
        super().__init__()
        self.id = _id
        self.name = name
        self.extension = extension
        self.data = data
        self.mime = mime
        self.uploader = uploader
        self.uploaded = uploaded

    @staticmethod
    def construct(response) -> list:
        return [Sound(x[0], x[1], x[2], x[3], x[4], x[5], x[6]) for x in response]

    def get_file(self) -> BytesIO:
        buffer = BytesIO()
        buffer.write(self.data)
        buffer.seek(0)
        return buffer


app = Flask(__name__)
auth = HTTPBasicAuth()


__version__ = "beta-1.0"


@auth.verify_password
def check_credentials(username, password):
    return username if loginlib.login(username, password).valid else None


@app.route("/")
def root():
    sounds = Sound.gets()
    return render_template("index.html", sounds=sounds)


@app.route("/upload", methods=["GET", "POST"])
@auth.login_required
def upload():
    if request.method == "POST":
        userid = loginlib.User.get(name=auth.current_user()).id
        form = request.form
        file = request.files["file"]

        if not file.filename:
            return abort(400, "File must have a filename")

        filename = form["name"]
        extension = file.filename.rsplit(".", 1)[-1]

        obj = Sound(..., filename, extension, file.stream.read(), file.mimetype, userid, ...)
        obj.commit()

        return redirect("/")

    return render_template("upload.html")


@app.route("/serve-sound/<sid>", defaults={"req_type": "serve"})
@app.route("/download/<sid>", defaults={"req_type": "download"})
def serve_sound(sid, req_type):
    sound = Sound.fetch(sid)
    as_attachment = req_type == "download"

    if not sound:
        return abort(404)

    return send_file(sound.get_file(), sound.mime, download_name=sound.name + "." + sound.extension, as_attachment=as_attachment)


@app.route("/get/<name>")
def get(name):
    sound = Sound.fetch(name=name)

    if not sound:
        return abort(404)

    return redirect(f"/serve-sound/{sound.id}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9980, debug=True)

