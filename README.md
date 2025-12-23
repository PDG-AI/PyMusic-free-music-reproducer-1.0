# PyMusic
A simple music reproducer based on terminal and commands, just a simple project, dont expect too much


-------------------------------------------------------------------------------------------------------

how to use
download python (i used python 3.11.9 (i think, idk (shouldnt matter)))
run python -m venv [venv_name]
run .\venv_name\scripts\activate
run pip install -r requirements.txt

go to spotify and idk how get your spotify client ID and secret ID and just put em on the config.py (idk why i made it a .py instead of .json or .txt, but yk)

finally run py main.py (will run if it doesnt just explode into a fucking fireball of errors)


if py or pip doesnt work, try pip3 and python or python3

if there is some problem, send feedback to the git repository


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
  - example: 1L remove 1 4 10
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
