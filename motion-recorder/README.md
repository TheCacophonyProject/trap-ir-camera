## Making a new image from scratch
- Install latest Raspberry Pi OS Lite (64 bit). Using rpi-imager press ctrl+shift+x to open the extra settings and set WiFi name, country, and password.
- Insert SD card to Raspberry Pi and power RPi through USB (powering through hat will cause it to restart without attiny installed yet)
- SSH onto the RPi
- `sudo apt update`
- `sudo apt upgrade -y`
- Run `raspi-config` to enable camera, i2c
- `sudo mkdir /etc/cacophony`
- `sudo mkdir /etc/salt`
- Install 
    - go-config
    - event-reporter
    - Management interface from branch ir-camera
    - RTC
    - ATTiny controller
    - device-register and change prefix to trap-ir
    - modemd 1.2.3
- `sudo mkdir /media/cp`
- Add to `/etc/fstab` `LABEL=cp /media/cp auto auto,nofail,noexec,nodev,noatime,nodiratime,umask=000 0 2`
- restart device
- Device register shoudl have changed name so scan using sidekcik to see the devices name.
- `sudo apt install python3-opencv`
- Install salt and configure to connect to cacophony salt https://repo.saltproject.io/#debian
- `sudo apt install python3-pip -y`
- Copy over `ir-camera.service` `main.py` `motion.py` `requirements.txt` 
- `pip3 install -r requirements.txt`
- 
- 






## Making a new image to save
- Make a new image from scratch.
- Add to `/lib/systemd/system/salt-minion.service` `ConditionPathExists=/etc/salt/minion_id`
- Delete `/etc/salt/minion_id`
- Delete device config





- Install latest <name> image
- sudo apt update
- sudo apt upgrade -y
- raspi-config to enable camera, i2c, set wifi country, and password
- sudo apt install python3-opencv
- install management-interface from branch ir-camera (disable snapshot API from doing anything)
- install RTC





- Install latest RPI image
- Enable wifi and i2c
- install attiny-controller




- Copy files onto device.
- `sudo apt install python3-pip -y`
- `sudo pip3 install -r requirements`
- `sudo apt-get install libatlas-base-dev`
- `sudo apt install libgtk-3-0`
- `sudo apt-get install build-essential cmake pkg-config libjpeg-dev libtiff5-dev libjasper-dev libpng-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libfontconfig1-dev libcairo2-dev libgdk-pixbuf2.0-dev libpango1.0-dev libgtk2.0-dev libgtk-3-dev libatlas-base-dev gfortran libhdf5-dev libhdf5-serial-dev libhdf5-103 libqtgui4 libqtwebkit4 libqt4-test python3-pyqt5 python3-dev -y`
- `libilmbase-dev libopenexr-dev libgstreamer1.0-dev`