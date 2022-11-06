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
main.above(cmd="ipython3", percentage=30)
main.build()
end
```