Snapshotting
============

One of the core concepts of Changes is snapshotting. At a high level, the API only provides an abstraction for snapshots and relies on individual implementations (such as the changes-lxc-wrapper project) to actually determine what they mean.


Architecture
------------

Snapshots consists of two discrete data models: Snapshot (snapshot) and SnapshotImage (snapshot_image).

A Snapshot object itself acts on a single Source (i.e. a commit) and generates an image for each build plan associated with a given project. This means that a SnapshotImage is keyed on (snapshot_id, plan_id).

For example, we might have a build that has two build plans: precise and lucid (two distros of ubuntu). You'd generally see a single build created, and within it two jobs: one job for precise, and one job for lucid. When a snapshot is generated, it will behave similarly, and it will also create two SnapshotImage objects: one for precise, and one for lucid.


The Build Process
-----------------

When a build is created for a snapshot it will be registered in the system with a special Cause attribute (linked to Cause.snapshot). A snapshot will be put into a pending state initially, and when all images are successfully built (again, one per plan) the snapshot will become 'active' and can then be set as the default snapshot for a given project.

If any of the jobs failed the entire snapshot is considered invalid and cannot be used.

If a new build plan is added when an existing snapshot is activated, it will simply ignore the missing image for the new build plan, which would suggest to the underlying system that they use whatever the default is.
