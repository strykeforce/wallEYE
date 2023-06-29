import { Card, Col, Row } from "react-bootstrap";
import CameraStream from "./CameraStream";

export default function CameraStreamList(props) {
    return (
        <Row>
            {
                props.state.cameraIDs.map((camID) => <Col md="auto"><CameraStream camID={camID} state={props.state} showConfig={props.showConfig} /></Col>)
            }
        </Row >
    );
}