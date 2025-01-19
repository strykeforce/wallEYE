# Script for Windows to deploy wallEYE Pi side updates with absolutely minimal security
# Modify to match setup

$servers = @(
    @{ Hostname = "10.27.67.11"; },
    @{ Hostname = "10.27.67.12";},
    @{ Hostname = "10.27.67.13"; },
)

foreach ($server in $servers) {
    $hostname = $server.Hostname
    $username = "strykeforce"
    $directory = $server.Directory

    $sshCommand = @"
cd $directory
git pull
echo StrykeForce | sudo -S systemctl restart walleye
"@

    Write-Host "Updating $hostname..."

    $sshSession = New-Object -TypeName System.Management.Automation.PSCustomObject -Property @{
        Hostname = $hostname
        Username = $username
        Password = "StrykeForce"
    }

    $sshCommandLine = "ssh $username@$hostname '$sshCommand'"

    cmd.exe /C "echo $passwordPlainText | ssh $username@$hostname $sshCommand"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successful $hostname"
    } else {
        Write-Host "Failed $hostname"
    }
}
