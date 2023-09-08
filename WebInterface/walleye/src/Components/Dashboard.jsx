import { Button, Row, Col, Image } from "react-bootstrap"
import CameraStreamList from "./CameraSteamList.jsx";
import { socket } from "../socket.js";
import 'bootstrap-icons/font/bootstrap-icons.css';

export default function Dashboard(props) {
    return (
        <>
            <h2>Controls</h2>
            <Button variant="outline-danger" className="m-2" onClick={() => { socket.emit("shutdown"); }}><i class="bi bi-power"></i>SHUTDOWN</Button>
            <Button variant="success" className="m-2" onClick={() => { socket.emit("toggle_pnp") }}><i class="bi bi-motherboard"></i>{props.state.currentState === "PROCESSING" ? "Stop PnP" : "Start PnP"}</Button>
            <a href="files/walleye.log" class="btn btn-info" role="button"> <i class="bi bi-file-earmark-arrow-down"></i> Export Log</a>

            <br />

            <h2> Cameras </h2>
            <CameraStreamList state={props.state} poses={props.poses} showConfig={false} />

            <hr />

            {/* {props.state.reprojectionError ? <p>Reprojection Error: {props.state.reprojectionError}</p> : <p> No recent calibration.</p>} */}
        
            {props.state.calImgPaths.map((path) => <><a href={'files/' + path}>{path}</a ><br/></>)}
         
        </>
    );
}

