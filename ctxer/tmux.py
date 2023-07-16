from __future__ import annotations
import argparse
import gdb
import os
import subprocess
import typing as T

__ctxer__: T.Optional[CTXer] = None
__panes__: T.List[Pane] = []


class TmuxCommand:
    @staticmethod
    def _run_command(cmd: str) -> str:
        p = subprocess.run(cmd.split(" "), capture_output=True)
        return p.stdout.strip().decode()

    @classmethod
    def split_pane(
        cls,
        pane: str,
        window: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        options: T.Optional[str] = None,
    ) -> T.Tuple[str, str, str]:
        if pane is not None:
            target = f" -t {pane}" if window is None else f" -t {pane}"
        else:
            target = ""

        cmd_ = "tmux split-window -P -d -F #{window_id}:#{pane_id}:#{pane_tty}"
        cmd_ += "" if options is None else f" {options}"
        cmd_ += target
        cmd_ += " cat -" if cmd is None else f" {cmd}"
        window_id, pane_id, pane_tty = cls._run_command(cmd_).split(":")
        return window_id, pane_id, pane_tty

    @classmethod
    def close_pane(cls, pane: str):
        if pane is not None:
            target = f" -t {pane}"
        else:
            target = ""
        cmd = "tmux kill-pane" + target
        cls._run_command(cmd)

    @classmethod
    def get_tty(cls, pane: T.Optional[str] = None) -> str:
        if pane is not None:
            target = f" -t {pane}"
        else:
            target = ""
        cmd = "tmux display -p -F #{pane_tty}" + target
        return cls._run_command(cmd)

    @classmethod
    def get_active_pane(cls) -> T.Tuple[str, str, str]:
        cmd = "tmux display -p -F #{window_id}:#{pane_id}:#{pane_tty}"
        window_id, pane_id, pane_tty = cls._run_command(cmd).split(":")
        return window_id, pane_id, pane_tty

    @classmethod
    def get_pane_idx(cls) -> T.Dict[str, str]:
        cmd = "tmux list-panes -F #{pane_index}:#{pane_id}"
        panes = {}
        for line in cls._run_command(cmd).split("\n"):
            idx, id_ = line.split(":")
            panes[idx] = id_
        return panes


class Pane:
    def __init__(
        self,
        window: str,
        pane: str,
        tty: T.Optional[str] = None,
        is_main: bool = False,
        clearing: bool = True,
        action: T.Optional[Action] = None,
    ):
        self.window = window
        self.pane = pane
        self.tty = tty
        self.is_main = is_main
        self.clearing = clearing
        self.action = action

    def split_above(self, cmd: T.Optional[str] = None, size: str = "50%"):
        size_opt = f"-p {size[:-1]}" if size[-1] == "%" else f"-l {size}"
        window, pane, tty = TmuxCommand.split_pane(
            pane=self.pane,
            window=self.window,
            cmd=cmd,
            options=f"-v -b {size_opt}",
        )
        return Pane(window, pane, tty)

    def split_below(self, cmd: T.Optional[str] = None, size: str = "50%"):
        size_opt = f"-p {size[:-1]}" if size[-1] == "%" else f"-l {size}"
        window, pane, tty = TmuxCommand.split_pane(
            pane=self.pane, window=self.window, cmd=cmd, options=f"-v {size_opt}"
        )
        return Pane(window, pane, tty)

    def split_left(self, cmd: T.Optional[str] = None, size: str = "50%"):
        size_opt = f"-p {size[:-1]}" if size[-1] == "%" else f"-l {size}"
        window, pane, tty = TmuxCommand.split_pane(
            pane=self.pane,
            window=self.window,
            cmd=cmd,
            options=f"-h -b {size_opt}",
        )
        return Pane(window, pane, tty)

    def split_right(self, cmd: T.Optional[str] = None, size: str = "50%"):
        size_opt = f"-p {size[:-1]}" if size[-1] == "%" else f"-l {size}"
        window, pane, tty = TmuxCommand.split_pane(
            pane=self.pane, window=self.window, cmd=cmd, options=f"-h {size_opt}"
        )
        return Pane(window, pane, tty)

    def close(self):
        TmuxCommand.close_pane(self.pane)


class Action:
    def do(self) -> str:
        raise NotImplementedError


class GdbCommandAction(Action):
    def __init__(self, cmd: str) -> None:
        super().__init__()
        self.cmd = cmd

    def do(self) -> str:
        return gdb.execute(self.cmd, to_string=True) or ""


class ExternalCommandAction(Action):
    def __init__(self, cmd: str) -> None:
        super().__init__()
        self.cmd = cmd

    def do(self) -> str:
        return subprocess.run(
            self.cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ).stdout.decode()


class CTXer:
    def __init__(self, now: T.Optional[Pane] = None):
        if now is None:
            window, pane, tty = TmuxCommand.get_active_pane()
            now = Pane(window, pane, tty, is_main=True, clearing=False)
            __panes__.append(now)
        self.now = now

    def select(self, pane: T.Optional[str], window: T.Optional[str] = None) -> CTXer:
        if pane is None:
            pane = TmuxCommand.get_active_pane()[1]
        else:
            panes = TmuxCommand.get_pane_idx()
            pane = panes[pane]
        if window is None:
            window = TmuxCommand.get_active_pane()[0]
        p = [p for p in __panes__ if p.window == window and p.pane == pane][0]
        return CTXer(p)

    def split(
        self,
        direct: str,
        pane: T.Optional[Pane] = None,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        size: str = "50%",
    ) -> CTXer:
        if pane is None:
            pane = self.now

        if gdbcmd is not None:
            action = GdbCommandAction(gdbcmd)
        elif excmd is not None:
            action = ExternalCommandAction(excmd)
        else:
            action = None

        split_func = {
            "above": pane.split_above,
            "below": pane.split_below,
            "left": pane.split_left,
            "right": pane.split_right,
        }
        new_pane = split_func[direct](cmd=cmd, size=size)
        new_pane.action = action
        __panes__.append(new_pane)
        return CTXer(new_pane)

    def above(
        self,
        pane: T.Optional[Pane] = None,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        size: str = "50%",
    ) -> CTXer:
        return self.split("above", pane, gdbcmd, excmd, cmd, size)

    def below(
        self,
        pane: T.Optional[Pane] = None,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        size: str = "50%",
    ) -> CTXer:
        return self.split("below", pane, gdbcmd, excmd, cmd, size)

    def left(
        self,
        pane: T.Optional[Pane] = None,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        size: str = "50%",
    ) -> CTXer:
        return self.split("left", pane, gdbcmd, excmd, cmd, size)

    def right(
        self,
        pane: T.Optional[Pane] = None,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        size: str = "50%",
    ) -> CTXer:
        return self.split("right", pane, gdbcmd, excmd, cmd, size)

    def update(self, event):
        for pane in __panes__:
            if pane.action is None or pane.tty is None or not os.path.exists(pane.tty):
                continue
            output = pane.action.do()
            with open(pane.tty, "w") as fo:
                if pane.clearing:
                    fo.write("\x1b[H\x1b[2J")
                fo.write(output.rstrip())

    def clean(self, event):
        global __panes__
        for pane in __panes__:
            if pane.is_main:
                continue
            pane.close()
        __panes__ = [p for p in __panes__ if p.is_main]

    def build(self):
        global __ctxer__
        __ctxer__ = self
        gdb.events.stop.connect(__ctxer__.update)
        gdb.events.gdb_exiting.connect(__ctxer__.clean)  # type: ignore


class PaneCommand(gdb.Command):
    """add empty pane command"""

    def __init__(self):
        super().__init__("pane", gdb.COMMAND_SUPPORT)

    def invoke(self, arg, from_tty):
        if __ctxer__ is None:
            raise ValueError(f"CTXer is not used")
        parser, args = self.get_args(arg)
        if args is None or args.sp is None:
            parser.print_usage()
        else:
            args.func(args)

    def get_args(
        self, arg: str
    ) -> T.Tuple[argparse.ArgumentParser, T.Optional[argparse.Namespace]]:
        parser = argparse.ArgumentParser()
        sp = parser.add_subparsers(dest="sp")

        p_add = sp.add_parser("add")
        p_add.set_defaults(func=self.add_pane)
        p_add.add_argument(
            "direct",
            choices=["above", "below", "left", "right", "k", "j", "h", "l"],
            default="below",
        )
        p_add.add_argument("pane", nargs="?", default=None)

        p_gdb = sp.add_parser("set")
        p_gdb.set_defaults(func=self.set_command)
        p_gdb.add_argument("pane")
        p_gdb.add_argument("command", nargs=argparse.REMAINDER)

        p_gdb = sp.add_parser("unset")
        p_gdb.set_defaults(func=self.unset_command)
        p_gdb.add_argument("pane")

        try:
            args = parser.parse_args(arg.split(" "))
        except Exception:
            return parser, None
        return parser, args

    def add_pane(self, args: argparse.Namespace):
        if __ctxer__ is None:
            raise ValueError(f"CTXer is not used")
        pane = __ctxer__.select(pane=args.pane)
        split_func = {
            "above": pane.above,
            "below": pane.below,
            "left": pane.left,
            "right": pane.right,
            # vim binding
            "k": pane.above,
            "j": pane.below,
            "h": pane.left,
            "l": pane.right,
        }
        split_func[args.direct]()

    def set_command(self, args: argparse.Namespace):
        if __ctxer__ is None:
            raise ValueError(f"CTXer is not used")
        pane = __ctxer__.select(pane=args.pane)
        cmd = " ".join(args.command)
        if cmd.startswith("!"):
            pane.now.action = ExternalCommandAction(cmd[1:])
        else:
            pane.now.action = GdbCommandAction(cmd)

    def unset_command(self, args: argparse.Namespace):
        if __ctxer__ is None:
            raise ValueError(f"CTXer is not used")
        pane = __ctxer__.select(pane=args.pane)
        pane.now.action = None


PaneCommand()
