# Install
```
> python -m venv t
> ./t/Scripts/activate  
> pip install -r requirements.txt
```

# Configure
Registration in https://cloud.ibm.com/ get API key and URL.  
Create .env file: 
```
PATH_MODULE="С:\\patch\\to\\folder\\core\\js\\newCore\\folder"
MODULE_NAME="mbo"
TRANSLATE_TO_ENG="N"
IBM_API_KEY=""
IBM_URL=""
```
and edit .env file. 

# Use
```
> python ./t.py
```
