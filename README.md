Hardware monitor icon for the system tray. Shows load, CPU, memory, network and disk I/O graphs. Works on Linux, BSD and Windows.

This is an updated version of [phwmon](https://gitlab.com/o9000/phwmon) working with python3 and gtk3. It also adds the option to include load measurements.  Right click the icon to get a "quit" menu.

The updating was done using Codex, and therefore is *not* under copyright. 

# Dependencies

python3-gi gir1.2-gtk-3.0 python3-psutil

On Debian/Ubuntu:

```
sudo apt install python3-gi gir1.2-gtk-3.0 python3-psutil
```
   

```
./phwmon.py --help
usage: phwmon.py [-h] [--cpu] [--core] [--mem] [--net] [--io] [--size SIZE]
                 [--bg BG] [--fg_cpu FG_CPU] [--fg_mem FG_MEM]
                 [--fg_net FG_NET] [--fg_io FG_IO]

optional arguments:
  -h, --help       show this help message and exit
  --load		   Show a graph of load
  --cpu            Show a CPU activity graph
  --core           Show a CPU activity graph for each logical CPU core
  --mem            Show a memory usage graph
  --net            Show a network usage graph
  --io             Show a disk I/O graph
  --size SIZE      Icon size in pixels. Default: 22.
  --bg BG          Background color (RGBA hex). Default: #00000077.
  --fg_cpu FG_CPU  CPU graph color (RGBA hex). Default: #3f3.
  --fg_mem FG_MEM  CPU graph color (RGBA hex). Default: #ff3.
  --fg_net FG_NET  CPU graph color (RGBA hex). Default: #33f.
  --fg_io FG_IO    CPU graph color (RGBA hex). Default: #3ff.
```
