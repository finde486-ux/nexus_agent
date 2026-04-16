from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

class NexusInterface:
    def __init__(self):
        self.console = Console()

    def display_welcome(self):
        self.console.print(Panel.fit(
            "[bold blue]NEXUS[/bold blue]\n[italic]Next-Generation Autonomous Engineering Intelligence[/italic]",
            border_style="blue"
        ))

    def display_task_start(self, task_id, description):
        self.console.print(f"\n[bold yellow]>>> Starting Task {task_id}:[/bold yellow] {description}")

    def display_subsystem_log(self, subsystem, message):
        self.console.print(f"[[bold cyan]{subsystem}[/bold cyan]] {message}")

    def display_task_complete(self, task_id, result):
        self.console.print(f"\n[bold green]<<< Task {task_id} Completed.[/bold green]")
        self.console.print(Panel(str(result), title="Execution Report"))
