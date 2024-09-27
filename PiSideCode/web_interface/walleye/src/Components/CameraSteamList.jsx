import { Card, Col, Form, Row } from "react-bootstrap";
import CameraStream from "./CameraStream";
import { useState } from "react";

export default function CameraStreamList(props) {
    const [currentCam, setCurrentCam] = useState(
        props.state.cameraIDs.length === 0 ? null : props.state.cameraIDs[0]
    );

    var cameraStreams = {};

    for (const camID of props.state.cameraIDs) {
        cameraStreams[camID] = (
            <CameraStream
                camID={camID}
                state={props.state}
                imgInfo={props.imgInfo}
                showConfig={props.showConfig}
                readTime={
                    props.camReadTime
                        ? props.camReadTime[camID]
                        : "Not Updating!"
                }
            />
        );
    }
    return (
        <>
            <Form.Select
                onChange={(e) => {
                    setCurrentCam(e.target.value);
                }}
                value={currentCam}
            >
                {props.state.cameraIDs.map((camID) => (
                    <option value={camID}>{props.state.camNicknames[camID]}</option>
                ))}
            </Form.Select>
            <br />
            {currentCam ? (
                cameraStreams[currentCam]
            ) : (
                <p> No cameras available</p>
            )}
        </>
    );
}
