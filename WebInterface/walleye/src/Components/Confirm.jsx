import { useState } from 'react';
import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';

export default function Confirm(props) {
    return (
        <>
            <Modal show={props.show} onHide={() => props.setShow(false)}>
                <Modal.Header closeButton>
                    <Modal.Title>Save Calibration First?</Modal.Title>
                </Modal.Header>
                <Modal.Body>This action will overwrite the existing calibration.</Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={() => { props.action(); }}>
                        Proceed WITHOUT saving
                    </Button>
                    <Button variant="primary" onClick={() => { window.open("files/" + props.state.calFilePaths[props.camID], "_blank"); props.action(); }}>
                        Proceed WITH saving
                    </Button>
                </Modal.Footer>
            </Modal>
        </>
    );
}
