import { useEffect, useState } from "react";
import Navigation from "./Components/Navigation.jsx";
import { pages } from "./data.js";
import Config from "./Components/Config.jsx";
import "./bootstrap.min.css";
import Dashboard from "./Components/Dashboard.jsx";
import { socket } from "./socket.js";
import { Container, Form, Spinner, Stack } from "react-bootstrap";
import { Helmet } from "react-helmet";
import "./App.css";
import PoseVisualizationList from "./Components/PoseVisualizationList.jsx";

function App() {
    const [page, setPage] = useState("dashboard");
    const [state, setState] = useState(null);
    const [isConnected, setIsConnected] = useState(socket.connected);
    const [isDark, setIsDark] = useState(true);
    const [poses, setPoses] = useState(null);
    const [loopTime, setLoopTime] = useState(2767);
    const [msg, setMsg] = useState("Unknown!!!");

    useEffect(() => {
        const interval = setInterval(function () {
            socket.emit("pose_update");
            socket.emit("performance_update");
            socket.emit("msg_update");
        }, 500);

        return () => {
            clearInterval(interval);
        };
    }, []);

    // Runs once, force render after
    useEffect(() => {
        function onConnect() {
            setIsConnected(true);
        }

        function onDisconnect() {
            setIsConnected(false);
        }

        function onConfigReady() {
            window.open("./files/walleye_data/config.zip", "_blank");
        }

        function onStateUpdate(newState) {
            setState(newState);
        }

        function onError(error) {
            alert(error);
        }

        function onPoseUpdate(poses) {
            setPoses(poses);
        }

        function onPerformanceUpdate(time) {
            setLoopTime(time);
        }

        function onMsgUpdate(msg) {
            setMsg(msg);
        }

        function onInfo(info) {
            alert(info);
        }

        socket.on("connect", onConnect);
        socket.on("disconnect", onDisconnect);
        socket.on("state_update", onStateUpdate);
        socket.on("error", onError);
        socket.on("pose_update", onPoseUpdate);
        socket.on("performance_update", onPerformanceUpdate);
        socket.on("info", onInfo);
        socket.on("config_ready", onConfigReady);
        socket.on("msg_update", onMsgUpdate);

        return () => {
            socket.off("connect", onConnect);
            socket.off("disconnect", onDisconnect);
            socket.off("state_update", onStateUpdate);
            socket.off("error", onError);
            socket.off("pose_update", onPoseUpdate);
            socket.off("performance_update", onPerformanceUpdate);
            socket.off("info", onInfo);
            socket.off("config_ready", onConfigReady);
            socket.off("msg_update", onMsgUpdate);
        };
    }, []);

    if (!state) {
        return (
            <>
                <Helmet>
                    <html className="position-relative" />
                </Helmet>
                <Spinner
                    animation="border"
                    className="position-absolute top-50 start-50 translate-middle"
                />
            </>
        );
    }

    return (
        <div className="App">
            <Helmet>
                <html data-bs-theme={isDark ? "dark" : "light"} />
            </Helmet>

            <center className="position-relative">
                <h1 className="display-3">WallEYE</h1>

                <Stack direction="vertical" gap={1}>
                    <Form className="position-absolute top-50 end-0 translate-middle-y">
                        <Form.Check
                            type="switch"
                            onChange={() => setIsDark(!isDark)}
                            label="Dark Mode"
                            checked={isDark}
                        />
                    </Form>
                    <p>Loop Time: {loopTime} secs</p>
                    <p> {msg} </p>
                </Stack>
            </center>

            <Navigation
                sticky="top"
                page={page}
                pages={pages}
                setPage={setPage}
            ></Navigation>

            <br />

            <Container>
                {page === "dashboard" && (
                    <Dashboard state={state} poses={poses} />
                )}
                {page === "config" && <Config state={state} />}
                {page === "pose_visualization" && (
                    <PoseVisualizationList state={state} poses={poses} />
                )}
            </Container>
        </div>
    );
}

export default App;
