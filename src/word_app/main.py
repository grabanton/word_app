import typer
from .english import WordDictionary, WordTrainer

app = typer.Typer(
    name="eng",
    add_completion=False,
    help="A command-line English language learning tool."
)

@app.command()
def dictionary():
    """Run the dictionary application. (Default mode)"""
    app = WordDictionary()
    app.run()

@app.command()
def trainer():
    """Start the training session."""
    app = WordTrainer()
    app.run()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Default behavior is to run the dictionary mode.
    """
    if ctx.invoked_subcommand is None:
        dictionary()

if __name__ == "__main__":
    app()