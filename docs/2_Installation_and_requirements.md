# Installation and requirements

orc2timeline requires **python3** and **python3-pip**. On Debian based distribution, these packages can be installed like this:
```
apt update && apt install python3 python3-pip
```

Make sure that the **latest version of pip** is installed, if not, it can be upgraded with the following command:
```
pip install --upgrade pip
```

orc2timeline can be installed **system-wide** or in a **virtual environment** (to avoid dependency issues) like any other python project. After cloning the repository with git, just run the `pip install .` command. This should download and install dependencies described in `pyproject.toml` file, after that the command `orc2timeline` should be in your path.

Supported and tested Operating Systems are:
  - Debian 11
  - Debian 12
  - Ubuntu 20.04
  - Ubuntu 22.04
  - Ubuntu 24.04

If an error occurs while using orc2timeline with one of these OS, feel free to **create an issue or a pull-request**.

If your favorite OS is not in the list, do not give up, it just means that it has not been tested **yet**.

## Installation without a virtual environment:

```
git clone https://github.com/ANSSI-FR/orc2timeline.git
cd orc2timeline
pip install .
```

## Installation with a virtual environment generated with virtualenv tool:

```
git clone https://github.com/ANSSI-FR/orc2timeline.git
cd orc2timeline
virtualenv -p python3 venv
source venv/bin/activate
pip install .
```

## View and edit dependencies for debugging or developing purposes

If you want to know or edit the dependencies, they can be found in `pyproject.toml` file, in the "dependencies" section.
```
[...]

dependencies = [  # Duplicate in pre-commit-config.yaml
  "click>=8.1.0",
  "dateparser==1.2.0",
  "py7zr==0.21.0",
  "libevtx-python==20240204",
  "libesedb-python==20240420",
  "dfwinreg==20240229",
  "six==1.16.0",
  "python-registry==1.3.1",
  "pytz==2024.1",
  "pyyaml==6.0.1",
]

[...]
```
