# PyMusic 1.3.0 update
A simple music reproducer based on terminal and commands, just a simple project, dont expect too much

**no ads or payment required, open source, you can do wathever changes you want to the code, open source, but please give some credit for it so other people can use this too**

current version (executable file stable): 1.1.2-stats
added some statistics shit so u can see how much time u have been damaging you ears and loosing your time on PyMusic

-----------------------------------

current version (executable beta): 1.3.0.b-DiscordPresence #the same as the source code update is, will work the same, may sometimes crash as python is not really made for exes, if you get any errors, share them and ill try to fix them, if you get many errors, you can switch to the executable file stable wich shouldnt crash

-----------------------------------

current version (source code (LATEST)): 1.3.0-DiscordPresence
now there is a discord integration, when you start PyMusic with discord desktop started, if you have the discord app in your account (https://discord.com/oauth2/authorize?client_id=1492995111682834646) it will be shown, indicating current song, reproduction time, and if it is stopped or not

other changes->
>alternative downloads, have added some more alternative sources, current used commands are just ADF (to import from folders, zips or files), Sch (to search on youtube by name), DS [spotify link] (to download from spotify, both playlists and individual songs), D [youtube link] (to download from youtube) - as all downloads (except ADF as it is import) use youtube, most songs are not going to be downloaded because of the copyrights on youtube, you can use SpotDown and import the folder with the music files

------------------------------------------------Changelog (read this if you get errors)

1.2.X:
now we got integrations, wich are basically integrations to other apps, right now there is only the streamlabs one, wich should also work for OBS and any other thing that uses web resource stream, and im not going to make a lot of integrations, cause i will focus on updating the base app, BUT YOU CAN, on the 1.2.1 i added the posibility to create your own integrations, see the example integration to know more, DO NOT USE STREAMLABS INTEGRATION AS AN EXAMPLE, PLEASE, IT IS NOT REALLY A NORMAL INTEGRATION, IT HAS GOT HARDCODED PARTS ON main.py, USE ONLY THE EXAMPLE INTEGRATION, the integrations system should be pretty easy to understand, to share them, zip the integration and upload it to drive, mediafire, or smth, idk, feel free to share your integrations with other people

about the streamlabs integration (wich should work for OBS), start PyMusic, and if you havent touched anything on the integrations folder, a server should start on http://localhost:8765/, put that as a web resource on OBS or StreamLabs,  500x150p, put a chroma key to make the black background disapear and should be ready to show wich song is starting to play on your streams :D 

-------------------------------------------------------------------------------------------------------

how to use
download python (i used python 3.11.9 (i think, idk (shouldnt matter anyways)))
run python -m venv [venv_name]
run .\venv_name\scripts\activate
run pip install -r requirements.txt

go to spotify and idk how get your spotify client ID and secret ID and just put em on the config.py (idk why i made it a .py instead of .json or .txt, but yk)

finally run py main.py (will run if it doesnt just explode into a fucking fireball of errors)


if py or pip doesnt work, try pip3 and python or python3

if there is some problem, send feedback to the git repository


HOW TO DOWNLOAD SONGS MANUALLY
- NO LONGER RECOMMENDED
i already added a adf ("ad"d song from "f"ile) command to the app on the 1.0 release, but if you got problems with that command, continue

HOW TO?
put the file you want on the /Songs folder (named as /A-Songs on the .exe version), then on the metadata.json put this information

  "**file_name**": {
    "title": "**song_name**",
    "added_date": "**this is not important, just leave a random date, for example, 2025-09-11 09:37:27**"
  },

if you have named it as a number, for example 34.mp3 to continue the normal music structure, just change the number on counter.json to match the number AFTER the one on the file (35 in this case), its important as the code can get confused and give an error when reaching that number as it alr exists but the counter says it doenst

then you can add it to any list with the command, but instead of an ID, you have to add it with the file_name
NOTE: you have follow json rules, so if it is the last song listed, dont put a "," at the end, but if there are more ahead of it put one 



# Commands

DOWNLOADING
- Download // D [YT link]    -downloads a YT song if its not private
- **RECOMENDED**- Paste // P    -downloads from wathever link you have copied, works on spotify and YT
- Download_spotify // DS [Spotify link]    -downloads any list // song from spotify               ----------- NEEDS TO HAVE config.py CONFIGURATED TO BE USED
- Cancel // C    -cancels the current download
- **BETA** - Search // sch    -searchs a song on youtube by name, with a - you can separate artist from song
- ADF    -asks you for a directory, then imports that file into the system automatically

MANAGING
- Create // CL [list_name] [song_id1] [song_id2]...    -creates a list with the set songs
  - example: CL this_shit_works_so_fucking_bad 1 2 3 8 10
- Edit // E [list_id] [add//remove] [song_id1] [song_id2]...    -edits the list to add or remove set songs
  - example: E 1L remove 1 4 10
- Delete [song_id//list_id] [password]    -removes the song or list


REPRODUCING
- Play // PL [list_id]    -reproduces a list on random song order
- Play_song // PS [song_id]    -reproduces a song
- Stop // S    -stops the current song
- Pass // P // Next // N    -passes to the next song on the list
- pause    -pause the reproduction, also unpauses it if its paused
- resume    -forcefully resume the reproduction
  

KNOWLEDGE
- Songs // SH    -shows all the songs with their song_id
- Lists // L    -shows all the lists with their list_id
- showlist // SL [list_id]    -shows the content of the list
- stats    -shows your "app" statistics


OTHERS
- help    -shows help menu
- volume // v    -changes volume from 0 to 300
- check [list_id]    -checks if the list to see if all the songs are downloaded and ready to use


-----------------------------------------------------------------------------------------------
in the case i missed a command here is the help command :D :
available commands:
- Download/D [url_youtube] - downloads a youtube video
- Download_Spotify/DS [url_playlist] - downloads an spotify playlist (some songs may be unavailable on youtube)
- Create/CL [list_name] [id1] [id2] ... - creates a new list
  example: Create ARandomList 1 2 5
  that will create a list named "ARandomList" with songs 1, 2 and 5
- Edit/E [list_id] add/remove [id1] [id2] ... - Edit an alr existing list
  examples:
  - Edit 1L add 6 7 8
  - Edit 1L remove 3 4
- Delete/DEL [list_id // song_id] [password] - delete a song or list
- Play/P [list_id] - plays a list
- Play_Song/PS [song_id] - plays an specific song
- Lists/L - shows all available lists
- Songs/SH - shows all available songs
- ShowList/SL [list_id] - shows a list's content
- Paste/PA - Paste whathever link you have copied and download the song
- Volume/V [0-300] - adjust volume (max 300% (i think it doesnt work and max is actually 100))
- Pass/NEXT/N - skips current song
- Check/CH [list_id] - verify list integrity
- Stop/S - stop current playing song
- Cancel/C - stops current download
- Help/H - shows this
- Search/Sch - name search on youtube
- ADF - add a song from a file
- Pause/Resume - pause or resume the current song
- stats - shows your app stats
-----------------------------------------------------------------------------------


-SIDE NOTES


