import { Button, Container } from "react-bootstrap"
import CameraStreamList from "./CameraSteamList.jsx";
import { socket } from "../socket.js";

export default function Dashboard(props) {
    return (
        <Container>
            <h2>Controls</h2>
            <Button variant="danger" className="m-2" onClick={() => { socket.emit("shutdown"); }}>SHUTDOWN</Button>
            <Button variant="success" className="m-2" onClick={() => { socket.emit("toggle_pnp") }}>{props.state.currentState === "PROCESSING" ? "Stop PnP" : "Start PnP"}</Button>

            <br/>

            <h2> Cameras </h2>
            <CameraStreamList state={props.state} showConfig={false} /> 
        </Container>
    );
}

