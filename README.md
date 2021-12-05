# YouTube Video Downloader

This tool allows you to download a single YouTube video, a whole playlist, and even a whole channel. The downloaded videos will be placed in the Downloads folder next to this file, not your computer's default Downloads folder.

Note: The videos and playlists you want to download must be either public or unlisted. If the video/playlist is private the tool cannot access it.

## Installing Necessary Packages (Windows)

1. Open command prompt and navigate to this folder using `cd "this folder's location"`
2. Makes sure that you have the latest version of pip using `py -m pip install --upgrade pip`
3. Install virtualenv: `py -m pip install --user virtualenv`
4. Create a virtual environment: `py -m venv venv`
5. Activate the virtual environment: `.\venv\Scripts\activate`
6. Install the required packages: `pip install -r requirements.txt`
7. When done, either:
   1. Go to step 3 in _Running the Tool_, or
   2. Deactivate the virtual environment: `deactivate`

## Running the Tool (Windows)

1. Open command prompt and navigate to this folder using `cd "this folder's location"`
2. Activate the virtual environment: `.\venv\Scripts\activate`
3. Run the tool: `py app.py`
4. The tool can now be used by following the instructions printed.
5. If the tool is taking a long time with downloading because you thought it was a good idea to download a playlist or channel with a **lot** of video but don't feel like waiting until it's done, pressing CTRL-C will terminate the tool.
6. If the tool got quit for any reason, it can be started again by going back to step 3.
7. When done, deactivate the virtual environment: `deactivate`
