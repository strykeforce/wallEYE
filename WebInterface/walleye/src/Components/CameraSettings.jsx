import { Button, Card, Form } from "react-bootstrap";
import FormRange from "react-bootstrap/esm/FormRange";
import { socket } from "../socket";

export default function CameraSettings(props) {
    return (
        <>
            <Form.Group>
                <Card.Text>Gain: {props.state.gain[props.camID]}</Card.Text>

                <FormRange id={"SliderForGain" + props.camID} step="0.01"
                    min={-1} max={1} value={props.state.gain[props.camID]}
                    onChange={(e) => { socket.emit("set_gain", props.camID, e.target.value); }} />
            </Form.Group>

            <Form.Group>
                < Card.Text > Exposure: {props.state.exposure[props.camID]}</Card.Text >

                <FormRange id={"SliderForExposure" + props.camID}
                    min={0} max={100} value={props.state.exposure[props.camID]}
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
            <Form.Control type="file" accept=".json" onChange={(e) => socket.emit("import_calibration", props.camID, e.target.files[0])} />

            <br />

            <Button variant="success" onClick={() => window.open("files/" + props.state.calFilePaths[props.camID], "_blank")} disabled={!props.state.calFilePaths[props.camID]}> Export Calibration </Button>
        </>
    );
}