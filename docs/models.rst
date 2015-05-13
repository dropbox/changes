Data Model
==========

.. autoclass:: changes.models.artifact.Artifact
.. autoclass:: changes.models.author.Author
.. autoclass:: changes.models.build.Build
.. autoclass:: changes.models.buildseen.BuildSeen
.. autoclass:: changes.models.command.Command
.. autoclass:: changes.models.comment.Comment
.. autoclass:: changes.models.event.Event
.. autoclass:: changes.models.failurereason.FailureReason
.. autoclass:: changes.models.filecoverage.FileCoverage
.. autoclass:: changes.models.itemsequence.ItemSequence
.. autoclass:: changes.models.itemstat.ItemStat
.. autoclass:: changes.models.job.Job
.. autoclass:: changes.models.jobplan.JobPlan
.. autoclass:: changes.models.jobstep.JobStep
.. autoclass:: changes.models.jobphase.JobPhase
.. autoclass:: changes.models.latest_green_build.LatestGreenBuild
.. autoclass:: changes.models.log.LogSource
.. autoclass:: changes.models.log.LogChunk
.. autoclass:: changes.models.node.Cluster
.. autoclass:: changes.models.node.ClusterNode
.. autoclass:: changes.models.node.Node
.. autoclass:: changes.models.patch.Patch
.. autoclass:: changes.models.phabricatordiff.PhabricatorDiff
.. autoclass:: changes.models.plan.Plan
.. autoclass:: changes.models.project.Project
.. autoclass:: changes.models.project.ProjectOption
.. autoclass:: changes.models.repository.Repository
.. autoclass:: changes.models.revision.Revision
.. autoclass:: changes.models.snapshot.Snapshot
.. autoclass:: changes.models.source.Source
.. autoclass:: changes.models.step.Step
.. autoclass:: changes.models.task.Task

    See :ref:`tasks` for more details on what the task_name can refer to.

.. autoclass:: changes.models.test.TestCase
.. autoclass:: changes.models.testartifact.TestArtifact
.. autoclass:: changes.models.user.User

.. _tasks:

Tasks
-----

.. autofunction:: changes.jobs.create_job.create_job
.. autofunction:: changes.jobs.import_repo.import_repo
.. autofunction:: changes.jobs.signals.fire_signal
.. autofunction:: changes.jobs.signals.run_event_listener
.. autofunction:: changes.jobs.sync_artifact.sync_artifact
.. autofunction:: changes.jobs.sync_job.sync_job
.. autofunction:: changes.jobs.sync_job_step.sync_job_step
.. autofunction:: changes.jobs.sync_repo.sync_repo
