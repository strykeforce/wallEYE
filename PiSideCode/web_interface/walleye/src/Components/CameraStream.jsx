import { Card, Button, Image, Col, Row, Badge, ButtonGroup } from "react-bootstrap";
import CameraSettings from "./CameraSettings";
import { socket } from "../socket";
import "bootstrap-icons/font/bootstrap-icons.css";
import Confirm from "./Confirm";
import { useState } from "react";

export default function CameraStream(props) {
    const [showCalWarning, setShowCalWarning] = useState(false);

    function action() {
        socket.emit("generate_calibration", props.camID);
    }

    return (
        <>
            <Confirm
                show={showCalWarning}
                setShow={setShowCalWarning}
                state={props.state}
                action={action}
                camID={props.camID}
            />

            <Card>
                <Card.Header className="d-flex justify-content-between">
                    Camera Stream {props.camID}
                    <div className="d-flex justify-content-end">
                        <Badge bg="info" className="mx-1">
                            {props.readTime} secs
                        </Badge>
                        {props.state.calFilePaths[props.camID] ? (
                            <Badge bg="success" className="mx-1">
                                Calibration loaded!
                            </Badge>
                        ) : (
                            props.state.calFilePaths[props.camID] == null && (
                                <Badge bg="danger" className="mx-1">
                                    Calibration not available!!
                                </Badge>
                            )
                        )}
                    </div>
                </Card.Header>
                <Card.Body>
                    <ButtonGroup className="d-flex">
                        <Button
                            variant="outline-success"
                            onClick={() => {
                                socket.emit("set_mode", "POSE_ESTIMATION");
                            }}
                        >
                            Pose Estimation
                        </Button>
                        <Button
                            variant="outline-success"
                            onClick={() => {
                                socket.emit("set_mode", "TAG_SERVOING");
                            }}
                        >
                            Tag Servoing
                        </Button>
                        <Button
                            variant="outline-success"
                            onClick={() => {
                                socket.emit("set_mode", "DISABLED");
                            }}
                        >
                            Disabled
                        </Button>
                    </ButtonGroup>
                    <br/>
                    <Row>
                        {props.showConfig && (
                            <Col>
                                <CameraSettings
                                    camID={props.camID}
                                    state={props.state}
                                />
                            </Col>
                        )}

                        <Col>
                            <a href={"video_feed/" + props.camID}>
                                <Image
                                    src={"video_feed/" + props.camID}
                                    alt="Camera stream failed"
                                    fluid
                                />
                            </a>

                            <Card.Text>
                                {" "}
                                Estimated Pose:{" "}
                                {props.poses
                                    ? props.poses[props.camID]
                                    : "Not available"}{" "}
                            </Card.Text>
                            <br />

                            <Button
                                variant="primary"
                                className="m-2"
                                onClick={() => {
                                    socket.emit(
                                        "toggle_calibration",
                                        props.camID
                                    );
                                }}
                            >
                                <i class="bi bi-camera-video"></i>
                                {props.state.currentState ===
                                    "BEGIN_CALIBRATION" ||
                                props.state.currentState ===
                                    "CALIBRATION_CAPTURE"
                                    ? "End Calibration"
                                    : "Start Calibration"}
                            </Button>

                            <Button
                                variant="secondary"
                                className="m-2"
                                onClick={() => {
                                    if (props.state.calFilePaths[props.camID])
                                        setShowCalWarning(true);
                                    else action();
                                }}
                            >
                                <i class="bi bi-check"></i>
                                Generate Calibration
                            </Button>
                        </Col>
                    </Row>
                </Card.Body>
            </Card>
        </>
    );
}
