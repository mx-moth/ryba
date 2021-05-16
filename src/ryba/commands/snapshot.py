import datetime

from .. import constants, directories, logging, targets

logger = logging.getLogger(__name__)


def create_snapshot(
    directory: directories.Directory,
    context: targets.TargetContext,
    *,
    timestamp: datetime.datetime,
    dry_run: bool,
) -> None:
    """
    Create a snapshot of the current backup for this Directory.
    """
    target_directory = directory.target_path
    snapshot_name = directory.snapshot_name(timestamp)
    current = target_directory / constants.CURRENT_SNAPSHOT_NAME
    snapshot = target_directory / snapshot_name
    logger.log(logging.INFO, "Creating snapshot %s", snapshot_name)

    cmd = [
        "cp", "--archive", "--link", "--no-target-directory", "--force",
        str(context.make_path(current)), str(context.make_path(snapshot)),
    ]
    if not dry_run:
        context.execute(cmd)
        context.write_file(
            snapshot / constants.TIMESTAMP_FILE_NAME,
            timestamp.isoformat().encode())
