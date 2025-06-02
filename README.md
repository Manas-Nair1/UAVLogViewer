### Manas Nair fork of UAV log viewer

## Notes/considerations
- MVP version of flight aware chatbot 
- eslint had most of its rules turned off during dev
- not prod ready -  db should be stored client side not serverside(security issue aswell)

## How it works
- injects data parsed from .bin files to python through a post request 
- parsed data is cached to a db in %appdata% on server, allows llm to have persistent access to data. Only cleared on new file upload
- LLM Agent interacts with user instructions using "actions." Key actions are making DB calls to get data dynamically and delegating analysis to a specific flight engineer Agent
- In ambiguous queries, asks for clarification, polls data needed, and passes to Analyst agent to make conclusions using prompt injection, added context, and recursive calls. 

## Installation instructions
- ensure node 16
- ensure python 13 
- needs cesium key in src\components\CesiumViewer.vue otherwise will hang after file upload
- needs openai key in backend/baseLLM.py

## Build Setup

``` bash
# install dependencies
npm install

#dont use npm run dev only starts frontend

# serve with hot reload at localhost:8080
npm run start #starts both frontend and backend concurrently


```
