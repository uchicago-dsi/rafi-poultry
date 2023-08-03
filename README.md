# RAFI-USA

project context, instructions for makefile, explain directories
update notebooks

## Development Dependencies

- Docker
- Make

## Setup

(1) Install [Docker](https://docker-curriculum.com/) if you have not already done so. Windows users
will have to set up and configure Windows Subsystem for Linux ([WSL2](https://docs.microsoft.com/en-us/windows/wsl/install))
beforehand.

(2) Install `make` for MacOS or Linux.  For example, users with Ubuntu would run `sudo apt update` followed by `sudo apt install make`. Confirm correct installation by running the command `make --version`.

(3) Ensure that Docker is running. Then navigate to the root of the project and run the command `make build` to create a new Docker image.