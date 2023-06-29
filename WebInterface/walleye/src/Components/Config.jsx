import Form from 'react-bootstrap/Form';
import { Button } from 'react-bootstrap';
import { socket } from '../socket.js';
import { useState } from 'react';

export default function Config(props) {
    const [newTableName, setNewTableName] = useState(props.state.TABLENAME);
    const [newTeamNumber, setNewTeamNumber] = useState(props.state.TEAMNUMBER);

    return (
        <Form>
            <Form.Group className="mb-3" >
                <Form.Label>Table Name</Form.Label>
                <Form.Control type="text"
                    onChange={(e) => { setNewTableName(e.target.value); }} />
                <Button variant="info" onClick={() => { socket.emit("set_table_name", newTableName) }}>
                    Update table name
                </Button>
            </Form.Group>
            <Form.Group className="mb-3" >
                <Form.Label>Team Number</Form.Label>
                <Form.Control type="number" onChange={(e) => { setNewTeamNumber(e.target.value) }} />
                <Button variant="info" onClick={() => { socket.emit("set_team_number", newTeamNumber); }}>
                    Update team number
                </Button>
            </Form.Group>
        </Form >
    );
}