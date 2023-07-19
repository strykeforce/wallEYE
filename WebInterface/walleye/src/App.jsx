import { useEffect, useState } from 'react';
import Navigation from './Components/Navigation.jsx';
import { pages } from './data.js';
import Config from './Components/Config.jsx';
import './bootstrap.min.css';
import Dashboard from './Components/Dashboard.jsx';
import CameraConfig from './Components/CameraConfig.jsx';
import { socket } from './socket.js';
import { Container, Form, Spinner, Stack } from 'react-bootstrap';
import { Helmet } from "react-helmet";
import './App.css';

function App() {
  const [page, setPage] = useState("dashboard");
  const [state, setState] = useState(null);
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [timestamp, setTimestamp] = useState("Never updated");
  const [isDark, setIsDark] = useState(true);
  const [poses, setPoses] = useState(null);

  // Not ideal way to get poses every 0.5 second
  setInterval(function(){
      socket.emit('pose_update'); 
  }, 500);

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

    function onPoseUpdate(poses) {
      setPoses(poses);
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('state_update', onStateUpdate);
    socket.on('error', onError);
    socket.on('pose_update', onPoseUpdate);

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('state_update', onStateUpdate);
      socket.off('error', onError);
      socket.off('pose_update', onPoseUpdate);
    };
  }, []);

  if (!state) {
    return (
      <>
        <Helmet>
          <html className="position-relative" />
        </Helmet>
        <Spinner animation="border" className="position-absolute top-50 start-50 translate-middle" />
      </>
    );
  }

  return (
    <div className="App">
      <Helmet>
        <html data-bs-theme={isDark ? "dark" : "light"} />
      </Helmet>

      <center className="position-relative">
        <h1 className="display-3">WallEYE Testing Interface</h1>
        <p className="lead">{(isConnected) ? "Connected" : "Not connected"} - Last updated at {timestamp}</p>

        <Stack direction="vertical" gap={1}>
          <Form className="position-absolute top-50 end-0 translate-middle-y">
            <Form.Check
              type="switch"
              onChange={() => setIsDark(!isDark)}
              label="Dark Mode"
              checked={isDark}
            />
          </Form>
        </Stack>
      </center>


      <Navigation sticky="top" page={page} pages={pages} setPage={setPage}></Navigation>

      <br />

      <Container>
        {page === 'dashboard' && <Dashboard state={state} poses={poses}/>}
        {page === 'config' && <Config state={state} />}
        {page === 'camera_config' && <CameraConfig state={state} poses={poses}/>}
      </Container>
    </div>
  );
}

export default App;
