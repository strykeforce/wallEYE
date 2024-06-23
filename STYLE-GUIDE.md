# wallEYE Style Guide

In an attempt to control the wild varieties of coding conventions that have been observed in this project, the following conventions are set forth to prevent our beloved wallEYE from decomposing into an unmaintainable puddle. Please update this document to ensure its relevance and helpfulness. 

## General

- `wallEYE` is the correct capitalization

## PiSideCode

- Folder and file names follow snake_case (special files like `Dockerfile` and `README.md` are exempt)
- Save paths as constants or write functions to generate the appropriate path in `directory.py`


### Python

- Follow [PEP 8 conventions](https://peps.python.org/pep-0008/). Most notably:
    - snake_case for variables and files
    - TitleCase for classes
    - SCREAMING_SNAKE_CASE for constants
    - Idiomatic Python (not Java!)
    - **Above all, be consistant!**
- Type hint when practical
- Send camelCase keys to front end web interface
- Documentation

### JS

- camelCase prevails here
- TitleCase for classes
- Use `props` in React hooks until someone desires to migrate to more modern React `{like, this, format}`

## RobotSideCode
- General Java conventions as excercised in robot code
- Documentation