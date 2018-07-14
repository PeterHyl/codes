set nocompatible                            " required
filetype off                                " required

set rtp+=~/.vim/bundle/Vundle.vim           " set the runtime path to include Vundle and initialize

call vundle#begin()

"-------------------=== Code/Project navigation ===-------------
Plugin 'VundleVim/Vundle.vim'               " let Vundle manage Vundle, required
Plugin 'scrooloose/nerdtree'                " Project and file navigation

"-------------------=== Other ===-------------------------------
Plugin 'Lokaltog/powerline'                 " Powerline fonts plugin
Plugin 'flazz/vim-colorschemes'             " Colorschemes
Plugin 'bling/vim-airline'                  " Lean & mean status/tabline for vim
Plugin 'vim-airline/vim-airline-themes'     " Themes for airline
Plugin 'godlygeek/tabular'

"-------------------=== Python  ===-----------------------------
Plugin 'klen/python-mode'                   " Python mode (docs, refactor, lints...)
Plugin 'scrooloose/syntastic'               " Syntax checking plugin for Vim
Plugin 'davidhalter/jedi-vim'               " Autocomplete plugin

" All of your Plugins must be added before the following line
call vundle#end()

filetype on
filetype plugin on
filetype plugin indent on

"=====================================================
" General settings
"=====================================================
syntax enable                               " syntax highlight

set t_Co=256                                " set 256 colors
colorscheme wombat256mod                    " set color scheme
set enc=utf-8                               " utf-8 by default

set number                                  " show line numbers
set ruler
set mousehide                               " hide mouse when typing
set mouse=a

set tabstop=4                               " 4 whitespaces for tabs visual presentation
set shiftwidth=4                            " shift lines by 4 spaces
set smarttab                                " set tabs for a shifttabs logic
set expandtab                               " expand tabs into spaces
set smartindent                             " smart indent
set pastetoggle=<F3>                        " paste without another indent

set cursorline                              " shows line under the cursor's line
set showmatch                               " shows matching part of bracket pairs (), [], {}
set nobackup
set swapfile
set dir=~/tmp
set backspace=indent,eol,start              " backspace removes all (indents, EOLs, start)

set scrolloff=10                            " let 10 lines before/after cursor during scroll
set clipboard=unnamed                       " clipboard normal behaviour
set showcmd                                 " show command in bottom right portion of the screen
set laststatus=2                            " always show the status line

"=====================================================
" Search settings
"=====================================================
set incsearch                              " incremental search
set hlsearch                               " highlight search results

"=====================================================
" Tabs / Buffers settings
"=====================================================
tab sball
set switchbuf=useopen
set laststatus=2
nmap <F9> :bprev<CR>
nmap <F10> :bnext<CR>
nmap <silent> <leader>q :SyntasticCheck # <CR> :bp <BAR> bd #<CR>
nmap <F8> :bd<CR>

"=====================================================
" AirLine settings
"=====================================================
let g:airline_theme='badwolf'
let g:airline#extensions#tabline#enabled=1
let g:airline#extensions#tabline#formatter='unique_tail'

"=====================================================
" NERDTree settings
"=====================================================
let NERDTreeIgnore=['\.pyc$', '\.pyo$', '__pycache__$']     " Ignore files in NERDTree
let NERDTreeWinSize=40
autocmd VimEnter * if !argc() | NERDTree | endif            " Load NERDTree only if vim is run without arguments
nmap <F2> :NERDTreeToggle<CR>
let g:NERDTreeDirArrowExpandable="+"
let g:NERDTreeDirArrowCollapsible="~"

"=====================================================
" Python settings
"=====================================================
" python executables for different plugins
let g:pymode_python='python'
let g:syntastic_python_python_exec='python'

" rope
let g:pymode_rope=0
let g:pymode_rope_completion=0
let g:pymode_rope_complete_on_dot=0
let g:pymode_rope_auto_project=0
let g:pymode_rope_enable_autoimport=0
let g:pymode_rope_autoimport_generate=0
let g:pymode_rope_guess_project=0

" documentation
let g:pymode_doc=0
let g:pymode_doc_key='K'

" syntax highlight
let g:pymode_syntax=1
let g:pymode_syntax_slow_sync=1
let g:pymode_syntax_all=1
let g:pymode_syntax_print_as_function=g:pymode_syntax_all
let g:pymode_syntax_highlight_async_await=g:pymode_syntax_all
let g:pymode_syntax_highlight_equal_operator=g:pymode_syntax_all
let g:pymode_syntax_highlight_stars_operator=g:pymode_syntax_all
let g:pymode_syntax_highlight_self=g:pymode_syntax_all
let g:pymode_syntax_indent_errors=g:pymode_syntax_all
let g:pymode_syntax_string_formatting=g:pymode_syntax_all
let g:pymode_syntax_space_errors=g:pymode_syntax_all
let g:pymode_syntax_string_format=g:pymode_syntax_all
let g:pymode_syntax_string_templates=g:pymode_syntax_all
let g:pymode_syntax_doctests=g:pymode_syntax_all
let g:pymode_syntax_builtin_objs=g:pymode_syntax_all
let g:pymode_syntax_builtin_types=g:pymode_syntax_all
let g:pymode_syntax_highlight_exceptions=g:pymode_syntax_all
let g:pymode_syntax_docstrings=g:pymode_syntax_all

" highlight 'long' lines (>= 120 symbols) in python files
augroup vimrc_autocmds
    autocmd!
    autocmd FileType python,rst,c,cpp highlight Excess ctermbg=DarkGrey guibg=Black
    autocmd FileType python,rst,c,cpp match Excess /\%121v.*/
    autocmd FileType python,rst,c,cpp set nowrap
    autocmd FileType python,rst,c,cpp set colorcolumn=120
augroup END

" code folding
let g:pymode_folding=0

" pep8 indents
let g:pymode_indent=1
let g:pymode_options_max_line_length = 120

" syntastic
let g:syntastic_always_populate_loc_list=1
let g:syntastic_auto_loc_list=1
let g:syntastic_enable_signs=1
let g:syntastic_check_on_wq=0
let g:syntastic_aggregate_errors=1
let g:syntastic_loc_list_height=7
let g:syntastic_error_symbol='X'
let g:syntastic_style_error_symbol='X'
let g:syntastic_warning_symbol='x'
let g:syntastic_style_warning_symbol='x'
let g:syntastic_python_checkers=['flake8', 'pylint']
let g:syntastic_python_pylint_post_args="--max-line-length=120"

" PyLint on open file
nmap <F4> :SyntasticCheck pylint<CR>

" remove trailing whitespace
autocmd BufWritePre * %s/\s\+$//e

"=====================================================
" Keys Mapping
"=====================================================
" switch between windows
nmap <Tab> <C-w>w

" save and quit keys
nmap <C-o> :w<CR>
imap <C-o> <C-O> :w<CR>
nmap <C-c> :q<CR>
imap <C-c> <Esc> :q<CR>

" quit discarding changes
imap <F6> <ESC>:qa!<CR>
nmap <F6> :qa!<CR>

" undo
imap <C-z> <Esc>u :startinsert<CR>
nmap <C-z> u

" delete line
nmap <C-d> dd
imap <C-d> <Esc>dd :startinsert<CR>

" Saves time; maps the spacebar to colon
nmap <space> :

" Map escape key to jj -- much faster
" imap jj <esc>

" Indent/unindent highlighted block (and maintain highlight)
vmap <Tab>    >gv
vmap <S-Tab>  <gv

" easier window navigation
nmap <C-h> <C-w>h
nmap <C-j> <C-w>j
nmap <C-k> <C-w>k
nmap <C-l> <C-w>l

" easier navigation with wraped lines
map <Down> gj
map <Up> gk

" mouse and number line enable/disable
nmap <silent><F12> :call ToggleMouse()<CR>
imap <silent><F12> :call ToggleMouse()<CR>
nmap <F11> :set invnumber<CR>
imap <F11> <C-O>:set invnumber<CR>

" toggle mouse
function! ToggleMouse()
    " check if mouse is enabled
    if &mouse == 'a'
        " disable mouse
        set mouse=
    else
        " enable mouse everywhere
        set mouse=a
    endif
endfunc
