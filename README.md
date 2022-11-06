# ctxer
gdb context viewer for tmux.

## install
```sh
git clone https://github.com/wchoco/ctxer.git
echo "source $PWD/ctxer/gdbinit.py" >> ~/.gdbinit
```

## settings

```.gdbinit
source <PATH_TO_CLONE>/ctxer/gdbinit.py

python
import ctxer
main = ctxer.CTXer()
main.right(gdbcmd="ctx")
main.above(cmd="ipython3", size="30%").above(excmd="date", size="1")
main.build()
end
```