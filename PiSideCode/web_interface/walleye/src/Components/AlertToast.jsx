import React, { useState } from 'react';
import Toast from 'react-bootstrap/Toast';

export default function AlertToast(props) {
    return (
        <Toast style={{ backgroundColor: "gold", color: "blue" }} onClose={() => props.setShow(false)} show={props.show} delay={8000} autohide>
            <Toast.Body>{props.msg}</Toast.Body>
        </Toast>
    );
}

    