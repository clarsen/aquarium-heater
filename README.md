sudo pip3 install pipenv
pipenv --three
pipenv install influxdb RPi.GPIO
sudo cp aquarium-heater.service /etc/systemd/system
sudo systemctl enable aquarium-heater.service
sudo systemctl start aquarium-heater.service
