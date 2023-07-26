import Form from 'react-bootstrap/Form';
import { Button, InputGroup } from 'react-bootstrap';
import { socket } from '../socket.js';
import { useState } from 'react';

export default function Config(props) {
    const [newTableName, setNewTableName] = useState(props.state.tableName);
    const [newTeamNumber, setNewTeamNumber] = useState(props.state.teamNumber);
    const [newBoardDimsW, setNewBoardDimsW] = useState(props.state.boardDims[0]);
    const [newBoardDimsH, setNewBoardDimsH] = useState(props.state.boardDims[1]);
    const [newStaticIP, setNewStaticIP] = useState(props.state.ip);
    const [newTagSize, setNewTagSize] = useState(props.state.tagSize);

    return (
        <Form>
            <Form.Group className="mb-3" >
                <InputGroup>
                    <InputGroup.Text>Table Name</InputGroup.Text>
                    <Form.Control type="text" value={newTableName}
                        onChange={(e) => { setNewTableName(e.target.value); }} />
                    <Button variant="info" onClick={() => { socket.emit("set_table_name", newTableName) }}>
                        Update
                    </Button>
                </InputGroup>
            </Form.Group>
            <Form.Group className="mb-3" >
                <InputGroup>
                    <InputGroup.Text>Team Number</InputGroup.Text>
                    <Form.Control type="number" value={newTeamNumber} onChange={(e) => { setNewTeamNumber(e.target.value) }} />
                    <Button variant="info" onClick={() => { socket.emit("set_team_number", newTeamNumber); }}>
                        Update
                    </Button>
                </InputGroup>
            </Form.Group>
            <Form.Group className="mb-3" >
                <InputGroup>
                    <InputGroup.Text>Calibration Board Dimensions</InputGroup.Text>
                    <Form.Control type="number" value={newBoardDimsW} onChange={(e) => { setNewBoardDimsW(e.target.value) }} />
                    <InputGroup.Text>by</InputGroup.Text>
                    <Form.Control type="number" value={newBoardDimsH} onChange={(e) => { setNewBoardDimsH(e.target.value) }} />
                    <Button variant="info" onClick={() => { socket.emit("set_board_dims", newBoardDimsW, newBoardDimsH); }}>
                        Update
                    </Button>
                </InputGroup>
            </Form.Group>
            <br/>
            <Form.Group className="mb-3" >
                <InputGroup>
                    <InputGroup.Text>Set Static IP</InputGroup.Text>
                    <Form.Control type="text" value={newStaticIP} onChange={(e) => { setNewStaticIP(e.target.value) }} />
                    <Button variant="info" onClick={() => { socket.emit("set_static_ip", newStaticIP); }}>
                        Update
                    </Button>
                </InputGroup>
            </Form.Group>
            <Form.Group className="mb-3" >
                <Button variant="info" onClick={() => { socket.emit("reset_networking"); }}>
                    Reset Networking
                </Button>
            </Form.Group>
            <Form.Group className="mb-3" >
                <InputGroup>
                    <InputGroup.Text>Set Tag Size</InputGroup.Text>
                    <Form.Control type="number" value={newTagSize} onChange={(e) => { setNewTagSize(e.target.value) }} />
                    <Button variant="info" onClick={() => { socket.emit("set_tag_size", newTagSize); }}>
                        Update
                    </Button>
                </InputGroup>
            </Form.Group>
        </Form >
    );
}