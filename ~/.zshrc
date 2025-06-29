# ========================================
# Professional ZSH Configuration
# ========================================

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load
ZSH_THEME="powerlevel10k/powerlevel10k"

# ========================================
# ZSH Configuration
# ========================================

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
HYPHEN_INSENSITIVE="true"

# Uncomment one of the following lines to change the auto-update behavior
zstyle ':omz:update' mode auto      # update automatically without asking

# Uncomment the following line to change how often to auto-update (in days).
zstyle ':omz:update' frequency 13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
COMPLETION_WAITING_DOTS="true"

# ========================================
# Plugins
# ========================================
plugins=(
    git                    # Git shortcuts and info
    brew                   # Homebrew completion
    docker                 # Docker completion
    docker-compose         # Docker-compose completion
    node                   # Node.js shortcuts
    npm                    # NPM completion
    yarn                   # Yarn completion
    python                 # Python shortcuts
    pip                    # Pip completion
    vscode                 # VS Code shortcuts
    web-search            # Search from terminal
    history-substring-search  # Search history with arrow keys
    zsh-autosuggestions   # Fish-like autosuggestions
    zsh-syntax-highlighting  # Syntax highlighting
)

source $ZSH/oh-my-zsh.sh

# ========================================
# User Configuration
# ========================================

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
if [[ -n $SSH_CONNECTION ]]; then
  export EDITOR='nano'
else
  export EDITOR='code'
fi

# ========================================
# Useful Aliases
# ========================================

# Navigation
alias ..="cd .."
alias ...="cd ../.."
alias ....="cd ../../.."
alias ~="cd ~"
alias -- -="cd -"

# Enhanced ls
alias ll="ls -alF"
alias la="ls -A"
alias l="ls -CF"
alias lt="ls -ltr"    # Sort by time, newest last
alias lh="ls -lh"     # Human readable sizes

# Git shortcuts
alias g="git"
alias ga="git add"
alias gaa="git add --all"
alias gc="git commit -v"
alias gcm="git commit -m"
alias gco="git checkout"
alias gcb="git checkout -b"
alias gd="git diff"
alias gl="git pull"
alias gp="git push"
alias gs="git status"
alias gst="git status"
alias gb="git branch"
alias gba="git branch -a"
alias glg="git log --graph --oneline --decorate --all"
alias glog="git log --oneline --decorate --graph"
alias gwip="git add -A; git rm \$(git ls-files --deleted) 2> /dev/null; git commit --no-verify --no-gpg-sign -m '--wip-- [skip ci]'"

# Development shortcuts
alias py="python3"
alias pip="pip3"
alias serve="python3 -m http.server 8000"
alias myip="curl http://ipecho.net/plain; echo"
alias ports="lsof -i -P -n | grep LISTEN"
alias c="clear"
alias h="history"
alias j="jobs"
alias path='echo -e ${PATH//:/\\n}'

# Directory operations
alias md="mkdir -p"
alias rd="rmdir"

# System shortcuts
alias reload="source ~/.zshrc"
alias zshrc="code ~/.zshrc"
alias hosts="sudo code /etc/hosts"

# Docker shortcuts
alias d="docker"
alias dc="docker-compose"
alias dps="docker ps"
alias dpsa="docker ps -a"
alias di="docker images"
alias dstop="docker stop \$(docker ps -q)"
alias drm="docker rm \$(docker ps -aq)"
alias dprune="docker system prune -f"

# npm/yarn shortcuts
alias ni="npm install"
alias nid="npm install --save-dev"
alias nig="npm install -g"
alias nis="npm install --save"
alias nrs="npm run start"
alias nrb="npm run build"
alias nrd="npm run dev"
alias nrt="npm run test"
alias yi="yarn install"
alias ya="yarn add"
alias yad="yarn add --dev"
alias ys="yarn start"
alias yb="yarn build"
alias yd="yarn dev"
alias yt="yarn test"

# Quick file editing
alias nano="nano -W -T 4"
alias edit="code"

# Network
alias ping="ping -c 5"
alias fastping="ping -c 100 -s.2"

# ========================================
# Custom Functions
# ========================================

# Create a new directory and enter it
mkcd() {
    mkdir -p "$@" && cd "$_";
}

# Extract most know archives with one command
extract() {
    if [ -f $1 ] ; then
        case $1 in
            *.tar.bz2)   tar xjf $1     ;;
            *.tar.gz)    tar xzf $1     ;;
            *.bz2)       bunzip2 $1     ;;
            *.rar)       unrar e $1     ;;
            *.gz)        gunzip $1      ;;
            *.tar)       tar xf $1      ;;
            *.tbz2)      tar xjf $1     ;;
            *.tgz)       tar xzf $1     ;;
            *.zip)       unzip $1       ;;
            *.Z)         uncompress $1  ;;
            *.7z)        7z x $1        ;;
            *)     echo "'$1' cannot be extracted via extract()" ;;
        esac
    else
        echo "'$1' is not a valid file"
    fi
}

# Find a file with a pattern in name
ff() { find . -type f -iname '*'"$*"'*' -ls ; }

# Find a file with pattern $1 in name and Execute $2 on it
fe() { find . -type f -iname '*'"${1:-}"'*' -exec ${2:-file} {} \;  ; }

# Show current network connections to the server
connections() {
    netstat -an | grep ESTABLISHED | wc -l;
}

# Show open ports
openports() {
    lsof -i -P -n | grep LISTEN
}

# Get current public IP
publicip() {
    curl -s http://ipecho.net/plain
    echo
}

# Start a simple HTTP server from current directory
server() {
    local port="${1:-8000}"
    sleep 1 && open "http://localhost:${port}/" &
    # Set the default Content-Type to `text/plain` instead of `application/octet-stream`
    # And serve everything as UTF-8 (although not technically correct, this doesn't break anything for binary files)
    python3 -c $'import SimpleHTTPServer;\nmap = SimpleHTTPServer.SimpleHTTPRequestHandler.extensions_map;\nmap[""] = "text/plain";\nfor key, value in map.items():\n\tmap[key] = value + ";charset=UTF-8";\nSimpleHTTPServer.test();' "$port"
}

# ========================================
# Environment Variables
# ========================================

# Add commonly used paths
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Homebrew
if [[ -d "/opt/homebrew/bin" ]]; then
    export PATH="/opt/homebrew/bin:$PATH"
fi

# Node.js (if using nvm)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Python
export PYTHONPATH="$HOME/.local/bin:$PYTHONPATH"

# ========================================
# History Configuration
# ========================================
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt appendhistory
setopt sharehistory
setopt incappendhistory

# ========================================
# Key Bindings
# ========================================
# Use vim key bindings
# bindkey -v

# Use emacs key bindings (default)
bindkey -e

# History search
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down

# ========================================
# Powerlevel10k Configuration
# ========================================
# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# ========================================
# Welcome Message
# ========================================
echo "🌟 Welcome back, developer! 🌟"
echo "💡 Type 'reload' to refresh this config"
echo "⚡ Your professional ZSH environment is ready!" 