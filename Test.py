from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

gauth = GoogleAuth()
gauth.LocalWebserverAuth()

def create_and_load(file_name = 'test.txt',file_content = 'Hello'):
    try:
        drive = GoogleDrive(gauth)
        myfile = drive.CreateFile({'title': f'{file_name}'})
        myfile.SetContentString(file_content)
        myfile.Upload()
        return f'File {file_name} was uploaded'
    except Exception as _ex:
        return "Error"
    
def upload_dir(dir_path = ''):
    try:
        drive = GoogleDrive(gauth)
        for file_name in os.listdir(dir_path):

            myfile = drive.CreateFile({'title': f'{file_name}'})
            myfile.SetContentFile(os.path.join(dir_path,file_name))
            myfile.Upload()
        return f'Files was uploaded'
    except Exception as _ex:
        return "Error"

def main():
    print(upload_dir(dir_path='Te'))

if __name__ =='__main__':
    main()