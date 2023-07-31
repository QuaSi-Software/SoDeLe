import PyInstaller.__main__


PyInstaller.__main__.run([
    './bin/app.py',
    # add the /sodele folder as option for source code
    '--add-data', './sodele;./sodele'
])
