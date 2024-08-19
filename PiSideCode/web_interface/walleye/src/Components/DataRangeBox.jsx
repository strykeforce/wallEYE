import { Card, Col, Form, Row } from "react-bootstrap";
import FormRange from "react-bootstrap/esm/FormRange";
import { socket } from "../socket";
import "bootstrap-icons/font/bootstrap-icons.css";
import { useState } from "react";

export default function DataRangeBox(props) {
    const [value, setValue] = useState(props.value);
    return (
        <Form.Group className="p-2">
            <Row>
                <Col md="auto">
                    <Card.Text><b>{props.label}:</b></Card.Text>
                </Col>
                <Col>
                    <FormRange
                        step="1"
                        min={props.min}
                        max={props.max}
                        value={value}
                        onChange={(e) => {
                            socket.emit(
                                "set",
                                props.label,
                                props.camID,
                                e.target.value
                            );
                            setValue(e.target.value);
                        }}
                    />
                </Col>
                <Col xs={3}>
                    <Form.Control
                        type="number"
                        value={value}
                        onChange={(e) => {
                            socket.emit(
                                "set",
                                props.label,
                                props.camID,
                                e.target.value
                            );
                            setValue(e.target.value);
                        }}
                    />
                </Col>
            </Row>
        </Form.Group>
    );
}
