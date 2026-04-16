from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

class TaskProgressDisplay:
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        )

    def start(self):
        self.progress.start()

    def add_task(self, description, total=100):
        return self.progress.add_task(description, total=total)

    def update(self, task_id, advance=1, description=None):
        self.progress.update(task_id, advance=advance, description=description)

    def stop(self):
        self.progress.stop()
