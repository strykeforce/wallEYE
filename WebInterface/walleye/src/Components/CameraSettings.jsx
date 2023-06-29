import { Card, Form } from "react-bootstrap";
import FormRange from "react-bootstrap/esm/FormRange";
import { socket } from "../socket";

export default function CameraSettings(props) {
    return (
        <div>
            <Card.Text>Gain: {props.state.gain[props.camID]}</Card.Text>

            <FormRange style={{ maxWidth: "25%" }} id={"SliderForGain" + props.camID}
                min={-1} max={1} value={props.state.gain[props.camID]}
                onChange={(e) => { socket.emit("set_gain", props.camID, e.target.value); }} />

            < Card.Text > Exposure: {props.state.exposure[props.camID]}</Card.Text >

            <FormRange style={{ maxWidth: "25%" }} id={"SliderForExposure" + props.camID}
                min={0} max={100} value={props.state.exposure[props.camID]}
                onChange={(e) => { socket.emit("set_exposure", props.camID, e.target.value); }} />

            < br />

            <Card.Text for={"res" + props.camID}>Select a Resolution</Card.Text>

            <Form.Select
                onChange={(e) => { socket.emit("set_resolution", props.camID, e.target.value); }}>

                {props.state.cameraResolutions[props.camID].map((res) => <option value={JSON.stringify(res)}>{JSON.stringify(res)}</option >)}

            </Form.Select >
            <br />
        </div>
    );
}