import { useState } from "react";
import Button from "react-bootstrap/Button";
import Modal from "react-bootstrap/Modal";

export default function Confirm(props) {
    return (
        <>
            <Modal show={props.show} onHide={() => props.setShow(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>
                        Save Calibration First? {props.camID}
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    This action will overwrite the existing calibration.
                </Modal.Body>
                <Modal.Footer>
                    <Button
                        variant="secondary"
                        onClick={(e) => {
                            props.action();
                            props.setShow(false);
                        }}
                    >
                        Proceed WITHOUT saving
                    </Button>
                    <Button
                        variant="primary"
                        onClick={() => {
                            window.open(
                                "files/" +
                                    props.state.calFilePaths[props.camID],
                                "_blank"
                            );
                            props.action();
                            props.setShow(false);
                        }}
                    >
                        Proceed WITH saving
                    </Button>
                </Modal.Footer>
            </Modal>
        </>
    );
}
