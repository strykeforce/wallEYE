import { Form } from "react-bootstrap";
import PoseVisualization from "./PoseVisualization";
import { socket } from "../socket";
import { useState } from "react";

export default function PoseVisualizationList(props) {
    const [isRendering, setIsRendering] = useState(props.state.visualizingPoses);

    const onToggle = () => {
        setIsRendering(!isRendering);
        socket.emit("toggle_pose_visualization", isRendering);
    };

    return (
        <>
            <Form>
                <Form.Check
                    type="switch"
                    onChange={onToggle}
                    label="Pose Visualization Toggle"
                    checked={isRendering}
                />
            </Form>
            {props.state.cameraIDs.map((camID) => <PoseVisualization poses={props.poses} state={props.state} camID={camID} />)}
        </>
    )
}