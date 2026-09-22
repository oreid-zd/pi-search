Output docs/demo.gif
Set FontSize 15
Set Width 1450
Set Height 720
Set Theme {"background": "#16161e", "foreground": "#c0caf5", "cursor": "#c0caf5", "black": "#15161e", "red": "#f7768e", "green": "#9ece6a", "yellow": "#e0af68", "blue": "#7aa2f7", "magenta": "#bb9af7", "cyan": "#7dcfff", "white": "#a9b1d6", "brightBlack": "#414868", "brightRed": "#f7768e", "brightGreen": "#9ece6a", "brightYellow": "#e0af68", "brightBlue": "#7aa2f7", "brightMagenta": "#bb9af7", "brightCyan": "#7dcfff", "brightWhite": "#c0caf5"}
Set Padding 30

Set Shell zsh
# recorded with: PATH=/tmp/pisearch-demo-home/bin:$PATH vhs docs/demo.tape
# (the PATH shim points pi-search at the fabricated demo corpus, not real sessions)
Type "pi-search 'redis'"
Sleep 0.5s
Enter
Sleep 3.5s
Down
Sleep 1.2s
Down
Sleep 1.5s
Enter
Sleep 2.5s
Type ":q"
Enter
Sleep 0.8s
Type "pi-search -v 'why is the dashboard slow'"
Enter
Sleep 8s
Down
Sleep 1.5s
Escape
Sleep 1s
