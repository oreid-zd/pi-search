Output docs/demo.gif
Set FontSize 15
Set Width 1450
Set Height 720
Set Theme {"background": "#16161e", "foreground": "#c0caf5", "cursor": "#c0caf5", "black": "#15161e", "red": "#f7768e", "green": "#9ece6a", "yellow": "#e0af68", "blue": "#7aa2f7", "magenta": "#bb9af7", "cyan": "#7dcfff", "white": "#a9b1d6", "brightBlack": "#414868", "brightRed": "#f7768e", "brightGreen": "#9ece6a", "brightYellow": "#e0af68", "brightBlue": "#7aa2f7", "brightMagenta": "#bb9af7", "brightCyan": "#7dcfff", "brightWhite": "#c0caf5"}
Set Padding 30

Set Shell zsh
# recorded with: docs/record-demo.sh
Require "docs/demo-search"
Hide
Type "alias pi-search='./docs/demo-search'"
Enter
Type "clear"
Enter
Show
Sleep 0.5s
Type "pi-search -d redis"
Sleep 0.5s
Enter
Sleep 2.5s
Escape
Sleep 0.5s
Type "pi-search -p -d redis"
Enter
Sleep 2.5s
Down
Sleep 1s
Ctrl+O
Sleep 4s
Type ":q"
Enter
Sleep 0.5s
Type "pi-search -p -d redis"
Enter
Sleep 2s
Enter
Sleep 4s
Ctrl+D
Sleep 1s
