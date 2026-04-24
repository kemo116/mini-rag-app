# mini-rag

this is a minimal implementaion of the rag model for question answering


## Requirements

- Python 3.13.9 or later


- Install Python using MiniConda

- create environment through :
$ conda create -n mini-rag 


- activate environment through :
$ conda activate mini-rag


(Optional) Setup you command line interface for better readability:
export PS1="\[\033[01;32m\]\u@\h:\w\n\[\033[00m\]\$ "

## installation

### install the required packages

```bash 
$ pip install -r requirements.txt
```

### Setup the environment variables 

```bash 
$ cp .env.example
```


Set your environment variables in the `.env` file.like `OPENAI_API_KEY` VALUE


### to run the fastapi server 
```$ uvicorn main:app --reload --host 0.0.0.0 --port 5000```


### download the postman collection from 

``` https://.postman.co/workspace/shoppingCart~d86c44b2-c31a-4ef3-ac01-89c526ad10c2/collection/33240565-81b8823d-300d-4b63-8c4d-be36ad6b0512?action=share&creator=33240565 ```


## Run Docker Compose Services

```bash
$ cd docker
$ cp .env.example .env

- update `.env` with your credentials
