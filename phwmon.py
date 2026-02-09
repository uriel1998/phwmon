#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GPLv2

import argparse
import subprocess
import shlex
import os

import psutil

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf
import cairo


def normalize_color_hex(s: str) -> str:
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3:
        s = s[0] + s[0] + s[1] + s[1] + s[2] + s[2]
    if len(s) == 4:
        s = s[0] + s[0] + s[1] + s[1] + s[2] + s[2] + s[3] + s[3]
    if len(s) == 6:
        s += "ff"
    if len(s) != 8:
        raise ValueError(f"Invalid RGBA hex color: {s!r}")
    return s


def color_hex_to_float(s: str):
    s = normalize_color_hex(s)
    return [
        int(s[0:2], 16) / 255.0,
        int(s[2:4], 16) / 255.0,
        int(s[4:6], 16) / 255.0,
        int(s[6:8], 16) / 255.0,
    ]


def bytes2human(n: int) -> str:
    symbols = ("K", "M", "G", "T", "P", "E", "Z", "Y")
    prefix = {}
    for i, sym in enumerate(symbols):
        prefix[sym] = 1 << ((i + 1) * 10)
    for sym in reversed(symbols):
        if n >= prefix[sym]:
            value = float(n) / prefix[sym]
            return "%.1f %sB" % (value, sym)
    return "%s B" % n


# Parameters
parser = argparse.ArgumentParser()

parser.add_argument("--load", help="Show a system load average graph", dest="load", action="store_true")

parser.add_argument("--cpu", help="Show a CPU activity graph", dest="cpu", action="store_true")
parser.add_argument("--core", help="Show a CPU activity graph for each logical CPU core", dest="core", action="store_true")

parser.add_argument("--mem", help="Show a memory usage graph", dest="mem", action="store_true")
parser.add_argument("--mem_percent", help="Tooltip: Show used memory in percentage", dest="mem_percent", action="store_true")

parser.add_argument("--swap", help="Show a swap usage graph", dest="swap", action="store_true")
parser.add_argument("--swap_percent", help="Tooltip: Show used swap in percentage", dest="swap_percent", action="store_true")

parser.add_argument("--net", help="Show a network usage graph", dest="net", action="store_true")
parser.add_argument("--net_scale", help="Maximum value for the network usage graph, in Mbps. Default: 40.", default=40, type=int)

parser.add_argument("--io", help="Show a disk I/O graph", dest="io", action="store_true")
parser.add_argument("--io_scale", help="Maximum value for the disk I/O graph, in MB/s. Default: 100.", default=100, type=int)

parser.add_argument("--size", help="Icon size in pixels. Default: 22.", default=22, type=int)
parser.add_argument("--invert", help="Try to invert order of icons", dest="invert", action="store_true")
parser.add_argument("--interval", help="Refresh interval in milliseconds. Default: 1000.", default=1000, type=int)

parser.add_argument("--bg", help="Background color (RGBA hex). Default: #00000077.", default="#00000077")
parser.add_argument("--fg_load", help="Load graph color (RGBA hex). Default: #f93.", default="#f93")
parser.add_argument("--fg_cpu", help="CPU graph color (RGBA hex). Default: #3f3.", default="#3f3")
parser.add_argument("--fg_mem", help="Memory graph color (RGBA hex). Default: #ff3.", default="#ff3")
parser.add_argument("--fg_swap", help="Swap graph color (RGBA hex). Default: #419CFF.", default="#419CFF")
parser.add_argument("--fg_net", help="Network graph color (RGBA hex). Default: #33f.", default="#33f")
parser.add_argument("--fg_io", help="Disk I/O graph color (RGBA hex). Default: #3cf.", default="#3cf")

parser.add_argument("--task_manager", help="Task manager command to execute on left click. Default: None.")

parser.set_defaults(load=False, cpu=False, core=False, mem=False, swap=False, net=False, io=False)
args = parser.parse_args()

w = h = args.size
invert = args.invert
interval_ms = args.interval
interval_s = max(0.001, interval_ms / 1000.0)

bg_rgba = color_hex_to_float(args.bg)
fgLoad = color_hex_to_float(args.fg_load)
fgCpu = color_hex_to_float(args.fg_cpu)
fgRam = color_hex_to_float(args.fg_mem)
fgSwap = color_hex_to_float(args.fg_swap)
fgNet = color_hex_to_float(args.fg_net)
fgDiskIo = color_hex_to_float(args.fg_io)

cpuEnabled = args.cpu or args.core
mergeCpus = not args.core
loadEnabled = args.load
ramEnabled = args.mem
memPercent = args.mem_percent
swapEnabled = args.swap
swapPercent = args.swap_percent
netEnabled = args.net
netScale = args.net_scale
diskIoEnabled = args.io
diskIoScale = args.io_scale
taskMgr = args.task_manager

# If no metric flags given, enable everything (including load).
if not loadEnabled and not cpuEnabled and not ramEnabled and not swapEnabled and not netEnabled and not diskIoEnabled:
    loadEnabled = True
    cpuEnabled = True
    mergeCpus = True
    ramEnabled = True
    swapEnabled = True
    netEnabled = True
    diskIoEnabled = True

cpu_count = psutil.cpu_count(logical=True) or 1
loadScale = cpu_count + 2


def run_task_manager(cmd: str) -> None:
    if not cmd:
        return
    try:
        argv = shlex.split(cmd)
        subprocess.Popen(argv)
    except Exception:
        subprocess.Popen(cmd, shell=True)


class HardwareMonitor:
    def __init__(self):
        if invert:
            self.initDiskIo()
            self.initNet()
            self.initSwap()
            self.initRam()
            self.initCpus()
            self.initLoad()
        else:
            self.initLoad()
            self.initCpus()
            self.initRam()
            self.initSwap()
            self.initNet()
            self.initDiskIo()

        self.redraw_all()
        GLib.timeout_add(interval_ms, self.update)

    def rightClickEvent(self, icon, button, activate_time):
        menu = Gtk.Menu()

        quit_item = Gtk.MenuItem.new_with_label("Quit")
        quit_item.connect("activate", lambda *_: Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        menu.popup(
            None,
            None,
            Gtk.StatusIcon.position_menu,
            icon,
            button,
            activate_time,
        )

    def leftClickEvent(self, icon):
        if taskMgr:
            run_task_manager(taskMgr)

    def _new_status_icon(self, title: str) -> Gtk.StatusIcon:
        icon = Gtk.StatusIcon()
        icon.set_title(title)
        icon.connect("popup-menu", self.rightClickEvent)
        icon.connect("activate", self.leftClickEvent)
        icon.set_visible(True)
        return icon

    # ---- Load ----
    def initLoad(self):
        if not loadEnabled:
            return
        self.load = [0.0 for _ in range(w)]
        self.loadIcon = self._new_status_icon("hwmon 0 load")

    def updateLoad(self):
        if not loadEnabled:
            return
        try:
            la1, la5, la15 = os.getloadavg()
        except (AttributeError, OSError):
            # Fallback: psutil provides only per-process load; if getloadavg unavailable,
            # just keep previous value.
            la1 = la5 = la15 = 0.0

        # Clamp to graph scale so it doesn't just pin at top.
        v = max(0.0, min(float(la1), float(loadScale)))
        self.load.append(v)
        self.load.pop(0)

        self.loadIcon.set_tooltip_text(
            f"Load avg: {la1:.2f} (1m), {la5:.2f} (5m), {la15:.2f} (15m)  |  scale 0..{loadScale}"
        )

    def drawLoad(self):
        if not loadEnabled:
            return
        self.draw(self.load, self.loadIcon, bg_rgba, fgLoad, loadScale)

    # ---- CPU ----
    def initCpus(self):
        if not cpuEnabled:
            return
        if mergeCpus:
            self.cpus = [[0 for _ in range(w)]]
            psutil.cpu_percent(percpu=False)  # prime
        else:
            n = len(psutil.cpu_percent(percpu=True))
            self.cpus = [[0 for _ in range(w)] for _ in range(n)]

        self.cpuIcons = []
        for i in range(len(self.cpus)):
            label = "" if mergeCpus else f" {i + 1}"
            self.cpuIcons.append(self._new_status_icon(f"hwmon 1 cpu{label}"))

    def updateCpus(self):
        if not cpuEnabled:
            return
        vals = psutil.cpu_percent(percpu=not mergeCpus)
        if mergeCpus:
            vals = [vals]
        for i, v in enumerate(vals):
            self.cpus[i].append(v)
            self.cpus[i].pop(0)
            label = "" if mergeCpus else f" {i + 1}"
            self.cpuIcons[i].set_tooltip_text(f"CPU{label}: {v}%")

    def drawCpus(self):
        if not cpuEnabled:
            return
        for i in range(len(self.cpus)):
            self.draw(self.cpus[i], self.cpuIcons[i], bg_rgba, fgCpu)

    # ---- RAM ----
    def initRam(self):
        if not ramEnabled:
            return
        self.ram = [0 for _ in range(w)]
        self.ramIcon = self._new_status_icon("hwmon 2 memory")

    def updateRam(self):
        if not ramEnabled:
            return
        mem = psutil.virtual_memory()
        total = int(mem.total)
        used = int(mem.used)
        used_percent = float(mem.percent)

        self.ram.append(used_percent)
        self.ram.pop(0)

        if memPercent:
            self.ramIcon.set_tooltip_text(f"Memory: {int(used_percent)}% used of {bytes2human(total)}")
        else:
            self.ramIcon.set_tooltip_text(f"Memory: {bytes2human(used)} used of {bytes2human(total)}")

    def drawRam(self):
        if not ramEnabled:
            return
        self.draw(self.ram, self.ramIcon, bg_rgba, fgRam)

    # ---- Swap ----
    def initSwap(self):
        if not swapEnabled:
            return
        self.swap = [0 for _ in range(w)]
        self.swapIcon = self._new_status_icon("hwmon 3 swap")

    def updateSwap(self):
        if not swapEnabled:
            return
        swap = psutil.swap_memory()
        total = int(swap.total)
        used = int(swap.used)
        used_percent = float(swap.percent)

        visible = bool(total)
        if bool(self.swapIcon.get_visible()) != visible:
            self.swapIcon.set_visible(visible)

        self.swap.append(used_percent if total else 0.0)
        self.swap.pop(0)

        if total:
            if swapPercent:
                self.swapIcon.set_tooltip_text(f"Swap: {int(used_percent)}% used of {bytes2human(total)}")
            else:
                self.swapIcon.set_tooltip_text(f"Swap: {bytes2human(used)} used of {bytes2human(total)}")

    def drawSwap(self):
        if not swapEnabled:
            return
        self.draw(self.swap, self.swapIcon, bg_rgba, fgSwap)

    # ---- Net ----
    def initNet(self):
        if not netEnabled:
            return
        self.net = [0 for _ in range(w)]
        v = psutil.net_io_counters(pernic=False)
        self.netBytes = int(v.bytes_sent + v.bytes_recv)
        self.netIcon = self._new_status_icon("hwmon 4 network")

    def updateNet(self):
        if not netEnabled:
            return
        v = psutil.net_io_counters(pernic=False)
        total = int(v.bytes_sent + v.bytes_recv)
        delta = total - self.netBytes
        self.netBytes = total

        mbps = (delta * 8.0) / 1.0e6 / interval_s
        self.net.append(mbps)
        self.net.pop(0)
        self.netIcon.set_tooltip_text(f"Network: {mbps:.1f} Mb/s")

    def drawNet(self):
        if not netEnabled:
            return
        self.draw(self.net, self.netIcon, bg_rgba, fgNet, netScale)

    # ---- Disk IO ----
    def initDiskIo(self):
        if not diskIoEnabled:
            return
        self.diskIo = [0 for _ in range(w)]
        v = psutil.disk_io_counters(perdisk=False)
        self.diskIoBytes = int(v.read_bytes + v.write_bytes)
        self.diskIoIcon = self._new_status_icon("hwmon 5 disk i/o")

    def updateDiskIo(self):
        if not diskIoEnabled:
            return
        v = psutil.disk_io_counters(perdisk=False)
        total = int(v.read_bytes + v.write_bytes)
        delta = total - self.diskIoBytes
        self.diskIoBytes = total

        mbs = (delta / 1.0e6) / interval_s
        self.diskIo.append(mbs)
        self.diskIo.pop(0)

        parts_lines = []
        for part in psutil.disk_partitions(all=False):
            if "cdrom" in part.opts or not part.fstype:
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except PermissionError:
                continue
            parts_lines.append(
                f"{part.mountpoint} {int(usage.percent)}% of {bytes2human(int(usage.total))} ({part.fstype})"
            )

        extra = "\n" + "\n".join(parts_lines) if parts_lines else ""
        self.diskIoIcon.set_tooltip_text(f"Disk I/O: {mbs:.1f} MB/s{extra}")

    def drawDiskIo(self):
        if not diskIoEnabled:
            return
        self.draw(self.diskIo, self.diskIoIcon, bg_rgba, fgDiskIo, diskIoScale)

    # ---- Drawing ----
    def draw(self, graph, icon, bg_rgba_f, fg_rgba_f, maxv=100):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surface)

        cr.set_source_rgba(bg_rgba_f[0], bg_rgba_f[1], bg_rgba_f[2], bg_rgba_f[3])
        cr.rectangle(0, 0, w, h)
        cr.fill()

        cr.set_source_rgba(fg_rgba_f[0], fg_rgba_f[1], fg_rgba_f[2], fg_rgba_f[3])
        for x in range(w):
            y = int(round((graph[x] / float(maxv)) * h))
            if y:
                cr.move_to(x + 0.5, h)
                cr.line_to(x + 0.5, h - y)
        cr.stroke()

        surface.flush()
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            surface.get_data(),
            GdkPixbuf.Colorspace.RGB,
            True,
            8,
            w,
            h,
            surface.get_stride(),
        )
        icon.set_from_pixbuf(pixbuf)

    def redraw_all(self):
        self.drawLoad()
        self.drawCpus()
        self.drawRam()
        self.drawSwap()
        self.drawNet()
        self.drawDiskIo()

    def update(self):
        self.updateLoad()
        self.updateCpus()
        self.updateRam()
        self.updateSwap()
        self.updateNet()
        self.updateDiskIo()
        self.redraw_all()
        return True


if __name__ == "__main__":
    HardwareMonitor()
    Gtk.main()
