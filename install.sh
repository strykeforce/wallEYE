echo "Beginning wallEYE Installation..."


if [ "$EUID" -ne 0 ]
  then echo "Run as root!"
  exit
fi

USER="$(whoami)"

# Python dependencies
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.12 python3.12-venv

wget https://bootstrap.pypa.io/get-pip.py
python3.12 get-pip.py

rm get-pip.py

python3.12 -m venv env

source env/bin/activate

# Download wallEYE
cd ~

git clone https://github.com/strykeforce/wallEYE.git

cd wallEYE/PiSideCode

python3.12 -m pip install -r requirements.txt

deactivate

# Dependencies
sudo apt install v4l-utils net-tools openssh-server

sudo chmod 4755 /usr/sbin/ifconfig

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
nvm install 20

echo "Node.js and npm version: $(node -v) $(npm -v)"

cd web_interface/walleye
npm install

# Service file
echo "[Unit]
Description=WallEYE Vision System Service
After=default.target
StartLimitIntervalSec=0
[Service]
Type=simple
Restart=always
RestartSec=1
WorkingDirectory=/home/$(USER)/wallEYE/PiSideCode
User=$(USER)
ExecStart=+/home/strykeforce/wallEYE/PiSideCode/env/bin/python3.12 /home/$(USER)/wallEYE/PiSideCode/init.py

[Install]
WantedBy=default.target" > /etc/systemd/system/walleye.service

sudo systemctl enable walleye
sudo systemctl start walleye

echo "wallEYE Installation Complete!"