# PyMusic mobile
A simple music reproducer based on terminal and commands, just a simple project, dont expect too much


-------------------------------------------------------------------------------------------------------

how to use
this is a mobile port, with changes to work on mobile devices with termux instaled (no root needed), will work when the phone is suspended or when you open any other app, even ones that doesnt let spotify work, like warthunder mobile, genshin etc, sometimes some commands break, like passing songs, wich can make two songs sound a the same time, and sometimes you cant see what you are typing

step 1: install termux from F-roid (the .apk) if you cant, use the Google play Termux, but might cause problems
step 2: execute termux and run
- pkg install python MPV (may also need FFmpeg)
step 3: download the repo.zip and put it on the Termux files, unzip it
step 4: navigate to the folder with the termux terminal (usually just "cd PyMusic")
step 5: execute
nano config.py (to change your spotify APIs)
nano password.py (to change your password)
step 6: do a "python main.py" and start hearing songs

HOW TO DOWNLOAD SONGS MANUALLY
rn there is no automated way, just do it the old way, put the .mp3 files you have on the /songs folder on the mobile phone, trought the mobile file manager, it doesnt show on PCs, then on metadata.json add

  "**file_name**": {
    "title": "**song_name**",
    "added_date": "**this is not important, just leave a random date, for example, 2025-09-11 09:37:27**"
  },

then you can add it to any list with the command, but instead of an ID, you have to add it with the file_name

commands

DOWNLOADING
- Download // D [YT link]    -downloads a YT song if its not private
- **RECOMENDED**- Paste // P    -downloads from wathever link you have copied, works on spotify and YT
- Download_spotify // DS [Spotify link]    -downloads any list // song from spotify
- Cancel // C    -cancels the current download
- **BETA** - Search // sch    -searchs a song on youtube by name, with a - you can separate artist from song


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


KNOWLEDGE
- Songs // SH    -shows all the songs with their song_id
- Lists // L    -shows all the lists with their list_id
- showlist // SL [list_id]    -shows the content of the list


OTHERS
- help    -shows help menu
- volume // v    -changes volume from 0 to 300




-SIDE NOTES

i made this shit over like 2 years, like one weekend, then i forget, and one month after that, i find it, so a lot of things dont make any f sense, like sometimes you need to use ID+L for list_id but sometimes just ID... idfc

no ads or payment required, open source
