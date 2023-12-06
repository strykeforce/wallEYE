import { Button, Card, Form } from "react-bootstrap";
import FormRange from "react-bootstrap/esm/FormRange";
import { socket } from "../socket";
import "bootstrap-icons/font/bootstrap-icons.css";
import { useState } from "react";
import Confirm from "./Confirm";
import DataRangeBox from "./DataRangeBox";

export default function CameraSettings(props) {
    const [showCalWarning, setShowCalWarning] = useState(false);
    const [calE, setCalE] = useState(null);

    function action(e) {
        socket.emit("import_calibration", props.camID, e.target.files[0]);
    }

    return (
        <>
            <Confirm
                show={showCalWarning}
                setShow={setShowCalWarning}
                state={props.state}
                camID={props.camID}
                action={() => action(calE)}
            />

            <DataRangeBox
                label="Exposure"
                value={props.state.gain[props.camID]}
                min={props.state.exposureRange[props.camID][0]}
                max={props.state.exposureRange[props.camID][1]}
                step={props.state.exposureRange[props.camID][2]}
                event="set_exposure"
            />
            <DataRangeBox
                label="Gain"
                value={props.state.gain[props.camID]}
                min={props.state.gainRange[props.camID][0]}
                max={props.state.gainRange[props.camID][1]}
                step={props.state.gainRange[props.camID][2]}
                event="set_gain"
            />

            <br />

            <Form.Group>
                <Card.Text for={"res" + props.camID}>
                    Select a Resolution
                </Card.Text>
                <Form.Select
                    onChange={(e) => {
                        socket.emit(
                            "set_resolution",
                            props.camID,
                            e.target.value
                        );
                    }}
                    value={JSON.stringify(props.state.resolution[props.camID])}
                >
                    {props.state.supportedResolutions[props.camID].map(
                        (res) => (
                            <option value={JSON.stringify(res)}>
                                {JSON.stringify(res)}
                            </option>
                        )
                    )}
                </Form.Select>
            </Form.Group>

            <br />
            <Form.Label> Import Calibration</Form.Label>
            <Form.Control
                type="file"
                accept=".json"
                onChange={(e) => {
                    if (props.state.calFilePaths[props.camID]) {
                        setCalE(e);
                        setShowCalWarning(true);
                    } else action(e);
                }}
            />

            <br />

            <Button
                variant="success"
                onClick={() =>
                    window.open(
                        "files/" + props.state.calFilePaths[props.camID],
                        "_blank"
                    )
                }
                disabled={!props.state.calFilePaths[props.camID]}
            >
                {" "}
                <i class="bi bi-filetype-json"></i> Export Calibration{" "}
            </Button>
        </>
    );
}
