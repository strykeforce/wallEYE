import { Card, Form } from "react-bootstrap";
import { socket } from "../socket";

export default function OptionMenu(props) {
    return (
        <Form.Group className="p-2">
            <Card.Text for={props.label + props.camID}>
                <b>Select {props.label}</b>
            </Card.Text>
            <Form.Select
                onChange={(e) => {
                    socket.emit(
                        "set",
                        props.label,
                        props.camID,
                        e.target.value
                    );
                }}
                value={JSON.stringify(props.value)}
            >
                {props.options.map(
                    (res) => (
                        <option value={JSON.stringify(res)}>
                            {JSON.stringify(res)}
                        </option>
                    )
                )}
            </Form.Select>
        </Form.Group>
    );
}
