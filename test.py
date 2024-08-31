from rich.panel import Panel
from rich.console import Console
from rich import print as rprint

panel_width = 100

lumen_banner = f"""
██╗     ██╗   ██╗███╗   ███╗███████╗███╗   ██╗
██║     ██║   ██║████╗ ████║██╔════╝████╗  ██║
██║     ██║   ██║██╔████╔██║█████╗  ██╔██╗ ██║
██║     ██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║
███████╗╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║
╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝

╭──────────────────────────────────────────────────╮
│               Lumen DDoS Security                │
│                                                  │
│        DDoS AORC Modify Prefix-List Script       │
│                                                  │
│    For issues with this script, please reach     │
│             out to Richard Blackwell             │
│                                                  │
│           Richard.Blackwell@lumen.com            │
╰──────────────────────────────────────────────────╯"""

script_banner = f"""
The purpose of this script is to allow the DDoS SOC
to add and remove prefixes from existing AORC customer's policies

Additional info can be found here:
https://nsmomavp045b.corp.intranet:8443/display/SOPP/AORC+Only+Modify+Prefix-list+Script"""

def make_banner(text: str) -> str:
    banner = ""
    for line in text.split("\n"):
        while len(line) < (panel_width - 4):
            line = f" {line} "
        banner += f"{line}\n"
    return banner

def print_banner(text: str) -> None:
    banner = make_banner(text)
    rprint(Panel(banner, style="bold", width=panel_width))

print_banner(lumen_banner)
print_banner(script_banner)


