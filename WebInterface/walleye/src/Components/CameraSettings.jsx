import { Button, Card, Form } from "react-bootstrap";
import FormRange from "react-bootstrap/esm/FormRange";
import { socket } from "../socket";
import 'bootstrap-icons/font/bootstrap-icons.css';
import { useState } from "react";
import Confirm from "./Confirm";

export default function CameraSettings(props) {
    const [showCalWarning, setShowCalWarning] = useState(false);
    var e = "";

    function action(e) {
        socket.emit("import_calibration", props.camID, e.target.files[0]);
    }

    return (
        <>
            <Confirm show={showCalWarning} setShow={setShowCalWarning} state={props.state} camID={props.camID} action={() => action(e)} />

            <Form.Group>
                <Card.Text>Gain: {props.state.gain[props.camID]}</Card.Text>

                <FormRange id={"SliderForGain" + props.camID} step="1"
                    min={0} max={100} value={props.state.gain[props.camID]}
                    onChange={(e) => { socket.emit("set_gain", props.camID, e.target.value); }} />
            </Form.Group>

            <Form.Group>
                < Card.Text > Exposure: {props.state.exposure[props.camID]}</Card.Text >

                <FormRange id={"SliderForExposure" + props.camID}
                    min={0} max={5000} value={props.state.exposure[props.camID]}
                    onChange={(e) => { socket.emit("set_exposure", props.camID, e.target.value); }} />
            </Form.Group>

            < br />

            <Form.Group>
                <Card.Text for={"res" + props.camID}>Select a Resolution</Card.Text>
                <Form.Select
                    onChange={(e) => { socket.emit("set_resolution", props.camID, e.target.value); }} value={JSON.stringify(props.state.resolution[props.camID])}>

                    {props.state.supportedResolutions[props.camID].map((res) => <option value={JSON.stringify(res)}>{JSON.stringify(res)}</option >)}

                </Form.Select >
            </Form.Group>

            <br />
            <Form.Label> Import Calibration</Form.Label>
            <Form.Control type="file" accept=".json" onChange={
                (e) => {
                    if (props.state.calFilePaths[props.camID]) setShowCalWarning(true);
                    else action(e);
                }
            } />

            <br />

            <Button variant="success" onClick={() => window.open("files/" + props.state.calFilePaths[props.camID], "_blank")} disabled={!props.state.calFilePaths[props.camID]}> <i class="bi bi-filetype-json"></i> Export Calibration </Button>
        </>
    );
}