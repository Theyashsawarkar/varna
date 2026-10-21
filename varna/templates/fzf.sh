# fzf colours, sourced by ~/.zshrc and the tmux pickers.
VARNA_FZF_COLORS='bg:-1,bg+:{{selected|surface0}},fg:{{fg}},fg+:{{text}},hl:{{accent2}},hl+:{{accent2}},border:{{accent2}},label:{{accent2}},prompt:{{accent2}},pointer:{{accent2}},info:{{muted}},query:{{fg}},ghost:{{overlay0}},input-border:{{accent2}},input-label:{{accent2}},list-border:{{line}},list-label:{{accent2}},footer-border:{{line}},footer-label:{{muted}},preview-border:{{line}},preview-label:{{muted}},spinner:{{accent}},marker:{{accent}}'
export VARNA_FZF_COLORS
export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS:+$FZF_DEFAULT_OPTS }--color=$VARNA_FZF_COLORS"
