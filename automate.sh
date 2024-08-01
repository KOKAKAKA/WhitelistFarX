tmux new-session -d -s "Bot" "cd /storage/emulated/0/Download/TermuxS && python bot.py"
tmux new-session -d -s "Node" "cd /storage/emulated/0/Download/TermuxS/WhitelistFarX && node whitelist.js"
tmux new-session -d -s "ngrok" "cd /storage/emulated/0/Download/TermuxS && ngrok start bin"
