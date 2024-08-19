import { Button, Card, Form } from "react-bootstrap";
import FormRange from "react-bootstrap/esm/FormRange";
import { socket } from "../socket";
import "bootstrap-icons/font/bootstrap-icons.css";
import { useState } from "react";
import Confirm from "./Confirm";
import DataRangeBox from "./DataRangeBox";
import OptionMenu from "./OptionMenu";

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

            {
                Object.entries(props.state.cameraConfigOptions[props.camID]).map(function (property) {
                    const info = props.state.cameraConfigs[props.camID];
                    const [name, rangeOrMenu] = property;
                    if (name.endsWith("_RANGE")) {
                        return <DataRangeBox
                            label={name.split("_RANGE")[0]}
                            value={info[name.split("_RANGE")[0]]}
                            camID={props.camID}
                            min={rangeOrMenu[0]}
                            max={rangeOrMenu[1]}
                            step={rangeOrMenu[2]}
                            event="set"
                        />
                    }
                    else if (name.endsWith("_MENU")) {
                        return <OptionMenu
                            label={name.split("_MENU")[0]}
                            value={info[name.split("_MENU")[0]]}
                            camID={props.camID}
                            options={rangeOrMenu}
                        />
                    }
                })
            }


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
