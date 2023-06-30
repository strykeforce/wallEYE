import { useEffect, useRef, useState } from 'react';
import Navigation from './Components/Navigation.jsx';
import { pages, emptyData } from './data.js';
import Config from './Components/Config.jsx';
import 'bootstrap/dist/css/bootstrap.min.css';
import Dashboard from './Components/Dashboard.jsx';
import CameraConfig from './Components/CameraConfig.jsx';
import { socket } from './socket.js';
import { Container, Spinner } from 'react-bootstrap';


function App() {
  const [page, setPage] = useState("dashboard");
  const [state, setState] = useState(null);
  // const [response, setResponse] = useState(data);
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [timestamp, setTimestamp] = useState("Never updated");

  // data = structuredClone(emptyData);

  // Runs once, force render after
  useEffect(() => {
    function onConnect() {
      setIsConnected(true);
    }

    function onDisconnect() {
      setIsConnected(false);
    }

    function onStateUpdate(newState) {
      setTimestamp(new Date().toLocaleString());
      setState(newState);
    }

    function onError(error) {
      alert(error);
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('state_update', onStateUpdate);
    socket.on('error', onError);

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('state_update', onStateUpdate);
      socket.off('error', onError);
    };
  }, []);

  // useEffect(() => {
  //   fetch('/', {
  //     method: 'POST',
  //     headers: {
  //       'Accept': 'application/json',
  //       'Content-Type': 'application/json'
  //     },
  //     body: JSON.stringify(response),
  //   }).then(res => res.json())
  //     .then(
  //       (result) => {
  //         state.current = result;
  //         setPage(pages[0].id);
  //       },
  //       (error) => {
  //         alert("Fetch failed");
  //       }
  //     );
  // }, []);

  // // Avoid rerendering, just update - THIS RUNS AFTER RENDER!!!
  // useEffect(() => {
  //   fetch('/', {
  //     method: 'POST',
  //     headers: {
  //       'Accept': 'application/json',
  //       'Content-Type': 'application/json'
  //     },
  //     body: JSON.stringify(response),
  //   }).then(res => res.json())
  //     .then(
  //       (result) => {
  //         state.current = result;
  //       },
  //       (error) => {
  //         alert("Fetch failed");
  //       }
  //     );
  // });
  if (!state) {
    return (
      <div className="d-flex align-items-center justify-content-center">
        <Spinner animation="border" />
      </div>
    );
  }

  return (
    <div className="App">
      <h1 className="display-1">WallEYE Testing Interface</h1>
      <p className="lead">{(isConnected) ? "Connected" : "Not connected"} - Last server response at {timestamp}</p>
      <Navigation sticky="top" page={page} pages={pages} setPage={setPage}></Navigation>

      <br />

      <Container>
        {page === 'dashboard' && <Dashboard state={state} />}
        {page === 'config' && <Config state={state} />}
        {page === 'camera_config' && <CameraConfig state={state} />}
      </Container>
    </div>
  );
}

export default App;
