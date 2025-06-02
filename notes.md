# notes on getting git repo running locally

- npm doesnt build on node 22, use node 16 
- missing cesium key in the npm instructions? needs it for cesium viewer to load and overlay to go away
- disable eslint during dev

# python backend 
- sending the parsed data to python backend. this is done through a post request in sidebarfilemanager everytime a new message type is parsed by the worker.  

- for each type of message, a table in a sqlite db is created, indexed by time, that the agentic ai will be able to interact with using sql commands to get context. 

- we have a couple additoinal things added as intermediate server-side logic such as dbinfo table: holding column names to give llm context on what data it has to reason about, and isAnomaly column: simply flags rows if they are statistically different from adjacent values using   


