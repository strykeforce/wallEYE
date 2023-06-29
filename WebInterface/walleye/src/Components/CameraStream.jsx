import { Card, Button, Image } from "react-bootstrap";
import CameraSettings from "./CameraSettings";
import { socket } from "../socket";

export default function CameraStream(props) {
    return (
        <Card>
            <Card.Header>Camera Stream {props.camID}</Card.Header>
            <Card.Body>
                {props.showConfig && <CameraSettings camID={props.camID} state={props.state} />}

                <Button variant="primary"
                    onClick={() => {
                        socket.emit("toggle_calibration", props.camID);
                    }}>
                    {
                        (props.state.currentState === "BEGIN_CALIBRATION" || props.state.currentState === "CALIBRATION_CAPTURE") ? "Stop Calibration" : "Start Calibration"
                    }
                </Button >

                <Button variant="secondary"
                    onClick={() => {
                        socket.emit("generate_calibration", props.camID);
                    }}>
                    Generate Calibration
                </Button>

                <br />

                <Image src={"video_feed/" + props.state.cameraIDs[props.camID]} alt="Camera stream failed" fluid />
            </Card.Body>
        </Card >
    );
}