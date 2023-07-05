import { Card, Button, Image, Col, Row, Badge } from "react-bootstrap";
import CameraSettings from "./CameraSettings";
import { socket } from "../socket";

export default function CameraStream(props) {
    return (
        <Card>
            <Card.Header>
                Camera Stream {props.camID} 
                {props.state.calFilePaths[props.camID] && <Badge bg="success"   >Calibration found</Badge>}
                {props.state.calFilePaths[props.camID] == null && <Badge bg="danger">Calibration not found</Badge>}
            </Card.Header>
            <Card.Body>
                <Row>
                    {props.showConfig && <Col><CameraSettings camID={props.camID} state={props.state} /></Col>}

                    <Col>
                        <Image src={"video_feed/" + props.camID} alt="Camera stream failed" fluid />

                        <br />

                        <Button variant="primary" className="m-2"
                            onClick={() => {
                                socket.emit("toggle_calibration", props.camID);
                            }}>
                            {
                                (props.state.currentState === "BEGIN_CALIBRATION" || props.state.currentState === "CALIBRATION_CAPTURE") ? "End Calibration" : "Start Calibration"
                            }
                        </Button >

                        <Button variant="secondary" className="m-2"
                            onClick={() => {
                                socket.emit("generate_calibration", props.camID);
                            }}>
                            Generate Calibration
                        </Button>
                    </Col>
                </Row>

            </Card.Body>
        </Card >
    );
}