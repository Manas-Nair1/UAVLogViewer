# UAV Log Viewer Notes

- npm doesnt build on node 22, use node 16 
- missing cesium key in the npm instructions? needs it for cesium viewer to load and overlay to go away

- after getting the UAV logger running locally, worked on sending the parsed data to python backend. this is done through a post request in sidebarfilemanager everytime a new message type is parsed by the worker. 

- for each type of message, a table in a sqlite db is created, indexed by time, that the agentic ai will be able to interact with using sql commands to get context. 

## step 1 disable eslint when making new vue components