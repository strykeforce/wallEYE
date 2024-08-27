# syntax=docker/dockerfile:1

FROM python:3.12

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
 
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Git, cv2 dependencies, v4l2
RUN apt-get update && apt-get install -y git libgl1-mesa-glx libsm6 libxext6 libatomic1 net-tools

# RUN python -m ensurepip --upgrade \
#     && python -m pip install --upgrade pip setuptools 
    

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install --extra-index-url=https://wpilib.jfrog.io/artifactory/api/pypi/wpilib-python-release-2024/simple robotpy-wpimath pyntcore \
    && python -m pip install -r requirements.txt


# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 5800

# Run the application.
CMD nice -n -20 python init.py
