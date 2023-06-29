import CameraStreamList from "./CameraSteamList";

export default function CameraConfig(props) {
    return (
        <>
            <CameraStreamList state={props.state} showConfig={true} />

            <hr />

            {props.state.calImgPaths.map((path) => <a href={'files/' + path}> {path} </a>) }

            {props.state.calFilePath != null && 
            <>
                <h2>Saved Calibration: </h2>
                <a href={'files/' + props.state.calFilePath}>{props.state.calFilePath}</a>
            </>}

        </>

    );
}