import { Button, Container } from "react-bootstrap"
import CameraStreamList from "./CameraSteamList.jsx";
import { socket } from "../socket.js";

export default function Dashboard(props) {
    return (
        <Container>
            <Button variant="danger" onClick={() => { socket.emit("shutdown"); }}>SHUTDOWN</Button>

            <Button variant="success" onClick={() => { socket.emit("toggle_pnp") }}>Toggle PnP</Button>

            <hr />

            <h2> Cameras </h2>

            <CameraStreamList state={props.state} showConfig={false} />
        </Container>
    );
}

