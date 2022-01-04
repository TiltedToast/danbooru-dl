# Description

An interactive CLI tool for downloading images off of danbooru (Do note that even the "safe" images can be suggestive, that's just how their rating system works)

# Build it yourself
If you want to compile the program yourself you'll need `pyinstaller`.

`pyi-makespec main.py --onefile --add-binary "driver/chromedriver.exe;driver\" --name danbooru-dl`

`pyinstaller --clean danbooru-dl.spec`
