#!/bin/bash

# Укажите путь к папке с сервером Valheim
SERVER_PATH="/valheim_server"

export templdpath=$LD_LIBRARY_PATH
export LD_LIBRARY_PATH="$SERVER_PATH/linux64:$LD_LIBRARY_PATH"
export SteamAppId=892970

echo "Starting server PRESS CTRL-C to exit"

# Tip: Make a local copy of this script to avoid it being overwritten by steam.
# NOTE: Minimum password length is 5 characters & Password cant be in the server name.
# NOTE: You need to make sure the ports 2456-2458 is being forwarded to your server through your local router & firewall.
"$SERVER_PATH/valheim_server.x86_64" -name "maserv" -port 2456 -world "123" -password "123wer543" -crossplay -logfile "/valheim_server/logs/valheim.log"

export LD_LIBRARY_PATH=$templdpath