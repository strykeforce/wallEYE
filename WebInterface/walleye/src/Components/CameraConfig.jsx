import CameraStreamList from "./CameraSteamList";

export default function CameraConfig(props) {
    return (
        <>
            <CameraStreamList state={props.state} showConfig={true} />

            <hr />

            {props.state.calImgPaths.length > 0 && <h2>Captured Calibration Images:</h2>}
            {props.state.calImgPaths.map((path) => <><br/><a href={'files/' + path}> {path} </a></>)}
        </>

    );
}