# trap-ir-camera

## Camera setup process

- Start with latest RPi image.
- `sudo apt update`
- `sudo apt upgrade`

- `sudo raspi-config`
    - Add bushnet network
    - Set network to NZ
    - Enable I2C
    - Enable camera
    - Rename to `trap-ir-<id>`

- Reboot after finished with `raspi-cofnig`
- `sudo mkdir /etc/cacophony`
- Install cacophony-config
- Install/enable attiny-controller
- Install modemd
- Install/enable rtc-util
- `sudo apt install -y gpac`
- `sudo apt-get install python3-pip`
- Install salt https://repo.saltproject.io/#raspbian
- Set master URL in `master: salt.cacophony.org.nz`
- `sudo vi /etc/salt/minion.d/ports.conf`
`ports.conf`
```
publish_port: 4507
master_port: 4508
```

`LABEL=cp /media/cp auto auto,nofail,noexec,nodev,noatime,nodiratime,umask=000 0 2`

https://linuxize.com/post/how-to-install-opencv-on-raspberry-pi/
https://pypi.org/project/imutils/


`apt-get install python-systemd python3-systemd`

- Copy over files `scp ./ir-camera* pi@trap-ir-<id>.local:` and `scp ./requirements.txt pi@trap-ir-<id>.local:`
- `sudo pip3 install -r requirements.txt`
