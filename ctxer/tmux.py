from __future__ import annotations
import gdb  # type: ignore
import argparse
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

    @staticmethod
    def run_at(pane: Pane, cmd: str) -> None:
        cmd_ = f'tmux send-keys -t {pane.pane} "{cmd}" Enter'
        subprocess.run(cmd_.split(" "))

    @classmethod
    def get_session(
        cls,
        session: T.Optional[str],
        cmd: T.Optional[str] = None,
        options: T.Optional[str] = None,
        delete: bool = True,
        title: T.Optional[str] = None,
    ) -> Pane:
        # get exists sessions
        cmd_ = (
            "tmux list-sessions -F #{session_name}:#{window_id}:#{pane_id}:#{pane_tty}"
        )
        for line in cls._run_command(cmd_).strip().split("\n"):
            session_name, window_id, pane_id, pane_tty = line.split(":")
            if session == session_name:
                new_pane = Pane(
                    window_id, pane_id, pane_tty, delete=delete, title=title
                )
                new_pane.clear()
                return new_pane

        # create session
        cmd_ = "tmux new-session -P -d -F #{window_id}:#{pane_id}:#{pane_tty}"
        cmd_ += "" if options is None else f" {options}"
        cmd_ += "" if session is None else f" -s {session}"
        cmd_ += " cat -" if cmd is None else f" {cmd}"
        window_id, pane_id, pane_tty = cls._run_command(cmd_).split(":")
        new_pane = Pane(window_id, pane_id, pane_tty, delete=delete, title=title)
        return new_pane

    @classmethod
    def split_pane(
        cls,
        pane: str,
        window: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        options: T.Optional[str] = None,
        title: T.Optional[str] = None,
    ) -> Pane:
        if pane is not None:
            target = f" -t {pane}" if window is None else f" -t {pane}"
        else:
            target = ""

        cmd_ = "tmux split-window -P -d -F #{window_id}:#{pane_id}:#{pane_tty}"
        cmd_ += "" if options is None else f" {options}"
        cmd_ += target
        cmd_ += " cat -" if cmd is None else f" {cmd}"
        window_id, pane_id, pane_tty = cls._run_command(cmd_).split(":")
        new_pane = Pane(window_id, pane_id, pane_tty, title=title)
        return new_pane

    @classmethod
    def close_pane(cls, pane: str):
        if pane is not None:
            target = f" -t {pane}"
        else:
            target = ""
        cmd = "tmux kill-pane" + target
        cls._run_command(cmd)

    @classmethod
    def show_panes(cls):
        cmd = "tmux display-panes"
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
        clearing: bool = True,
        action: T.Optional[Action] = None,
        delete: bool = True,
        title: T.Optional[str] = None,
    ):
        self.window = window
        self.pane = pane
        self.tty = tty
        self.clearing = clearing
        self.action = action
        self.delete = delete
        self.title = title

        if title is not None:
            self.set_title(title)

    def split_above(self, cmd: T.Optional[str] = None, size: str = "50%", **kwargs):
        size_opt = f"-p {size[:-1]}" if size[-1] == "%" else f"-l {size}"
        return TmuxCommand.split_pane(
            pane=self.pane,
            window=self.window,
            cmd=cmd,
            options=f"-v -b {size_opt}",
            **kwargs,
        )

    def split_below(self, cmd: T.Optional[str] = None, size: str = "50%", **kwargs):
        size_opt = f"-p {size[:-1]}" if size[-1] == "%" else f"-l {size}"
        return TmuxCommand.split_pane(
            pane=self.pane,
            window=self.window,
            cmd=cmd,
            options=f"-v {size_opt}",
            **kwargs,
        )

    def split_left(self, cmd: T.Optional[str] = None, size: str = "50%", **kwargs):
        size_opt = f"-p {size[:-1]}" if size[-1] == "%" else f"-l {size}"
        return TmuxCommand.split_pane(
            pane=self.pane,
            window=self.window,
            cmd=cmd,
            options=f"-h -b {size_opt}",
            **kwargs,
        )

    def split_right(self, cmd: T.Optional[str] = None, size: str = "50%", **kwargs):
        size_opt = f"-p {size[:-1]}" if size[-1] == "%" else f"-l {size}"
        return TmuxCommand.split_pane(
            pane=self.pane,
            window=self.window,
            cmd=cmd,
            options=f"-h {size_opt}",
            **kwargs,
        )

    def write(self, data: str):
        if self.tty is not None:
            with open(self.tty, "w") as fo:
                fo.write(data)

    def set_title(self, title: str):
        self.write(f"\033]2;{title}\033\\")

    def clear(self):
        self.write("\x1b[H\x1b[2J")

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
            now = Pane(window, pane, tty, clearing=False, delete=False)
            __panes__.append(now)
        self.now = now

    def select(self, pane: T.Optional[str], window: T.Optional[str] = None) -> CTXer:
        if pane is None:
            pane_id = TmuxCommand.get_active_pane()[1]
        else:
            ps = [p for p in __panes__ if p.title == pane]
            if len(ps) == 1:
                return CTXer(ps[0])

            panes = TmuxCommand.get_pane_idx()
            pane_id = panes[pane]

        if window is None:
            window = TmuxCommand.get_active_pane()[0]

        p = [p for p in __panes__ if p.window == window and p.pane == pane_id][0]
        return CTXer(p)

    def split(
        self,
        direct: str,
        pane: T.Optional[Pane] = None,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        size: str = "50%",
        title: T.Optional[str] = None,
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
        new_pane = split_func[direct](cmd=cmd, size=size, title=title)
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
        title: T.Optional[str] = None,
    ) -> CTXer:
        return self.split("above", pane, gdbcmd, excmd, cmd, size, title)

    def below(
        self,
        pane: T.Optional[Pane] = None,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        size: str = "50%",
        title: T.Optional[str] = None,
    ) -> CTXer:
        return self.split("below", pane, gdbcmd, excmd, cmd, size, title)

    def left(
        self,
        pane: T.Optional[Pane] = None,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        size: str = "50%",
        title: T.Optional[str] = None,
    ) -> CTXer:
        return self.split("left", pane, gdbcmd, excmd, cmd, size, title)

    def right(
        self,
        pane: T.Optional[Pane] = None,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        size: str = "50%",
        title: T.Optional[str] = None,
    ) -> CTXer:
        return self.split("right", pane, gdbcmd, excmd, cmd, size, title)

    def session(
        self,
        name: str,
        gdbcmd: T.Optional[str] = None,
        excmd: T.Optional[str] = None,
        cmd: T.Optional[str] = None,
        delete: bool = True,
        title: T.Optional[str] = None,
    ) -> CTXer:
        if gdbcmd is not None:
            action = GdbCommandAction(gdbcmd)
        elif excmd is not None:
            action = ExternalCommandAction(excmd)
        else:
            action = None

        new_pane = TmuxCommand.get_session(
            session=name, cmd=cmd, delete=delete, title=title
        )
        new_pane.action = action
        __panes__.append(new_pane)
        return CTXer(new_pane)

    def update(self, event=None):
        for pane in __panes__:
            if pane.action is None or pane.tty is None or not os.path.exists(pane.tty):
                continue
            output = pane.action.do()
            if pane.clearing:
                pane.clear()
            pane.write(output)

    def clean(self, event=None):
        global __panes__
        for pane in __panes__:
            if not pane.delete:
                continue
            pane.close()
        __panes__ = [p for p in __panes__ if not p.delete]

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
            TmuxCommand.show_panes()
        else:
            args.func(args)

    def get_args(
        self, arg: str
    ) -> T.Tuple[argparse.ArgumentParser, T.Optional[argparse.Namespace]]:
        parser = argparse.ArgumentParser(exit_on_error=False)
        sp = parser.add_subparsers(dest="sp")

        p_add = sp.add_parser("add")
        p_add.set_defaults(func=self.add_pane)
        p_add.add_argument(
            "direct",
            choices=["above", "below", "left", "right", "k", "j", "h", "l"],
            default="below",
        )
        p_add.add_argument("pane", nargs="?")

        p_output = sp.add_parser("output")
        p_output.set_defaults(func=self.output_command)
        p_output.add_argument("pane")
        p_output.add_argument("command", nargs=argparse.REMAINDER)

        p_set = sp.add_parser("set")
        p_set.set_defaults(func=self.set_command)
        p_set.add_argument("--no-clearing", "-n", action="store_true")
        p_set.add_argument("pane")
        p_set.add_argument("command", nargs=argparse.REMAINDER)

        p_unset = sp.add_parser("unset")
        p_unset.set_defaults(func=self.unset_command)
        p_unset.add_argument("pane")

        p_update = sp.add_parser("update")
        p_update.set_defaults(func=self.update_panes)

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

    def output_command(self, args: argparse.Namespace):
        if __ctxer__ is None:
            raise ValueError(f"CTXer is not used")
        pane = __ctxer__.select(pane=args.pane)
        cmd = " ".join(args.command)
        if cmd.startswith("!"):
            action = ExternalCommandAction(cmd[1:])
        else:
            action = GdbCommandAction(cmd)
        output = action.do()
        pane.now.write(output)

    def set_command(self, args: argparse.Namespace):
        if __ctxer__ is None:
            raise ValueError(f"CTXer is not used")
        pane = __ctxer__.select(pane=args.pane)
        pane.now.clearing = not args.no_clearing
        cmd = " ".join(args.command)
        if cmd.startswith("!"):
            pane.now.action = ExternalCommandAction(cmd[1:])
        else:
            pane.now.action = GdbCommandAction(cmd)
        __ctxer__.update()

    def unset_command(self, args: argparse.Namespace):
        if __ctxer__ is None:
            raise ValueError(f"CTXer is not used")
        pane = __ctxer__.select(pane=args.pane)
        pane.now.action = None

    def update_panes(self, args: argparse.Namespace):
        if __ctxer__ is None:
            raise ValueError(f"CTXer is not used")
        __ctxer__.update()


PaneCommand()
