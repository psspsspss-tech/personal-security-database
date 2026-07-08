Set WshShell = CreateObject("WScript.Shell")

' Set working directory to backend folder so relative paths in Python work correctly
WshShell.CurrentDirectory = "C:\Users\acer\Desktop\Security Suite\backend"

' Kill any existing instances to prevent port conflicts
WshShell.Run "cmd.exe /c taskkill /F /IM pythonw.exe /T", 0, True
WshShell.Run "cmd.exe /c taskkill /F /IM node.exe /T", 0, True

' Run Python backend completely hidden (using pythonw which has no console)
WshShell.Run "pythonw server.py", 0, False

' Run Node torrent service completely hidden (0 = hidden window)
WshShell.Run "cmd.exe /c node torrent_service.mjs", 0, False
