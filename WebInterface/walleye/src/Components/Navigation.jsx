import { Container, Form, Navbar, Stack } from 'react-bootstrap';
import Nav from 'react-bootstrap/Nav';

export default function Navigation(props) {
    const handleSelect = (eventKey) => { props.setPage(eventKey) };

    return (
        <Navbar sticky="top" >
            <Nav activeKey={props.page} onSelect={handleSelect} variant="tabs" className="vw-100" justify>
                {props.pages.map((page) => {
                    return (
                        <Nav.Item>
                            <Nav.Link eventKey={page.id}>
                                {page.name}
                            </Nav.Link>
                        </Nav.Item>)
                })}
            </Nav>
        </Navbar>
    );
}
