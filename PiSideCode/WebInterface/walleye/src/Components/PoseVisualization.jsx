import { Card, Image } from "react-bootstrap";

export default function PoseVisualization(props) {
    return (
        <Card>
            <Card.Header>
                Pose Visualization for Camera {props.camID}
            </Card.Header>
            <Card.Body>
                <Image
                    src={"pose_visualization/" + props.camID}
                    alt="Camera stream failed"
                    fluid
                />

                <Card.Text>
                    {" "}
                    Estimated Pose:{" "}
                    {props.poses
                        ? props.poses[props.camID]
                        : "Not available"}{" "}
                </Card.Text>
            </Card.Body>
        </Card>
    );
}
