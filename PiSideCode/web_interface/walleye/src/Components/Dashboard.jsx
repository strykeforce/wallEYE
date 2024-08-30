import { Button, Row, Col, Image, Form } from "react-bootstrap";
import CameraStreamList from "./CameraSteamList.jsx";
import { socket } from "../socket.js";
import "bootstrap-icons/font/bootstrap-icons.css";

export default function Dashboard(props) {
    return (
        <>
            <h2>Controls</h2>
            <Button
                variant="outline-danger"
                className="m-2"
                onClick={() => {
                    socket.emit("shutdown");
                }}
            >
                <i class="bi bi-power"></i>SHUTDOWN
            </Button>
            <Button
                variant="success"
                className="m-2"
                onClick={() => {
                    socket.emit("toggle_pnp");
                }}
            >
                <i class="bi bi-motherboard"></i>
                {props.state.currentState === "PROCESSING"
                    ? "Stop PnP"
                    : "Start PnP"}
            </Button>
            <a
                href="files/walleye_data/walleye.log"
                className="btn btn-info"
                role="button"
            >
                {" "}
                <i class="bi bi-file-earmark-arrow-down"></i> Export Log
            </a>
            <Button
                variant="warning"
                className="m-2"
                onClick={() => {
                    socket.emit("export_config");
                }}
            >
                <i className="bi bi-file-earmark-arrow-down"></i>Export Config
            </Button>
            <br />
            <Form.Label> Import Config</Form.Label>
            <Form.Control
                type="file"
                accept=".zip"
                onChange={(e) => {
                    socket.emit("import_config", e.target.files[0]);
                }}
            />

            <br />

            <h2> Cameras </h2>
            <CameraStreamList
                state={props.state}
                imgInfo={props.imgInfo}
                showConfig={true}
                camReadTime={props.camReadTime}
            />

            <hr />

            {/* {props.state.reprojectionError ? <p>Reprojection Error: {props.state.reprojectionError}</p> : <p> No recent calibration.</p>} */}

            {props.state.calImgPaths.map((path) => (
                <>
                    <a href={"files/walleye_data/" + path}>{path}</a>
                    <br />
                </>
            ))}
        </>
    );
}
