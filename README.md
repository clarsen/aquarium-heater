   git clone https://github.com/clarsen/aquarium-heater.git
   cd aquarium-heater
   sudo pip3 install pipenv
   pipenv --three
   pipenv install influxdb RPi.GPIO PyYAML
   make your own config.yaml
   sudo cp aquarium-heater.service /etc/systemd/system
   sudo systemctl enable aquarium-heater.service
   sudo systemctl start aquarium-heater.service
