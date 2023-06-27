# Written for remote debugging
# Feel free to get rid of this if desired
import cv2
from flask import Response, Flask, render_template, request, send_file
import state
import os


class Buffer:  # Hacky solution, look for better way
    outputFrame = b""

    def update(self, img):
        self.outputFrame = cv2.imencode(".jpg", img)[1].tobytes()

    def output(self):
        while True:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + self.outputFrame + b"\r\n"
            )


app = Flask(__name__)

camBuffers = [Buffer() for i in range(len(state.cameraIDs))]


@app.route("/files/<path:path>")
def files(path):
    return send_file(os.path.join(os.getcwd(), path), as_attachment=True)


@app.route("/video_feed/<int:camID>")
def video_feed(camID):
    return Response(
        camBuffers[camID].output(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.get_json()

        print(data)
        
        state.camNum = data["camNum"]
        state.TEAMNUMBER = data["teamNum"]
        state.TABLENAME = data["tableName"]

        if data["gain"] is not None:
            state.gain[state.camNum] = float(data["gain"])

        if data["exposure"] is not None:
            state.exposure[state.camNum] = float(data["exposure"])

        if data["resolution"] is not None:
            state.resolution[state.camNum] = tuple(map(int, data["resolution"][1:-1].split(", ")))

        if "Processing" == data["clicked"]:
            state.currentState = state.States.PROCESSING

        if "toggleCalibration" == data["clicked"]:
            if state.currentState in (state.States.IDLE, state.States.PROCESSING):
                state.currentState = state.States.BEGIN_CALIBRATION
                state.cameraInCalibration = data["camNum"]
                state.reprojectionError = None
                state.calFilePath = None

            elif state.currentState == state.States.CALIBRATION_CAPTURE:
                state.currentState = state.States.IDLE

        elif "generateCalibration" == data["clicked"]:
            state.currentState = state.States.GENERATE_CALIBRATION

        elif "shutdown" == data["clicked"]:
            state.currentState = state.States.SHUTDOWN
        
        return render_template("index.html", state=state, page=data["page"])

    else:
        return render_template("index.html", state=state, page="dashboard")
