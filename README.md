# UAV Log Viewer

![log seeking](preview.gif "Logo Title Text 1")

 This is a Javascript based log viewer for Mavlink telemetry and dataflash logs.
 [Live demo here](http://plot.ardupilot.org).

## Build Setup

``` bash
# install dependencies
npm install

# serve with hot reload at localhost:8080
npm run dev

# build for production with minification
npm run build

# run unit tests
npm run unit

# run e2e tests
npm run e2e

# run all tests
npm test
```

# Docker

run the prebuilt docker image:

``` bash
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest

```

or build the docker file locally:

``` bash

# Build Docker Image
docker build -t manasnair1/uavlogviewer .

# Run Docker Image
docker run -e VUE_APP_CESIUM_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI5OTc4ZmM2Zi1mMTAwLTRiMDgtOWFiMy1jMDZkNmIxMDYzMzciLCJpZCI6MzA4MDQzLCJpYXQiOjE3NDg3MDI4Nzh9.B471G6n68ywPyk8A-RO6-C1o7VzcW2L6ksrWpg3zGsc -it -p 8080:8080 -v ${PWD}:/usr/src/app manasnair1/uavlogviewer

# Navigate to localhost:8080 in your web browser

# changes should automatically be applied to the viewer

```
