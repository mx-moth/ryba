import datetime
import typing as t

from .. import directories, logging, rotators, targets

logger = logging.getLogger(__name__)

TBackupVerdict = t.Tuple[targets.Backup, rotators.Verdict, str]


def rotate_directory(
    directory: directories.Directory,
    context: targets.TargetContext,
    *,
    timestamp: datetime.datetime,
    dry_run: bool = False,
) -> None:
    """
    Rotate the existing snapshots for this directory,
    using the configured rotator for the directory.
    """
    if directory.rotate is None:
        logger.log(logging.INFO, "Not rotating backups: no rotator configured")
        return

    if (reason := directory.rotate.should_rotate()) is not True:
        logger.log(logging.INFO, f"Not rotating backups: {reason}")
        return

    logger.log(logging.INFO, f"Rotating backups using '{directory.rotate}' strategy")
    backups = list(context.list_backups(directory.target_path))

    # If this is a dry run, a current snapshot will not have been made.
    # To simulate the backup process properly, append a fictitious snapshot
    # that would have been created in a normal run
    if dry_run and timestamp is not None:
        backups.append(targets.Backup(
            name=directory.snapshot_name(timestamp),
            timestamp=timestamp))

    verdicts = sorted(directory.rotate.rotate_backups(timestamp, backups))
    for message in map(format_verdict_tuple, verdicts):
        logger.log(logging.INFO, message)
    if not dry_run:
        delete_snapshots(directory, context, verdicts)


def format_verdict_tuple(verdict_tuple: TBackupVerdict) -> t.Iterable[str]:
    """Format the verdict tuple for logging."""
    backup, verdict, explanation = verdict_tuple
    return f"  - {backup.name}: {verdict.name}. {explanation}"


def delete_snapshots(
    directory: directories.Directory,
    context: targets.TargetContext,
    verdicts: t.List[TBackupVerdict],
) -> None:
    for backup, verdict, explanation in sorted(verdicts):
        if verdict is rotators.Verdict.drop:
            entry_path = context.make_path(directory.target_path / backup.name)
            context.execute(["chmod", "-R", "u+wX", str(entry_path)])
            context.execute(["rm", "-rf", str(entry_path)])
