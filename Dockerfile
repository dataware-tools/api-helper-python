FROM python:3.8-slim

# Basic Setting
ENV LANG="en_US.UTF-8"

# Install poetry
RUN python3 -m pip install --upgrade pip \
  && python3 -m pip install setuptools \
  && python3 -m pip install poetry \
  && poetry config virtualenvs.create false \
  && rm -rf ~/.cache/pip

# Copy files and install dependencies
RUN mkdir -p /opt/app
COPY ./pyproject.toml /opt/app/pyproject.toml
WORKDIR /opt/app
RUN poetry install || poetry update

# Copy remaining files
COPY . /opt/app

# Default CMD
CMD ["python", "test.py"]
