set -e
echo "Beginning wallEYE Installation..."

user=$(whoami)

echo "Installing as ${user}"

# Python dependencies
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install python3.13 python3.13-venv python3.13-dev

cd ~

git clone https://github.com/strykeforce/wallEYE.git # -b Refactoring --single-branch

cd wallEYE/PiSideCode

python3.13 -m venv env

source env/bin/activate

wget https://bootstrap.pypa.io/get-pip.py
python3.13 get-pip.py

rm get-pip.py

python3.13 -m pip install --upgrade setuptools
python3.13 -m pip install -r requirements.txt

deactivate

# Dependencies
sudo apt install v4l-utils net-tools openssh-server gpiod
sudo apt install -y nodejs npm
sudo apt install --reinstall linux-headers-$(uname -r)

sudo chmod 4755 /usr/sbin/ifconfig
sudo chmod 4755 /usr/sbin/ip

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" 

nvm install 20

echo "Node.js and npm version: $(node -v) $(npm -v)"

cd web_interface/walleye
npm install
npm run build

# Service file
sudo bash -c "echo \"[Unit]
Description=WallEYE Vision System Service
After=default.target
StartLimitIntervalSec=0
[Service]
Type=simple
Restart=always
RestartSec=1
WorkingDirectory=/home/${user}/wallEYE/PiSideCode
User=${user}
ExecStartPre=+/sbin/modprobe uvcvideo nodrop=1 timeout=5000 quirks=0x80
ExecStart=+/home/${user}/wallEYE/PiSideCode/env/bin/python3.13 /home/${user}/wallEYE/PiSideCode/init.py

[Install]
WantedBy=default.target\" > /etc/systemd/system/walleye.service"

sudo systemctl enable walleye
sudo systemctl start walleye

sudo chmod -R 777 "/home/${user}/wallEYE"

echo -e "\033[1;92m wallEYE Installation Complete!"
echo -e "\033[1;91m    Remember to disable autosuspend / sync the clock"
echo -e "\033[1;91m    Remember to disable autosuspend / sync the clock"
echo -e "\033[1;91m    Remember to disable autosuspend / sync the clock"
