# Collector Node Services

## Installation

```sh
SERVICE_NAME=<service-name>
sudo cp -f "$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
service "$SERVICE_NAME" restart
systemctl enable "$SERVICE_NAME"
service "$SERVICE_NAME" status
```

### Cardano node

```sh
SERVICE_NAME=cardano-node
sudo cp -f "$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
service "$SERVICE_NAME" restart
systemctl enable "$SERVICE_NAME"
service "$SERVICE_NAME" status
```

### Ogmios

```sh
SERVICE_NAME=ogmios
sudo cp -f "$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
service "$SERVICE_NAME" restart
systemctl enable "$SERVICE_NAME"
service "$SERVICE_NAME" status
```

### cnt-indexer

```sh
SERVICE_NAME=cnt-indexer
sudo cp -f "$SERVICE_NAME.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
service "$SERVICE_NAME" restart
systemctl enable "$SERVICE_NAME"
service "$SERVICE_NAME" status
```

## Monitoring

```sh
SERVICE_NAME=<service-name>
journalctl -f -n 50 -u $SERVICE_NAME
```
