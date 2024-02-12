# Collector Node

A simplified collector node concept from Orcfax. Original documentation
available to maintainers can be found: [here][gh-1].

An Orcfax collector node now:

* Uses cron to request price-feed data every 1x minute.
* Via this Python script requests the price-feed data via Orcfax's enhanced
version of Chronicle Labs [gofer][gh-2].
* Parses the results from `gofer` and send the results to a validator
web-socket.

[gh-1]: https://github.com/orcfax/collector-node-archive
[gh-2]: https://github.com/orcfax/oracle-suite

## Node install

A small recipe for installation on a collector node machine.

> NB. the following assumes we're in the home folder root, i.e. `~/.` and a
> username of `orcfax`, i.e. `/home/orcfax/`.

### Create a collector directory

```sh
mkdir -p collector && cd collector
```

### Download this script

<!-- markdownlint-disable -->

```sh
wget https://raw.githubusercontent.com/orcfax/collector-node/main/collector.py -O collector.py
wget https://raw.githubusercontent.com/orcfax/collector-node/main/requirements/requirements.txt -O requirements.txt
```

<!-- markdownlint-enable -->

### Create a virtual environment

```sh
python3 -m venv venv
source venv/bin/activate
python -m pip install requirements.txt
```

### Download and initialize node-id

<!-- markdownlint-disable -->

```sh
wget https://github.com/orcfax/node-id/releases/download/0.0.1/node-id_0.0.1_Linux_x86_64 -O node-id
chmod +x node-id
./node-id -w ""
```

<!-- markdownlint-enable -->

> NB. the `-w` argument is legacy and replaced with the use of validator.env in
> this repository.

### Download gofer

<!-- markdownlint-disable -->

```sh
wget https://github.com/orcfax/oracle-suite/releases/download/0.0.1/gofer_0.0.1_Linux_x86_64 -O gofer
chmod +x gofer
```

<!-- markdownlint-enable -->

### Edit crontab

#### Open crontab

```sh
crontab -e
```

#### Amend the file with the following

<!-- markdownlint-disable -->

```text
ORCFAX_VALIDATOR=wss://<node-ws-endpoint>
*/1 * * * * /home/orcfax/collector/venv/bin/python /home/orcfax/collector/collector.py 2>&1 | logger -t orcfax_collector
```

<!-- markdownlint-enable -->

> NB. `crontab` will read the environment variable from its own context when
> it is set there.

### Congratulations

The collector node should be installed. You can view log output in the syslog.

```sh
sudo tail -f /var/log/syslog | grep orcfax_collector
```

## Developer install

### pip

Setup a virtual environment `venv` and install the local development
requirements as follows:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements/local.txt
```

#### Upgrade dependencies

A `make` recipe is included, simply call `make upgrade`. Alternatively run
`pip-upgrader` once the local requirements have been installed and follow the
prompts. `requirements.txt` and `local.txt` can be updated as desired.

### tox

#### Run tests (all)

```bash
python -m tox
```

#### Run tests-only

```bash
python -m tox -e py3
```

#### Run linting-only

```bash
python -m tox -e linting
```

### pre-commit

Pre-commit can be used to provide more feedback before committing code. This
reduces reduces the number of commits you might want to make when working on
code, it's also an alternative to running tox manually.

To set up pre-commit, providing `pip install` has been run above:

* `pre-commit install`

This repository contains a default number of pre-commit hooks, but there may
be others suited to different projects. A list of other pre-commit hooks can be
found [here][pre-commit-1].

[pre-commit-1]: https://pre-commit.com/hooks.html

## Packaging

The `Makefile` contains helper functions for packaging and release.

Makefile functions can be reviewed by calling `make`  from the root of this
repository:

```make
help                           Print this help message
pre-commit-checks              Run pre-commit-checks.
tar-source                     Package repository as tar for easy distribution
upgrade                        Upgrade project dependencies
```
