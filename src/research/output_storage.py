"""Common output interface: existing reports plus optional per-entity projections.

Folder storage is domain-neutral: profiles supply a validated adapter rather than
implementing another archive or publisher. The intel report stays agent-readable.
"""


def store_output(report, archive, *, mode="report", folder_storage=None, records=None):
    if mode not in ("report", "opportunity_folders"):
        raise ValueError("Unknown output storage mode")
    if mode == "opportunity_folders":
        if folder_storage is None or records is None:
            raise ValueError("Folder storage requires a validated entity adapter")
        folder_storage.sync(records)
    return archive.write(report)
