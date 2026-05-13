# Fuzz Targets

This directory contains Atheris fuzz targets built by ClusterFuzzLite.

The first target exercises `Settings` validation because configuration is a process boundary that accepts environment, file, and CLI-derived values. It intentionally avoids network calls and secrets.

Run the batch fuzzing workflow from GitHub Actions, or build the ClusterFuzzLite container locally with the files in `.clusterfuzzlite/`.
