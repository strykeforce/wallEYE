import { Button } from "react-bootstrap";
import PoseVisualization from "./PoseVisualization";
import { socket } from "../socket";
import { useState } from "react";

export default function PoseVisualizationList(props) {
    const [isRendering, setIsRendering] = useState(
        props.state.visualizingPoses
    );

    return (
        <>
            <Button
                variant="info"
                onClick={() => {
                    socket.emit("toggle_pose_visualization");
                }}
            >
                <i class="bi bi-bar-chart-line-fill"></i>
                {isRendering ? "Stop Visualizing" : "Start Visualizing"}
            </Button>
            <br />
            {props.state.cameraIDs.map((camID) => (
                <PoseVisualization
                    poses={props.poses}
                    state={props.state}
                    camID={camID}
                />
            ))}
        </>
    );
}
