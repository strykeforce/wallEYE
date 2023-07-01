import Nav from 'react-bootstrap/Nav';

export default function Navigation(props) {
    const handleSelect = (eventKey) => { props.setPage(eventKey) };

    return (
        <Nav variant="tabs" sticky="top" activeKey={props.page} onSelect={handleSelect}>
            {props.pages.map((page) => {
                return (
                    <Nav.Item>
                        <Nav.Link eventKey={page.id}>
                            {page.name}
                        </Nav.Link>
                    </Nav.Item>)
            })}
        </Nav>
    );
}
