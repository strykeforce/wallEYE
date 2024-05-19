# syntax=docker/dockerfile:1

FROM ubuntu

RUN apt-get update && apt-get install -y software-properties-common && add-apt-repository ppa:deadsnakes/ppa && apt-get install -y python3.11 python3-pip

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Git, cv2 dependencies, v4l2
RUN apt-get install -y git ffmpeg libsm6 libxext6 v4l-utils

RUN python3.11 -m pip install -U setuptools

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python3.11 -m pip install -U -r requirements.txt

# Add user to groups 
RUN usermod -a -G video root

# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 5800

# Run the application.
CMD python3.11 init.py
