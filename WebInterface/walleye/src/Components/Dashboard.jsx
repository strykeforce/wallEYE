import { Button, Row, Col, Image } from "react-bootstrap"
import CameraStreamList from "./CameraSteamList.jsx";
import { socket } from "../socket.js";

export default function Dashboard(props) {
    return (
        <>
            <h2>Controls</h2>
            <Button variant="outline-danger" className="m-2" onClick={() => { socket.emit("shutdown"); }}>SHUTDOWN</Button>
            <Button variant="success" className="m-2" onClick={() => { socket.emit("toggle_pnp") }}>{props.state.currentState === "PROCESSING" ? "Stop PnP" : "Start PnP"}</Button>

            <br />

            <h2> Cameras </h2>
            <CameraStreamList state={props.state} showConfig={false} />

            <hr />

            {props.state.calImgPaths.length > 0 && <h2>Captured Calibration Images:</h2>}
            <Row>
                {props.state.calImgPaths.map((path) => <Col><a href={'files/' + path}><Image src={'files/' + path} /></a ></Col>)}
            </Row >
        </>
    );
}

