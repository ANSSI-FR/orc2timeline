"""Module for command line interface."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import click

from .config import Config
from .core import OrcArgument, process, process_dir
from .info import __copyright__, __description__, __version__

LOG_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
ORC_REGEX = r"^(?:DFIR\-)?ORC_[^_]*_(.*)_[^_]*\.7z$"
RESULT_EXTENSION = ".csv.gz"


@click.group(name="orc2timeline", help=__description__, epilog=f"{__version__} - {__copyright__}")
@click.version_option(__version__)
@click.option(
    "tmp_dir",
    "--tmp-dir",
    envvar="TMPDIR",
    type=click.Path(dir_okay=True, file_okay=False, exists=True, writable=True, readable=True),
    help="Directory where to write temporary files into. TMPDIR global variable can also be used.",
)
@click.option(
    "--log-level",
    metavar="level",
    type=click.Choice(LOG_LEVELS),
    default="INFO",
    show_default=True,
    help="Print log messages of this level and higher",
)
@click.option("--log-file", help="Log file to store DEBUG level messages", metavar="file")
def entrypoint(tmp_dir: str, log_level: str, log_file: str | None) -> None:
    """Cli function."""
    # Setup logging
    if log_file:
        # Send everything (DEBUG included) in the log file and keep only log_level messages on the console
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(asctime)s] %(levelname)-8s - %(name)s - %(message)s",
            filename=log_file,
            filemode="w",
        )
        # define a Handler which writes messages of log_level or higher to the sys.stderr
        console = logging.StreamHandler()
        console.setLevel(log_level)
        # set a format which is simpler for console use
        formatter = logging.Formatter("[%(asctime)s] %(levelname)-8s - %(message)s")
        # tell the handler to use this format
        console.setFormatter(formatter)
        # add the handler to the root logger
        logging.root.addHandler(console)
    else:
        logging.basicConfig(
            level=log_level,
            format="[%(asctime)s] %(levelname)-8s - %(message)s",
        )

    if tmp_dir is not None:
        os.environ["TMPDIR"] = tmp_dir


@entrypoint.command("show_conf_file")
def cmd_show_conf_file() -> None:
    """Show path to configuration file."""
    click.echo("Configuration file is located at the following path:")
    click.echo(Config().config_file)


@entrypoint.command("show_conf")
def cmd_show_conf() -> None:
    """Show the configuration file content."""
    conf_path = Config().config_file
    click.echo("Configuration file content:")
    click.echo("=======================================================================")
    with conf_path.open("r") as f:
        data = f.read()
        click.echo(data)
    click.echo("=======================================================================")


@entrypoint.command("process")
@click.option("-j", "--jobs", type=int, default=-1, help="Number of threads to use")
@click.argument("file_list", type=click.Path(dir_okay=False, exists=True), nargs=-1)
@click.argument("output_path", type=click.Path(dir_okay=False, exists=False), nargs=1)
@click.option(
    "--overwrite",
    is_flag=True,
    show_default=True,
    default=False,
    help="Overwrite destination file if it already exists",
)
def cmd_process(jobs: int, file_list: str, output_path: str, *, overwrite: bool) -> None:
    """Command to process a list of files."""
    if (not Path(output_path).parent.exists()) or (not Path(output_path).parent.is_dir()):
        msg = (
            f"'OUTPUT_PATH': Directory '{click.format_filename(Path(output_path).parent.as_posix())}'"
            " does not exist or is not a directory."
        )
        raise click.BadParameter(msg)
    if not overwrite and Path(output_path).exists():
        msg = (
            f"'OUTPUT_PATH': File '{click.format_filename(output_path)}' already exists,"
            " use '--overwrite' if you know what you are doing."
        )
        raise click.BadParameter(msg)
    if jobs == -1:
        logging.warning(
            "--jobs option was not given, thus only one thread will be used. Therefore processing could take a while.",
        )

    hostname_set = set()
    clean_file_list = []
    for file in file_list:
        hostname = ""
        try:
            re_extract = re.search(ORC_REGEX, Path(file).name)
            if re_extract is not None:
                hostname = re_extract.group(1)
                clean_file_list.append(Path(file))
            else:
                msg = (
                    rf"Impossible to extract hostname from filename '{file}', file will be ignored."
                    rf" Tip: filename must match regex '{ORC_REGEX}'"
                )
                logging.info(msg)

        except AttributeError:
            msg = rf"Impossible to extract hostname from filename '{file}', filename must match regex '{ORC_REGEX}'"
            logging.info(msg)

        if hostname != "":
            hostname_set.add(hostname)

    if len(hostname_set) != 1:
        msg = f"Bad file list, all files must belong to the same host. Parsed hosts: {hostname_set}"
        raise click.BadParameter(msg)

    process(clean_file_list, output_path, hostname_set.pop(), jobs)


@entrypoint.command("process_dir")
@click.option("-j", "--jobs", type=int, default=-1, help="Number of threads to use")
@click.argument("input_dir", type=click.Path(dir_okay=True, file_okay=False, exists=True), nargs=1)
@click.argument("output_dir", type=click.Path(dir_okay=True, file_okay=False, exists=True), nargs=1)
@click.option(
    "--overwrite",
    is_flag=True,
    show_default=True,
    default=False,
    help="Overwrite destination file if it already exists",
)
def cmd_process_dir(jobs: int, input_dir: str, output_dir: str, *, overwrite: bool) -> None:
    """Process all ORCs in INPUT_DIRECTORY, writes output files in OUTPUT_DIR."""
    if jobs == -1:
        logging.warning(
            "--jobs option was not given, thus only one thread will be used. Therefore processing could take a while.",
        )

    orc_arguments = _crawl_input_dir_and_return_megastruct(input_dir, output_dir)

    final_orc_arguments = []
    for orc_argument in orc_arguments:
        if orc_argument.output_path.exists() and not overwrite:
            # verify if destination output already exists
            # create output directory if it does not exist
            logging.warning(
                "Output file '%s' already exists, processing will be ignored for host %s"
                " use '--overwrite' if you know what you are doing.",
                orc_argument.output_path.as_posix(),
                orc_argument.hostname,
            )
            continue
        if not orc_argument.output_path.parent.exists():
            orc_argument.output_path.parent.mkdir(parents=True, exist_ok=True)
        final_orc_arguments.append(orc_argument)

    process_dir(final_orc_arguments, jobs)


def _crawl_input_dir_and_return_megastruct(input_dir: str, output_dir: str) -> list[OrcArgument]:
    orc_arguments: dict[str, OrcArgument] = {}
    for file_in_sub_dir in Path(input_dir).glob("**/*"):
        re_extract = re.search(ORC_REGEX, Path(file_in_sub_dir).name)
        hostname = ""
        if re_extract is not None:
            hostname = re_extract.group(1)
        if hostname != "":
            output_sub_path = Path(file_in_sub_dir.parent).relative_to(input_dir) / (hostname + RESULT_EXTENSION)
            output_total_path = str(Path(output_dir) / output_sub_path)
            if orc_arguments.get(output_total_path) is None:
                new_orc_argument = OrcArgument(hostname=hostname, output_path=Path(output_total_path))
                orc_arguments[output_total_path] = new_orc_argument
            orc_arguments[output_total_path].orc_paths.append(Path(file_in_sub_dir))

    return list(orc_arguments.values())
