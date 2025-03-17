# script.cortanacloud
Cortana Cloud - Dropbox-based cloud save game synchronization for XBMC4Xbox.

## How to use:
- Create a Dropbox account, go into the developer console, create a new app with a unique name (ideally with App Folder access), enable all write functions in Permissions, and generate an authorization token.
- Copy this token to "dropbox.txt" and copy it to Q:/UserData/profiles/YourUsernameHere/
- Copy Cortana Cloud to "Q:/scripts/Cortana Cloud"
- Run and select upload/download/bulk upload/bulk download!

## Bugs:
- No upload timestamps as of yet.
- There's no backup feature, so make sure you REALLY want to download that cloud save!
- Some TitleIDs (such as homebrew) just display as their TitleIDs and not game names. Not much I can do about this apart from maybe make a blacklist to hide them!

## TODO:
- Add timestamps to last upload/download date.
- Add backup functionality if duplicate save folder is found
- Add scheduled backups?
- Implement proper progress bar for uploads.
- Add warning if cloud save is older than local save or vice versa.
