These are instructions to get it running on your local machine for Visual Studio 2022
Python version 3.12

after cloning repo location: https://github.com/redroyalty910/resturaunt-mvp.git

You can view project files at View -> Solution Explorer

in terminal you have to run command to initialize virtual environment:
```
python -m venv venv
```
then activate the virtual environment:
(powershell)
```
.\venv\Scripts\Activate.ps1  
```
then run command to install packages (commands might take some time, please be patient)
```
pip install -r requirements.txt
```
then run python app in terminal with command:
```
python app.py
```

To access admin login page, type after the URL 8000/```admin/login```

The default login information to access admin panel for testing purposes is:

username: ``` admin ```

password: ```Password123```
