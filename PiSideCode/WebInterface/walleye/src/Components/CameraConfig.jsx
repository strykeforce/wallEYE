import CameraStreamList from "./CameraSteamList";

export default function CameraConfig(props) {
    return (
        <>
            <CameraStreamList state={props.state} poses={props.poses} showConfig={true} />
        </>
    );
}